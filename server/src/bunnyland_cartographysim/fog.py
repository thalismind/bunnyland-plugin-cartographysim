"""Fog of war mechanic: unmapped ground reads as "uncharted".

A field map holder sees whether the room they stand in is already charted, and which exits
lead off the edge of their map into uncharted territory. This is the discovery loop: the
frontier stays visibly unknown until the mapping consequence stamps it in. It composes
naturally with darkness/wilderness packs, which hide the ground the map has not yet recorded.
"""

from __future__ import annotations

from bunnyland.core.ecs import contents
from bunnyland.core.edges import ExitTo
from relics import Entity, World

from .components import MapComponent
from .spatial import room_of


def held_map(world: World, character: Entity) -> MapComponent | None:
    """Return the map component of the first field map ``character`` is holding."""
    for item_id in contents(character):
        if not world.has_entity(item_id):
            continue
        item = world.get_entity(item_id)
        if item.has_component(MapComponent):
            return item.get_component(MapComponent)
    return None


def frontier_lines(room: Entity, charted: frozenset[str]) -> list[str]:
    """Lines for each visible exit of ``room`` leading to an uncharted room, by direction."""
    frontier = sorted(
        {
            edge.direction
            for edge, target in room.get_relationships(ExitTo)
            if not edge.hidden and str(target) not in charted
        }
    )
    return [
        f"Beyond the {direction or 'unmarked way'} lies uncharted territory."
        for direction in frontier
    ]


def fog_fragments(world: World, character: Entity) -> list[str]:
    """Charted/uncharted status of the current room plus any uncharted frontier exits."""
    if character is None:
        return []
    map_component = held_map(world, character)
    if map_component is None:
        return []
    room = room_of(world, character.id)
    if room is None:
        return []
    charted = map_component.charted_ids()
    lines: list[str]
    if str(room.id) in charted:
        lines = ["This place is charted on your field map."]
    else:
        lines = ["This place is uncharted; it is not yet on your field map."]
    lines.extend(frontier_lines(room, charted))
    return sorted(dict.fromkeys(lines))


__all__ = ["fog_fragments", "frontier_lines", "held_map"]
