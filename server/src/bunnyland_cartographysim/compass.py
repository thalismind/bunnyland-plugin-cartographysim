"""Compass mechanic: name the current room's exits by direction.

A character holding a :class:`~bunnyland_cartographysim.components.CompassComponent` reads a
prompt line for every exit leading out of the room they stand in, reusing each ``ExitTo``
edge's ``direction`` and ``label``. This orients players and AI without guessing which way a
door leads. Hidden exits are omitted — the compass points to ways you can actually see.
"""

from __future__ import annotations

from bunnyland.core.ecs import contents
from bunnyland.core.edges import ExitTo
from relics import Entity, World

from .components import CompassComponent
from .spatial import room_of


def _holds_compass(world: World, character: Entity) -> bool:
    for item_id in contents(character):
        if world.has_entity(item_id) and world.get_entity(item_id).has_component(CompassComponent):
            return True
    return False


def compass_lines(room: Entity) -> list[str]:
    """One deterministic line per visible exit of ``room``, sorted by direction."""
    lines: list[str] = []
    exits = sorted(
        (
            (edge.direction, edge.label)
            for edge, _target in room.get_relationships(ExitTo)
            if not edge.hidden
        ),
        key=lambda pair: (pair[0], pair[1]),
    )
    for direction, label in exits:
        heading = direction or "an unmarked way"
        if label:
            lines.append(f"Your compass points {heading}: {label}.")
        else:
            lines.append(f"Your compass points {heading}.")
    return lines


def compass_fragments(world: World, character: Entity) -> list[str]:
    """Compass exit lines for a character holding a compass, else nothing."""
    if character is None or not _holds_compass(world, character):
        return []
    room = room_of(world, character.id)
    if room is None:
        return []
    lines = compass_lines(room)
    if not lines:
        return ["Your compass finds no way out of here."]
    return sorted(dict.fromkeys(lines))


__all__ = ["compass_fragments", "compass_lines"]
