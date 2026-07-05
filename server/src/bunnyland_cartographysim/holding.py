"""Shared helper: find the field-map *entity* a character is holding.

Several v2 mechanics (sharing, annotations, surveys) need the map entity itself — to hang an
edge, a second component, or a note on it — not just its :class:`MapComponent` value. v1's
``fog.held_map`` returns the component; this returns the entity so callers can mutate it.
"""

from __future__ import annotations

from bunnyland.core.ecs import contents
from relics import Entity, World

from .components import MapComponent


def held_map_entity(world: World, character: Entity) -> Entity | None:
    """Return the first field-map item ``character`` is holding, or ``None``."""
    for item_id in contents(character):
        if not world.has_entity(item_id):
            continue
        item = world.get_entity(item_id)
        if item.has_component(MapComponent):
            return item
    return None


__all__ = ["held_map_entity"]
