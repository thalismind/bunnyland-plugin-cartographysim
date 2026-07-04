"""Cartography components: the field map, the compass, and room landmarks.

All three are immutable pydantic-dataclass :class:`relics.Component` subclasses. State is
never mutated in place — the mapping consequence and command handlers swap whole values with
``replace_component(entity, replace(component, ...))`` (or build a fresh component).

- :class:`MapComponent` is carried on an *item* (a field map). It records every room its
  holder has stood in as a tuple of :class:`ChartedRoom` records, each capturing the room's
  title, biome, and known :class:`ChartedExit` edges. The recorded exit graph is what
  fast-travel routes over, so the map only ever knows what its holder actually walked.
- :class:`CompassComponent` is carried on an item and orients the holder; the compass
  fragment provider reads the *current* room's live exits, so the component itself is a thin
  marker.
- :class:`LandmarkComponent` is drawn onto a *room* (by the ``name-landmark`` verb or the
  worldgen hook) and pins a memorable name to it.
"""

from __future__ import annotations

from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component

# --------------------------------------------------------------------------------------
# Field map records (plain immutable value objects, not ECS components)
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ChartedExit:
    """One recorded exit from a charted room: a direction leading to a known room."""

    direction: str
    to_room_id: str
    label: str = ""


@dataclass(frozen=True)
class ChartedRoom:
    """A single room as recorded on a field map."""

    room_id: str
    title: str
    biome: str = "unknown"
    exits: tuple[ChartedExit, ...] = ()


def _sorted_rooms(rooms: tuple[ChartedRoom, ...]) -> tuple[ChartedRoom, ...]:
    return tuple(sorted(rooms, key=lambda room: room.room_id))


# --------------------------------------------------------------------------------------
# Components
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class MapComponent(Component):
    """A carried field map that records every room its holder visits.

    ``rooms`` is kept sorted by ``room_id`` so serialization and iteration are deterministic.
    """

    rooms: tuple[ChartedRoom, ...] = ()

    def charted_ids(self) -> frozenset[str]:
        """Room ids this map has charted."""
        return frozenset(room.room_id for room in self.rooms)

    def get(self, room_id: str) -> ChartedRoom | None:
        """Return the charted record for ``room_id``, or ``None`` if uncharted."""
        for room in self.rooms:
            if room.room_id == room_id:
                return room
        return None

    def with_room(self, record: ChartedRoom) -> MapComponent:
        """Return a new map with ``record`` added or replacing an existing same-id record."""
        others = tuple(room for room in self.rooms if room.room_id != record.room_id)
        return MapComponent(rooms=_sorted_rooms((*others, record)))

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        # Only the map's holder reads its charted-room tally.
        if not ctx.is_first_person:
            return ()
        count = len(self.rooms)
        if count == 0:
            return ("Your field map is blank; you have charted no rooms yet.",)
        noun = "room" if count == 1 else "rooms"
        return (f"Your field map shows {count} charted {noun}.",)


@dataclass(frozen=True)
class CompassComponent(Component):
    """A carried compass. The compass fragment reads the current room's live exits."""

    style: str = "brass"


@dataclass(frozen=True)
class LandmarkComponent(Component):
    """A memorable name pinned to a room. ``kind`` distinguishes natural vs player marks."""

    name: str
    kind: str = "marker"
    shared: bool = True

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        return (f"This place is known as {self.name!r}.",)


__all__ = [
    "ChartedExit",
    "ChartedRoom",
    "CompassComponent",
    "LandmarkComponent",
    "MapComponent",
]
