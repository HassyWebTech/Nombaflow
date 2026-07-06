import hashlib
import hmac
import json
import uuid
from datetime import datetime
from uuid import UUID
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.webhook import WebhookEndpoint, WebhookDelivery
from app.database import AsyncSessionLocal


# ---------------------------------------------------------------------------
# Emit an event to all registered webhook endpoints for a tenant
# This is called after every significant state change in the system
# ---------------------------------------------------------------------------
async def emit_event(
    tenant_id: UUID,
    event_type: str,
    payload: dict,
    db: AsyncSession,
):
    # Find all active endpoints for this tenant that subscribed to this event
    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.tenant_id == tenant_id,
            WebhookEndpoint.active == True,
        )
    )
    endpoints = result.scalars().all()

    for endpoint in endpoints:
        # Check if this endpoint wants this event type
        if not _endpoint_wants_event(endpoint.events, event_type):
            continue

        # Build the signed payload
        full_payload = {
            "id": str(uuid.uuid4()),
            "event": event_type,
            "created_at": datetime.utcnow().isoformat(),
            "data": payload,
        }

        payload_str = json.dumps(full_payload, separators=(",", ":"))
        signature = _sign_payload(payload_str, endpoint.secret)

        # Create a delivery record before sending
        # This gives us a full audit trail even if delivery fails
        delivery = WebhookDelivery(
            endpoint_id=endpoint.id,
            event_type=event_type,
            payload=payload_str,
            attempt_count=0,
        )
        db.add(delivery)
        await db.commit()
        await db.refresh(delivery)

        # Dispatch asynchronously via Celery
        # We don't block the main request waiting for delivery
        from app.workers.webhook_tasks import deliver_webhook
        deliver_webhook.delay(str(delivery.id))


# ---------------------------------------------------------------------------
# Send a single webhook delivery
# Called by the Celery webhook_tasks worker
# ---------------------------------------------------------------------------
def send_delivery(delivery_id: str):
    """Sync wrapper for Celery."""
    import asyncio
    asyncio.run(_send_delivery(delivery_id))


async def _send_delivery(delivery_id: str):
    async with AsyncSessionLocal() as db:
        delivery = await db.get(WebhookDelivery, delivery_id)
        if not delivery:
            return

        endpoint = await db.get(WebhookEndpoint, delivery.endpoint_id)
        if not endpoint or not endpoint.active:
            return

        # Re-sign the payload for each delivery attempt
        signature = _sign_payload(delivery.payload, endpoint.secret)

        delivery.attempt_count += 1

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    endpoint.url,
                    content=delivery.payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-NombaFlow-Signature": signature,
                        "X-NombaFlow-Event": delivery.event_type,
                        "User-Agent": "NombaFlow-Webhooks/1.0",
                    }
                )

            delivery.status_code = response.status_code

            # 2xx means delivered successfully
            if 200 <= response.status_code < 300:
                delivery.delivered_at = datetime.utcnow()
                await db.commit()
                return

            # Non-2xx — schedule a retry if under max attempts
            await _schedule_redelivery_if_needed(delivery, db)

        except Exception as e:
            # Network error — schedule retry
            delivery.status_code = None
            await db.commit()
            await _schedule_redelivery_if_needed(delivery, db)


# ---------------------------------------------------------------------------
# Retry failed webhook deliveries with backoff
# Max 5 attempts: immediately, 5min, 30min, 2hr, 8hr
# ---------------------------------------------------------------------------
MAX_WEBHOOK_ATTEMPTS = 5
WEBHOOK_RETRY_DELAYS = [0, 300, 1800, 7200, 28800]  # seconds


async def _schedule_redelivery_if_needed(
    delivery: WebhookDelivery,
    db: AsyncSession,
):
    await db.commit()

    if delivery.attempt_count >= MAX_WEBHOOK_ATTEMPTS:
        # Give up — delivery permanently failed
        return

    delay_seconds = WEBHOOK_RETRY_DELAYS[
        min(delivery.attempt_count, len(WEBHOOK_RETRY_DELAYS) - 1)
    ]

    from app.workers.webhook_tasks import deliver_webhook
    from datetime import timedelta
    eta = datetime.utcnow() + timedelta(seconds=delay_seconds)
    deliver_webhook.apply_async(args=[str(delivery.id)], eta=eta)


# ---------------------------------------------------------------------------
# Sign a payload with HMAC-SHA256
# Merchants use this signature to verify the webhook came from NombaFlow
# Header sent: X-NombaFlow-Signature: sha256=<hex_digest>
# ---------------------------------------------------------------------------
def _sign_payload(payload: str, secret: str) -> str:
    signature = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={signature}"


# ---------------------------------------------------------------------------
# Check if an endpoint is subscribed to a specific event
# endpoints.events stores "*" for all events or comma-separated list
# e.g. "subscription.active,invoice.paid,dunning.started"
# ---------------------------------------------------------------------------
def _endpoint_wants_event(events_config: str, event_type: str) -> bool:
    if not events_config or events_config.strip() == "*":
        return True
    subscribed = [e.strip() for e in events_config.split(",")]
    # Support wildcard prefixes e.g. "subscription.*" matches "subscription.active"
    for subscribed_event in subscribed:
        if subscribed_event == event_type:
            return True
        if subscribed_event.endswith(".*"):
            prefix = subscribed_event[:-2]
            if event_type.startswith(prefix):
                return True
    return False


# ---------------------------------------------------------------------------
# Register a new webhook endpoint for a tenant
# ---------------------------------------------------------------------------
async def register_endpoint(
    tenant_id: UUID,
    url: str,
    events: str,
    db: AsyncSession,
) -> WebhookEndpoint:
    # Generate a signing secret unique to this endpoint
    secret = uuid.uuid4().hex + uuid.uuid4().hex

    endpoint = WebhookEndpoint(
        tenant_id=tenant_id,
        url=url,
        secret=secret,
        events=events,
        active=True,
    )
    db.add(endpoint)
    await db.commit()
    await db.refresh(endpoint)
    return endpoint
