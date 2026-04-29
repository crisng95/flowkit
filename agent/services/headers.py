"""Randomized browser headers to avoid detection."""
import random
import time
from agent.config import USER_AGENTS, CHROME_VERSIONS, BROWSER_VALIDATIONS, CLIENT_DATA


def random_headers() -> dict:
    """Generate randomized browser-like headers for Google Flow API."""
    ua = random.choice(USER_AGENTS)
    chrome_ver = random.choice(CHROME_VERSIONS)
    validation = random.choice(BROWSER_VALIDATIONS)
    client_data = random.choice(CLIENT_DATA)

    if "Windows" in ua:
        platform, mobile = '"Windows"', "?0"
    elif "Macintosh" in ua:
        platform, mobile = '"macOS"', "?0"
    else:
        platform, mobile = '"Linux"', "?0"

    return {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "text/plain;charset=UTF-8",
        "origin": "https://labs.google",
        "priority": "u=1, i",
        "referer": "https://labs.google/",
        "sec-ch-ua": f'"Not;A=Brand";v="99", {chrome_ver}',
        "sec-ch-ua-mobile": mobile,
        "sec-ch-ua-platform": platform,
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "user-agent": ua,
        "x-browser-channel": "stable",
        "x-browser-copyright": "Copyright 2025 Google LLC. All rights reserved.",
        "x-browser-validation": validation,
        "x-browser-year": "2025",
        "x-client-data": client_data,
    }


def read_headers() -> dict:
    """Headers for read-only endpoints (credits/media/status polling).

    Keep deterministic browser-like headers so Google Flow read endpoints can
    be called from extension context without relying on randomization.
    """
    return {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "text/plain;charset=UTF-8",
        "origin": "https://labs.google",
        "referer": "https://labs.google/",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
    }
