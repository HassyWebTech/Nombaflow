import httpx
from app.nomba.auth import get_access_token
from app.config import settings

async def create_checkout_session(
    amount: int,
    currency: str,
    reference: str,
    customer_email: str,
    callback_url: str,
) -> dict:
    """
    Creates a Nomba checkout session.
    Used when a customer subscribes for the first time —
    they pay via checkout and their card gets tokenised.
    """
    access_token = await get_access_token()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.nomba_base_url}/checkout/order",
            json={
                "orderReference": reference,
                "customerId": customer_email,
                "callbackUrl": callback_url,
                "customer": {"email": customer_email},
                "orderDetails": {
                    "amount": amount,
                    "currency": currency,
                    "description": "NombaFlow subscription",
                },
                "tokenizeCard": True,
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "accountId": settings.nomba_account_id,
            }
        )
        response.raise_for_status()
        return response.json()
