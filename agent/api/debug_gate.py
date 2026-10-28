"""Gate for debug and experiment routes.

They reach into the signed-in Flow tab, mint reCAPTCHA tokens, return raw RPC
payloads or submit outside the worker's safety checks, so they answer 404
unless FLOWKIT_DEBUG_ENDPOINTS=1.
"""
from fastapi import Depends, HTTPException

from agent import config


def debug_only():
    if not config.FLOWKIT_DEBUG_ENDPOINTS:
        raise HTTPException(404, "debug endpoint disabled; set FLOWKIT_DEBUG_ENDPOINTS=1")


DEBUG = [Depends(debug_only)]
