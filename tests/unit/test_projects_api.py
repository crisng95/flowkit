import pytest
from fastapi import HTTPException

from agent.api import projects as projects_api


def test_extract_flow_project_id_from_success_shape():
    flow_result = {
        "data": {
            "result": {
                "data": {
                    "json": {
                        "result": {
                            "projectId": "project-123",
                        }
                    }
                }
            }
        }
    }

    assert projects_api._extract_flow_project_id(flow_result) == "project-123"


def test_extract_flow_project_id_raises_clear_error_on_unauthorized():
    flow_result = {
        "id": "abc",
        "status": 401,
        "data": {
            "error": {
                "json": {
                    "message": "Unauthorized",
                    "data": {
                        "code": "UNAUTHORIZED",
                    },
                }
            }
        },
    }

    with pytest.raises(HTTPException) as exc:
        projects_api._extract_flow_project_id(flow_result)

    assert exc.value.status_code == 502
    assert exc.value.detail == "Flow createProject failed: Unauthorized (UNAUTHORIZED)"


@pytest.mark.asyncio
async def test_detect_user_tier_falls_back_when_credits_payload_is_error():
    class _StubClient:
        async def get_credits(self):
            return {"detail": "NO_FLOW_KEY"}

    tier = await projects_api._detect_user_tier(_StubClient())

    assert tier == "PAYGATE_TIER_ONE"
