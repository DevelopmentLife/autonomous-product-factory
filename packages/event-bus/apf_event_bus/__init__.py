"""APF Event Bus — Redis Streams client and Pydantic event schemas."""

from .client import EventBusClient
from .memory import InMemoryEventBus
from .schemas import (
    ApprovalGrantedEvent,
    ApprovalRequiredEvent,
    BaseEvent,
    ConnectorEvent,
    PipelineCompleteEvent,
    PipelineFailedEvent,
    StageCompleteEvent,
    StageDispatchEvent,
    StageFailedEvent,
    StageStartedEvent,
)
from .streams import Streams

__all__ = [
    # Clients
    "EventBusClient",
    "InMemoryEventBus",
    # Stream constants
    "Streams",
    # Event schemas
    "BaseEvent",
    "StageDispatchEvent",
    "StageStartedEvent",
    "StageCompleteEvent",
    "StageFailedEvent",
    "ApprovalRequiredEvent",
    "ApprovalGrantedEvent",
    "PipelineCompleteEvent",
    "PipelineFailedEvent",
    "ConnectorEvent",
]
