"""YouTube OAuth2 authentication helper for Flow Kit."""
import json
import logging
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

BASE_DIR = Path(__file__).resolve().parent.parent
CHANNELS_DIR = BASE_DIR / "youtube" / "channels"


def get_channel_dir(channel_name: str) -> Path:
    """Return directory path for a channel."""
    return CHANNELS_DIR / channel_name


def get_authenticated_service(channel_name: str):
    """Authenticate and return a YouTube Data API v3 service resource."""
    cdir = get_channel_dir(channel_name)
    cdir.mkdir(parents=True, exist_ok=True)
    token_file = cdir / "token.json"
    secrets_file = cdir / "client_secrets.json"

    creds: Optional[Credentials] = None

    if token_file.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        except Exception as e:
            logger.warning("Failed to load existing token for %s: %s", channel_name, e)
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired token for channel %s", channel_name)
            creds.refresh(Request())
        else:
            if not secrets_file.exists():
                raise FileNotFoundError(
                    f"client_secrets.json not found for channel '{channel_name}' at {secrets_file}. "
                    "Download OAuth client ID from Google Cloud Console and place it there."
                )
            logger.info("Running OAuth flow for channel %s", channel_name)
            flow = InstalledAppFlow.from_client_secrets_file(str(secrets_file), SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials for subsequent runs
        token_file.write_text(creds.to_json(), encoding="utf-8")
        logger.info("Saved token to %s", token_file)

    service = build("youtube", "v3", credentials=creds)
    return service
