"""Opt-in Omni 1.2 text-to-video through Flow's own signed-in composer.

Flow 1.2 has a 3–15s slider and versioned model selection. The
macaron_cookie keys are documented by the separate live-captured FlowKit PR #85.
A dedicated Chrome CDP target is explicitly configured by the operator.
No account data, cookies, or CAPTCHA tokens are read or copied by this module.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any
from urllib.parse import urlparse

from agent.services import flow_batch as fb
from agent.services.omni_model_versions import (
    estimate_omni_12_credits, matches_model_label,
)

logger = logging.getLogger(__name__)


def is_omni_12_ui_envelope(freq: str) -> bool:
    """Match the model slot, never arbitrary user prompt text."""
    try:
        inner = json.loads(json.loads(freq)[0][0][1])
        model = str(inner[0][0][1])
    except (ValueError, KeyError, IndexError, TypeError):
        return False
    return bool(re.fullmatch(r"macaron_cookie_t2v_\d{1,2}s(?:_360p)?", model))


def parse_ui_request(freq: str) -> tuple[str, str, int, str, int]:
    """Decode the intent from a FlowKit envelope without submitting it."""
    wrapper = json.loads(freq)
    inner = json.loads(wrapper[0][0][1])
    request = inner[0][0]
    model = str(request[1])
    match = re.fullmatch(r"macaron_cookie_t2v_(\d{1,2})s(_360p)?", model)
    if not match:
        raise ValueError("Not an Omni 1.2 UI request")
    seconds = int(match.group(1))
    resolution = "360p" if match.group(2) else "720p"
    aspect = int(request[2])
    prompt = str(request[0][2][0][0][0])
    project_id = str(inner[1][5])
    estimate_omni_12_credits(seconds, resolution)  # validates duration and resolution
    if aspect not in (fb.VIDEO_ASPECT_PORTRAIT, fb.VIDEO_ASPECT_LANDSCAPE):
        raise ValueError("Invalid Omni 1.2 aspect")
    return prompt, project_id, seconds, resolution, aspect


def read_credit_quote(body: str) -> int:
    """Parse a visible live quote; unknown UI locale fails without spending."""
    text = body[-1500:]
    patterns = (
        r"кредитів:\s*(\d+)",
        r"(\d+)\s+credits",
        r"credits?:\s*(\d+)",
        r"(\d+)\s+Credits",
    )
    for pattern in patterns:
        found = re.search(pattern, text, flags=re.IGNORECASE)
        if found:
            return int(found.group(1))
    raise RuntimeError("Flow's live credit quote was not visible; refusing generation")


async def _click_radio(page: Any, label: str, *, icon: bool = False) -> None:
    radios = page.locator('button[role="radio"]:visible')
    for i in range(await radios.count()):
        item = radios.nth(i)
        if icon:
            val = await item.locator("mat-icon").first.inner_text() if await item.locator("mat-icon").count() else ""
            ok = val.strip() == label
        else:
            ok = label in (await item.inner_text())
        if ok:
            if await item.get_attribute("aria-checked") != "true":
                await item.click()
                await page.wait_for_timeout(160)
            return
    raise RuntimeError(f"Flow UI option not found: {label}")


async def _pick_model(page: Any) -> None:
    triggers = page.locator("button").filter(
        has=page.locator("mat-icon", has_text="arrow_drop_down")
    )
    for i in range(await triggers.count()):
        button = triggers.nth(i)
        if not await button.is_visible():
            continue
        text = (await button.inner_text()).strip()
        if not any(word in text for word in ("Omni", "Veo", "Nano Banana")):
            continue
        if matches_model_label(text, "Omni 1.2 Flash"):
            return
        await button.click()
        items = page.locator('[role="menuitem"]:visible')
        for j in range(await items.count()):
            item = items.nth(j)
            if matches_model_label(await item.inner_text(), "Omni 1.2 Flash"):
                await item.click()
                await page.wait_for_timeout(220)
                return
        raise RuntimeError("Omni 1.2 Flash is not offered by the signed-in Flow account")
    raise RuntimeError("Flow UI model menu was not found")


async def _set_duration(page: Any, seconds: int) -> None:
    slider = page.locator('input[type="range"][min="0"][max="12"]:visible').first
    await slider.wait_for(state="visible", timeout=7000)
    bounds = await slider.bounding_box()
    if not bounds:
        raise RuntimeError("Omni 1.2 duration slider is not attached")
    await slider.click(position={"x": min(7, bounds["width"]/2), "y": bounds["height"]/2})
    for _ in range(seconds - 3):
        await slider.press("ArrowRight")
    if int(await slider.input_value()) != seconds - 3:
        raise RuntimeError("Flow did not select the requested Omni 1.2 duration")


async def _configure(page: Any, *, seconds: int, resolution: str, aspect: int) -> None:
    settings = page.locator("button.settings-trigger-button").first
    if not await settings.is_visible():
        if await page.locator("flow-creative-agent-prompt-box").is_visible():
            raise RuntimeError("This account uses the new agent-first composer; support for that Flow UI remains pending")
        raise RuntimeError("Classic Flow settings trigger is unavailable")
    await settings.click()
    await _click_radio(page, "videocam", icon=True)
    await _click_radio(page, "chrome_extension", icon=True)
    await _click_radio(page, "crop_9_16" if aspect == fb.VIDEO_ASPECT_PORTRAIT else "crop_16_9", icon=True)
    await _pick_model(page)
    await _click_radio(page, resolution)
    await _set_duration(page, seconds)
    await _click_radio(page, "x1")
    await page.wait_for_timeout(320)
    quoted = read_credit_quote(await page.locator("body").inner_text())
    expected = estimate_omni_12_credits(seconds, resolution)
    cap = int(os.environ.get("FLOW_OMNI12_MAX_CREDITS", "20"))
    if cap < 0:
        raise ValueError("FLOW_OMNI12_MAX_CREDITS must be non-negative")
    if quoted > cap:
        raise RuntimeError(f"Flow quotes {quoted} credits; exceeds configured max {cap}")
    if quoted > expected:
        raise RuntimeError(
            f"Flow quotes {quoted} credits, above the known {expected}-credit limit; refusing generation"
        )
    await settings.click()
    await page.wait_for_timeout(180)


async def _capture_generation_response(route: Any, future: asyncio.Future, timeout: float) -> None:
    """Proxy the UI-generated POST only once; capture body before navigation."""
    try:
        response = await route.fetch(timeout=int(timeout * 1000))
        body = await response.text()
        await route.fulfill(response=response)
        if not future.done():
            future.set_result((int(response.status), body))
    except Exception as exc:
        if not future.done():
            future.set_exception(exc)
        try:
            await route.abort()
        except Exception:
            pass


async def run_omni_12_ui_generation(
    freq: str, *, project_id: str | None, timeout: float = 120
) -> dict:
    """Submit at most once via Flow's own UI, never by replaying a model id."""
    cdp = os.environ.get("FLOW_OMNI12_CDP_URL", "").strip()
    if not cdp or urlparse(cdp).hostname not in ("127.0.0.1", "localhost"):
        return {"status": 422, "error": "FLOW_OMNI12_CDP_URL must be an explicit local Chrome CDP address"}
    try:
        prompt, pid, seconds, resolution, aspect = parse_ui_request(freq)
        if project_id and pid != project_id:
            raise ValueError("Requested project and UI generation project differ")
        configured_cap = int(os.environ.get("FLOW_OMNI12_MAX_CREDITS", "20"))
        if configured_cap < 0:
            raise ValueError("FLOW_OMNI12_MAX_CREDITS cannot be negative")
        if estimate_omni_12_credits(seconds, resolution) > configured_cap:
            return {"status": 422, "error": f"Omni 1.2 generation exceeds max {configured_cap} credits"}
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        return {"status": 422, "error": str(exc)}

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {"status": 503, "error": "Omni 1.2 UI backend requires optional playwright (pip install playwright)"}

    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(cdp)
        contexts = browser.contexts
        if not contexts:
            return {"status": 503, "error": "The configured Chrome has no signed-in Flow profile"}
        # Always use an isolated tab in the existing browser profile; never
        # close the user's persistent Chrome or replace their active Flow tab.
        page = await contexts[0].new_page()
        try:
            await page.goto(
                f"https://flow.google.com/project/{pid}",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            await page.wait_for_timeout(1100)
            await _configure(page, seconds=seconds, resolution=resolution, aspect=aspect)
            editor = page.locator('[contenteditable="true"]:visible').first
            if not await editor.count():
                editor = page.locator("textarea:visible").first
            await editor.wait_for(state="visible", timeout=9000)
            await editor.fill(prompt)
            await page.wait_for_timeout(250)
            if (await editor.inner_text()).strip() != prompt.strip() and await editor.evaluate("e=>e.isContentEditable"):
                raise RuntimeError("Flow composer did not accept the prompt")

            future = asyncio.get_running_loop().create_future()
            async def on_route(route: Any) -> None:
                await _capture_generation_response(route, future, timeout)

            def matcher(url: Any) -> bool:
                text = str(url)
                return "batchexecute" in text and f"rpcids={fb.RPC_GEN_VIDEO_TEXT}" in text

            await page.route(matcher, on_route)
            try:
                generate = page.locator("button.generate-icon-button:visible").first
                await generate.wait_for(state="visible", timeout=7000)
                if await generate.is_disabled():
                    raise RuntimeError("Flow Generate button is disabled")
                await generate.click()  # ONE submit; no automatic retry
                status, body = await asyncio.wait_for(future, timeout=timeout)
            finally:
                await page.unroute(matcher, on_route)

            if "PUBLIC_ERROR_UNUSUAL_ACTIVITY" in body:
                return {"status": 429, "error": "PUBLIC_ERROR_UNUSUAL_ACTIVITY"}
            return {"status": status, "data": body}
        except Exception as exc:
            logger.warning("Omni 1.2 UI submit failed (no automatic retry): %s", exc)
            return {"status": 502, "error": f"OMNI_12_UI_SUBMIT_FAILED: {type(exc).__name__}: {exc}"}
        finally:
            await page.close()
