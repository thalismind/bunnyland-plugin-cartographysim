"""Domain events emitted by the cartography verbs and consequences."""

from __future__ import annotations

from bunnyland.core.events import DomainEvent


class LandmarkNamedEvent(DomainEvent):
    """A character pinned a landmark name to a room."""

    room_id_named: str
    name: str


class TravelStartedEvent(DomainEvent):
    """A character began fast-travelling toward a charted destination."""

    destination_id: str
    hops: int


class TravelStepEvent(DomainEvent):
    """A fast-travelling character advanced one hop along its planned route."""

    from_room_id: str
    to_room_id: str
    direction: str = ""


class TravelArrivedEvent(DomainEvent):
    """A fast-travelling character reached its destination."""

    destination_id: str


__all__ = [
    "LandmarkNamedEvent",
    "TravelArrivedEvent",
    "TravelStartedEvent",
    "TravelStepEvent",
]
