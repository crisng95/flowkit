"""Offline tests for the opt-in browser UI Omni 1.2 bridge."""
import asyncio
from types import SimpleNamespace

import pytest

from agent.services import flow_batch as fb
from agent.services.omni_12_ui import (
    parse_ui_request, read_credit_quote, _capture_generation_response,
    run_omni_12_ui_generation, is_omni_12_ui_envelope,
)
from agent.services.omni_model_versions import (
    OMNI_12_DURATIONS, estimate_omni_12_credits,
    is_omni_12_label, matches_model_label,
)


def test_aliases_match_12_not_11():
    assert matches_model_label("Omni 1.2 Flash", "Omni Flash 1.2")
    assert matches_model_label("Gemini Omni Flash 1.2", "Omni 1.2 Flash")
    assert not matches_model_label("Omni 1.1 Flash", "Omni Flash 1.2")
    assert not is_omni_12_label("Omni Flash 1.1")


@pytest.mark.parametrize("seconds",range(3,16))
def test_ui_marker_parses_all_durations(seconds):
    assert seconds in OMNI_12_DURATIONS
    freq=fb.text_video_request(
        "paper boat", "f7c87337-60dd-4d1b-b109-40158e34a9ab",
        aspect="VIDEO_ASPECT_RATIO_LANDSCAPE",
        model=f"macaron_cookie_t2v_{seconds}s",
        resolution="360p",
    )
    prompt,pid,duration,resolution,aspect=parse_ui_request(freq)
    assert prompt=="paper boat"
    assert pid=="f7c87337-60dd-4d1b-b109-40158e34a9ab"
    assert duration==seconds
    assert resolution=="360p"
    assert aspect==fb.VIDEO_ASPECT_LANDSCAPE


@pytest.mark.parametrize("duration,cost360,cost720",[(3,3,9),(10,10,30),(11,12,36),(15,20,60)])
def test_costs_include_higher_rate_for_11_to_15(duration,cost360,cost720):
    assert estimate_omni_12_credits(duration,"360p")==cost360
    assert estimate_omni_12_credits(duration,"720p")==cost720


def test_unknown_quote_fails_closed():
    assert read_credit_quote("Для створення буде використано стільки кредитів: 3")==3
    assert read_credit_quote("This will use 30 credits")==30
    with pytest.raises(RuntimeError,match="live credit quote"):
        read_credit_quote("Choose your video model")


@pytest.mark.asyncio
async def test_missing_explicit_ui_config_refuses_request(monkeypatch):
    monkeypatch.delenv("FLOW_OMNI12_CDP_URL",raising=False)
    freq=fb.text_video_request("test","project",model="macaron_cookie_t2v_3s",resolution="360p")
    response=await run_omni_12_ui_generation(freq,project_id="project")
    assert response["status"]==422


@pytest.mark.asyncio
async def test_low_credit_cap_rejects_15s_without_opening_browser(monkeypatch):
    monkeypatch.setenv("FLOW_OMNI12_CDP_URL","http://127.0.0.1:9224")
    monkeypatch.setenv("FLOW_OMNI12_MAX_CREDITS","20")
    freq=fb.text_video_request("test","project",model="macaron_cookie_t2v_15s")
    response=await run_omni_12_ui_generation(freq,project_id="project")
    assert response["status"]==422
    assert "max 20 credits" in response["error"]


def test_model_check_does_not_match_user_prompt_containing_key():
    freq=fb.text_video_request(
        "Please explain the model name macaron_cookie_t2v_3s",
        "project",model="abra_t2v_4s")
    assert not is_omni_12_ui_envelope(freq)
    freq12=fb.text_video_request("test","project",model="macaron_cookie_t2v_3s")
    assert is_omni_12_ui_envelope(freq12)


@pytest.mark.asyncio
async def test_body_captured_once_before_ui_navigation():
    calls=[]
    class Response:
        status=200
        async def text(self):
            calls.append("read_body")
            return "rpc-body"
    class Route:
        async def fetch(self,**kwargs):
            calls.append("forward_once")
            return Response()
        async def fulfill(self,**kwargs):
            calls.append("return_to_flow")
        async def abort(self):calls.append("abort")
    f=asyncio.get_running_loop().create_future()
    await _capture_generation_response(Route(),f,120)
    assert await f==(200,"rpc-body")
    assert calls==["forward_once","read_body","return_to_flow"]
