"""World-generation enrichment: seed natural landmarks on generated rooms.

Generated rooms expose a ``biome`` plus semantic ``tags``/``wants``/``needs`` and an intent
``description``. This hook scans that text for natural-landmark cues (peaks, ruins,
crossroads, caverns, shrines) and pins a themed :class:`LandmarkComponent` onto the room, so
freshly generated worlds already have a few memorable places to chart — without the core
generator knowing this plugin exists. Rooms that already carry a landmark are left untouched.
"""

from __future__ import annotations

from bunnyland.core import RoomComponent
from bunnyland.core.ecs import parse_entity_id, replace_component
from bunnyland.core.events import RoomGeneratedEvent
from bunnyland.core.world_actor import WorldActor

from .components import LandmarkComponent

#: Ordered ``(cue terms, landmark kind, name)`` rules; the first matching rule wins so
#: seeding is deterministic regardless of how many cues a room mentions.
NATURAL_LANDMARKS: tuple[tuple[tuple[str, ...], str, str], ...] = (
    (("crossroads", "junction", "crossing"), "crossroads", "the Crossroads"),
    (("peak", "summit", "mountain", "ridge", "cliff"), "peak", "the High Peak"),
    (("ruin", "ruins", "ancient", "derelict", "forgotten"), "ruin", "the Old Ruins"),
    (("shrine", "temple", "altar", "sanctuary"), "shrine", "the Forgotten Shrine"),
    (("cave", "cavern", "grotto", "hollow"), "cave", "the Deep Cavern"),
)


def _text(event: RoomGeneratedEvent) -> str:
    generation = event.generation
    return " ".join(
        (
            event.entity_kind,
            event.biome,
            generation.description,
            *generation.tags,
            *generation.wants,
            *generation.needs,
        )
    ).casefold()


def classify_landmark(event: RoomGeneratedEvent) -> tuple[str, str] | None:
    """Return the ``(kind, name)`` of the natural landmark a room cues, or ``None``."""
    text = _text(event)
    for terms, kind, name in NATURAL_LANDMARKS:
        if any(term in text for term in terms):
            return kind, name
    return None


class CartographyWorldgenHook:
    """Attach natural landmarks to generated rooms that read like memorable places."""

    def subscribe(self, actor: WorldActor) -> None:
        self._actor = actor
        actor.bus.subscribe(RoomGeneratedEvent, self._on_room)

    def _on_room(self, event: RoomGeneratedEvent) -> None:
        parsed = parse_entity_id(event.entity_id)
        if parsed is None or not self._actor.world.has_entity(parsed):
            return
        room = self._actor.world.get_entity(parsed)
        if not room.has_component(RoomComponent) or room.has_component(LandmarkComponent):
            return
        classified = classify_landmark(event)
        if classified is None:
            return
        kind, name = classified
        replace_component(room, LandmarkComponent(name=name, kind=kind, shared=True))


__all__ = ["NATURAL_LANDMARKS", "CartographyWorldgenHook", "classify_landmark"]
