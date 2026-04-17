"""Flow Kit SDK — high-level domain-model interface."""

from agent.sdk.models.base import DomainModel
from agent.sdk.persistence.sqlite_repository import SQLiteRepository
from agent.sdk.services.operations import init_operations, OperationService


def init_sdk(flow_client) -> OperationService:
    """Bootstrap the SDK: create repo, wire into DomainModel, return OperationService."""
    repo = SQLiteRepository()
    return init_operations(flow_client, repo)
