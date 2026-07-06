import httpx
from app.nomba.auth import get_access_token
from app.config import settings

async def charge_tokenised_card(
    token: str,
    amount: int,
    currency: str,
    reference: str,
    customer_email: str,
) -> dict:
    """
    Charges a previously tokenised card.
    amount is in kobo (smallest currency unit).
    reference must be unique per charge — used for idempotency.
    """
    access_token = await get_access_token()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.nomba_base_url}/checkout/charge",
            json={
                "token": token,
                "amount": amount,
                "currency": currency,
                "reference": reference,
                "customerEmail": customer_email,
                "accountId": settings.nomba_subaccount_id,
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "accountId": settings.nomba_account_id,
            }
        )
        response.raise_for_status()
        return response.json()
