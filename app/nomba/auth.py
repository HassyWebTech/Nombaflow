import httpx
from app.config import settings

async def get_access_token() -> str:
    """
    Authenticates with Nomba and returns a short-lived access token.
    Every API call needs this token in the Authorization header.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.nomba_base_url}/auth/token/issue",
            json={
                "clientId": settings.nomba_client_id,
                "clientSecret": settings.nomba_private_key,
            },
            headers={"accountId": settings.nomba_account_id}
        )
        response.raise_for_status()
        data = response.json()
        return data["data"]["access_token"]
