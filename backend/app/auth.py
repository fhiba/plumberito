import os

import httpx
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/auth")

GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")
OAUTH_CALLBACK_URL = os.environ.get("OAUTH_CALLBACK_URL", "")


@router.get("/github")
def github_login():
    return RedirectResponse(
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={OAUTH_CALLBACK_URL}"
        f"&scope=repo"
    )


@router.post("/exchange")
async def exchange_code(body: dict):
    code = body.get("code", "")

    token_resp = httpx.post(
        "https://github.com/login/oauth/access_token",
        json={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
        },
        headers={"Accept": "application/json"},
    )
    token_data = token_resp.json()
    access_token = token_data.get("access_token")

    if not access_token:
        return {"error": token_data.get("error_description", "Failed to get access token")}

    user_resp = httpx.get(
        "https://api.github.com/user",
        headers={
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github+json",
        },
    )
    user_data = user_resp.json()

    return {
        "access_token": access_token,
        "username": user_data.get("login", ""),
    }
