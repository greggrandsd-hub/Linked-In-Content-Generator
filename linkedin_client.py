"""
LinkedIn API client — Post approved content directly to LinkedIn.

Setup:
  1. Go to https://www.linkedin.com/developers/apps and create an app
  2. Under Products, request "Share on LinkedIn" and "Sign In with LinkedIn using OpenID Connect"
  3. Under Auth tab, add redirect URL: http://localhost:8585/callback
  4. Copy Client ID and Client Secret to your .env file
  5. Run: python linkedin_client.py --setup
     This opens a browser for you to authorize, then saves your access token.
"""

import json
import os
import sys
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs

import requests

from config import (
    LINKEDIN_CLIENT_ID,
    LINKEDIN_CLIENT_SECRET,
    LINKEDIN_ACCESS_TOKEN,
)

TOKEN_FILE = os.path.join(os.path.dirname(__file__), ".linkedin_token.json")
REDIRECT_URI = "http://localhost:8585/callback"
SCOPES = "w_member_social"


def _load_saved_token() -> str | None:
    """Load a previously saved access token."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            data = json.load(f)
            # Check if token is still valid
            if data.get("expires_at", 0) > time.time():
                return data["access_token"]
            else:
                print("[LinkedIn] Saved token has expired. Re-run: python linkedin_client.py --setup")
    return None


def _save_token(access_token: str, expires_in: int) -> None:
    """Save the access token to a file."""
    with open(TOKEN_FILE, "w") as f:
        json.dump({
            "access_token": access_token,
            "expires_at": time.time() + expires_in,
        }, f)
    print(f"[LinkedIn] Token saved to {TOKEN_FILE}")


def get_access_token() -> str:
    """Get a valid LinkedIn access token (from .env, saved file, or prompt setup)."""
    # First check .env
    if LINKEDIN_ACCESS_TOKEN:
        return LINKEDIN_ACCESS_TOKEN
    # Then check saved file
    saved = _load_saved_token()
    if saved:
        return saved
    raise ValueError(
        "No LinkedIn access token found. Run: python linkedin_client.py --setup"
    )


def setup_oauth() -> str:
    """
    Run the OAuth 2.0 flow to get a LinkedIn access token.
    Opens a browser for the user to authorize.
    """
    if not LINKEDIN_CLIENT_ID or not LINKEDIN_CLIENT_SECRET:
        print("ERROR: Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET in your .env file first.")
        print("Get these from: https://www.linkedin.com/developers/apps")
        sys.exit(1)

    auth_code = None

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal auth_code
            query = parse_qs(urlparse(self.path).query)
            auth_code = query.get("code", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>LinkedIn authorized. You can close this tab.</h1>")

        def log_message(self, format, *args):
            pass  # Silence HTTP logs

    # Step 1: Open browser for authorization
    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization?"
        + urlencode({
            "response_type": "code",
            "client_id": LINKEDIN_CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
        })
    )
    print("[LinkedIn] Opening browser for authorization...")
    webbrowser.open(auth_url)

    # Step 2: Wait for callback
    print("[LinkedIn] Waiting for authorization callback on localhost:8585...")
    server = HTTPServer(("localhost", 8585), CallbackHandler)
    server.handle_request()

    if not auth_code:
        print("ERROR: No authorization code received.")
        sys.exit(1)

    # Step 3: Exchange code for access token
    print("[LinkedIn] Exchanging code for access token...")
    resp = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": LINKEDIN_CLIENT_ID,
            "client_secret": LINKEDIN_CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
        },
    )
    resp.raise_for_status()
    token_data = resp.json()

    access_token = token_data["access_token"]
    expires_in = token_data.get("expires_in", 5184000)  # default 60 days

    _save_token(access_token, expires_in)
    print(f"[LinkedIn] Authorization complete. Token valid for {expires_in // 86400} days.")
    return access_token


def get_my_profile_urn(access_token: str) -> str:
    """Get the current user's LinkedIn URN (person ID) from saved token data."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            data = json.load(f)
            member_sub = data.get("member_sub")
            if member_sub:
                return f"urn:li:person:{member_sub}"

    raise ValueError(
        "No member ID found in saved token. Re-run: python linkedin_client.py --setup"
    )


def post_to_linkedin(
    post_text: str,
    image_bytes: bytes | None = None,
) -> str:
    """
    Post content to LinkedIn. Returns the post URL.
    """
    access_token = get_access_token()
    person_urn = get_my_profile_urn(access_token)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202401",
    }

    # If we have an image, upload it first
    image_urn = None
    if image_bytes:
        image_urn = _upload_image(access_token, person_urn, image_bytes)

    # Build the post payload
    payload = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": post_text,
                },
                "shareMediaCategory": "IMAGE" if image_urn else "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC",
        },
    }

    if image_urn:
        payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [{
            "status": "READY",
            "media": image_urn,
        }]

    print("[LinkedIn] Publishing post...")
    resp = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers=headers,
        json=payload,
    )

    if resp.status_code == 201:
        post_id = resp.headers.get("X-RestLi-Id", resp.json().get("id", ""))
        print(f"[LinkedIn] Post published successfully. ID: {post_id}")
        return post_id
    else:
        print(f"[LinkedIn] Post failed: {resp.status_code} — {resp.text}")
        resp.raise_for_status()


def _upload_image(access_token: str, person_urn: str, image_bytes: bytes) -> str:
    """Upload an image to LinkedIn and return its asset URN."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    # Step 1: Register the upload
    register_payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": person_urn,
            "serviceRelationships": [{
                "relationshipType": "OWNER",
                "identifier": "urn:li:userGeneratedContent",
            }],
        }
    }

    resp = requests.post(
        "https://api.linkedin.com/v2/assets?action=registerUpload",
        headers=headers,
        json=register_payload,
    )
    resp.raise_for_status()

    upload_data = resp.json()["value"]
    upload_url = upload_data["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
    ]["uploadUrl"]
    asset_urn = upload_data["asset"]

    # Step 2: Upload the image binary
    print("[LinkedIn] Uploading image...")
    resp = requests.put(
        upload_url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "image/png",
        },
        data=image_bytes,
    )
    resp.raise_for_status()

    print(f"[LinkedIn] Image uploaded: {asset_urn}")
    return asset_urn


if __name__ == "__main__":
    if "--setup" in sys.argv:
        setup_oauth()
    elif "--test" in sys.argv:
        token = get_access_token()
        urn = get_my_profile_urn(token)
        print(f"Authenticated as: {urn}")
    else:
        print("Usage:")
        print("  python linkedin_client.py --setup   # Authorize with LinkedIn")
        print("  python linkedin_client.py --test    # Test your connection")
