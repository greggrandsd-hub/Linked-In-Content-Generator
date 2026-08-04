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

# ---------------------------------------------------------------------------
# APPROVAL GATE (Greg's ruling 2026-07-31, enforced 2026-08-04)
#
# On 2026-07-31 three comments went live on Greg's LinkedIn that he never
# approved. His ruling: "I didn't tell you to ever post without me."
#
# Every write function below now fails CLOSED. Nothing publishes unless Greg's
# same-day, per-comment approval is on file. The Claude hook
# .claude/hooks/block_linkedin_autopost.py blocks these paths at the tool
# boundary; this guard is the second layer, so the module stays safe even when
# run outside Claude entirely (Task Scheduler, a stray python call, a future
# script that imports it).
#
# The gate is opened only by .claude/hooks/grant_li_comment_approval.py after
# Greg types his GO. Do not add a bypass flag. Do not weaken this to "warn".
# ---------------------------------------------------------------------------
APPROVAL_FILE = r"C:\Users\16194\Desktop\Git Test Folder\_BACKUPS\.li_comment_approval.json"


def _require_greg_approval(action: str, action_class: str,
                           comment_number: int | None = None) -> None:
    """Raise unless Greg approved this exact action today. Fail closed.

    action_class matters (hardened 2026-08-04 after the council review): before
    this, an approval covering comments 1-3 ALSO unlocked post_to_linkedin()
    (an original post to Greg's feed) and setup_oauth() (a fresh 60-day posting
    token), because those pass comment_number=None and the per-item check was
    skipped. A comment GO is a comment GO. It is not permission to publish a
    post and it is certainly not permission to mint a token.
    """
    from datetime import date

    try:
        with open(APPROVAL_FILE, encoding="utf-8") as f:
            record = json.load(f)
    except Exception:
        record = None

    if not record or record.get("date") != date.today().isoformat():
        raise RuntimeError(
            f"REFUSED: {action} without Greg's approval.\n"
            f"No valid approval for {date.today().isoformat()} at {APPROVAL_FILE}.\n"
            "Greg's rule (2026-07-31): nothing posts to his LinkedIn without his\n"
            "typed GO on that specific item, that same day. Send the ping, wait\n"
            "for his GO, record it with grant_li_comment_approval.py."
        )

    if record.get("class", "comment") != action_class:
        raise RuntimeError(
            f"REFUSED: {action}.\n"
            f"Today's approval covers '{record.get('class', 'comment')}' actions, "
            f"not '{action_class}'.\n"
            "A GO on comments never authorizes publishing a post or minting a token."
        )

    if comment_number is not None:
        approved = record.get("approved") or []
        numbers = {item["n"] for item in approved
                   if isinstance(item, dict) and "n" in item}
        if comment_number not in numbers:
            raise RuntimeError(
                f"REFUSED: comment #{comment_number} is not in today's approval.\n"
                f"Greg approved only {sorted(numbers)} "
                f"(his words: {record.get('greg_wording', 'not recorded')})."
            )


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

    GATED: minting a token is what makes silent posting possible again, so this
    requires Greg's same-day approval too. The saved token expired 2026-05-18 and
    it stays that way unless Greg himself decides otherwise.
    """
    _require_greg_approval("minting a new LinkedIn posting token", "token")
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

    GATED: raises unless Greg's same-day approval is on file. Greg publishes his
    own original posts; this path exists for legacy callers (run.py, app.py) and
    must never fire on its own.
    """
    _require_greg_approval("publishing a LinkedIn post", "post")
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


def post_comment(post_urn: str, comment_text: str, comment_number: int | None = None) -> dict:
    """
    Post a comment on an existing LinkedIn post or share.

    GATED: raises unless Greg approved this comment number today. See
    _require_greg_approval above. Callers must pass comment_number (the "## Comment N"
    from the dated queue file) so approval is enforced per comment, not per batch.

    Args:
        post_urn: The URN of the target post. Accepts forms:
            - urn:li:share:1234567890
            - urn:li:ugcPost:1234567890
            - urn:li:activity:1234567890
            If the bare numeric activity ID is passed, it is wrapped as urn:li:activity:.
        comment_text: The comment body. Apply Voice DNA scrub before calling.

    Returns:
        Dict with at minimum {"ok": bool, "status": int, "comment_id": str|None, "raw": str}.

    LinkedIn endpoint: POST /v2/socialActions/{encoded_share_urn}/comments
    Required scope: w_member_social (already in SCOPES at top of file).
    """
    if comment_number is None:
        raise RuntimeError(
            "REFUSED: post_comment() requires comment_number.\n"
            "Without it the per-comment check is skipped and any same-day approval\n"
            "would authorize arbitrary comment text. Pass the '## Comment N' number\n"
            "from the dated queue file Greg actually reviewed."
        )
    _require_greg_approval("posting a LinkedIn comment", "comment", comment_number)
    access_token = get_access_token()
    person_urn = get_my_profile_urn(access_token)

    if not post_urn.startswith("urn:li:"):
        # Treat bare numeric IDs as activity URNs by default
        post_urn = f"urn:li:activity:{post_urn}"

    from urllib.parse import quote
    encoded = quote(post_urn, safe="")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202401",
    }

    payload = {
        "actor": person_urn,
        "object": post_urn,
        "message": {
            "text": comment_text,
        },
    }

    print(f"[LinkedIn] Posting comment on {post_urn}...")
    resp = requests.post(
        f"https://api.linkedin.com/v2/socialActions/{encoded}/comments",
        headers=headers,
        json=payload,
        timeout=30,
    )

    body_text = resp.text[:500] if resp.text else ""
    if resp.status_code in (200, 201):
        try:
            comment_id = resp.json().get("id") or resp.headers.get("X-RestLi-Id", "")
        except Exception:
            comment_id = resp.headers.get("X-RestLi-Id", "")
        print(f"[LinkedIn] Comment posted. ID: {comment_id}")
        return {"ok": True, "status": resp.status_code, "comment_id": comment_id, "raw": body_text}

    print(f"[LinkedIn] Comment failed: {resp.status_code} - {body_text}")
    return {"ok": False, "status": resp.status_code, "comment_id": None, "raw": body_text}


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
