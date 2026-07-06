import httpx
from app.nomba.auth import get_access_token
from app.config import settings

async def initiate_refund(
    amount: int,
    reference: str,
    original_charge_ref: str,
) -> dict:
    """
    Refunds a charge — used for proration credits when
    a customer downgrades mid-cycle.
    """
    access_token = await get_access_token()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.nomba_base_url}/transfers/refund",
            json={
                "amount": amount,
                "reference": reference,
                "originalReference": original_charge_ref,
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "accountId": settings.nomba_account_id,
            }
        )
        response.raise_for_status()
        return response.json()
