"""Spawn factories for cartography items.

The loader does not consume ``ContentContribution.prefabs``, so the field map and compass are
created with these ``spawn_entity`` helpers (from tests, admin tooling, or a worldgen hook).
Each device is a portable, holdable item carrying its component; pass ``room_id`` to drop it
into a room, or leave it out to spawn it uncontained (e.g. straight into an inventory).
"""

from __future__ import annotations

from bunnyland.core import (
    ContainmentMode,
    Contains,
    HoldableComponent,
    IdentityComponent,
    PortableComponent,
    spawn_entity,
)
from relics import Entity, World

from .components import CompassComponent, MapComponent


def _link_into_room(world: World, item: Entity, room_id) -> None:
    if room_id is None or not world.has_entity(room_id):
        return
    world.get_entity(room_id).add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), item.id)


def spawn_field_map(world: World, *, room_id=None) -> Entity:
    """Spawn a blank field map item, optionally placed in ``room_id``."""
    item = spawn_entity(
        world,
        [
            IdentityComponent(name="field map", kind="item", tags=("cartographysim",)),
            PortableComponent(),
            HoldableComponent(slot="hand"),
            MapComponent(),
        ],
    )
    _link_into_room(world, item, room_id)
    return item


def spawn_compass(world: World, *, room_id=None, style: str = "brass") -> Entity:
    """Spawn a compass item, optionally placed in ``room_id``."""
    item = spawn_entity(
        world,
        [
            IdentityComponent(name="compass", kind="item", tags=("cartographysim",)),
            PortableComponent(),
            HoldableComponent(slot="hand"),
            CompassComponent(style=style),
        ],
    )
    _link_into_room(world, item, room_id)
    return item


__all__ = ["spawn_compass", "spawn_field_map"]
