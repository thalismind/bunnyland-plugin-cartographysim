from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)

from bunnyland_cartographysim import holder_of, room_of, spawn_field_map
from bunnyland_cartographysim.holding import held_map_entity


def _room(world, *, title="Room"):
    return spawn_entity(world, [RoomComponent(title=title)])


def _character(world, room=None):
    character = spawn_entity(
        world, [IdentityComponent(name="Vin", kind="character"), CharacterComponent()]
    )
    if room is not None:
        room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


# -- holder_of --------------------------------------------------------------------------


def test_holder_of_returns_the_carrier():
    actor = WorldActor()
    room = _room(actor.world)
    carrier = _character(actor.world, room)
    item = spawn_entity(actor.world, [IdentityComponent(name="lantern", kind="item")])
    carrier.add_relationship(Contains(mode=ContainmentMode.INVENTORY), item.id)
    assert holder_of(actor.world, item.id) == carrier


def test_holder_of_none_for_loose_item_in_a_room():
    actor = WorldActor()
    room = _room(actor.world)
    item = spawn_entity(actor.world, [IdentityComponent(name="lantern", kind="item")])
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), item.id)
    assert holder_of(actor.world, item.id) is None


def test_holder_of_none_for_uncontained_item():
    actor = WorldActor()
    item = spawn_entity(actor.world, [IdentityComponent(name="lantern", kind="item")])
    assert holder_of(actor.world, item.id) is None


def test_holder_of_none_for_unknown_entity():
    actor = WorldActor()
    assert holder_of(actor.world, "entity_9999") is None


# -- room_of ----------------------------------------------------------------------------


def test_room_of_resolves_through_a_holder():
    actor = WorldActor()
    room = _room(actor.world)
    carrier = _character(actor.world, room)
    item = spawn_entity(actor.world, [IdentityComponent(name="lantern", kind="item")])
    carrier.add_relationship(Contains(mode=ContainmentMode.INVENTORY), item.id)
    assert room_of(actor.world, item.id) == room


def test_room_of_none_for_unknown_entity():
    actor = WorldActor()
    assert room_of(actor.world, "entity_9999") is None


def test_room_of_none_when_uncontained():
    actor = WorldActor()
    drifter = _character(actor.world)  # in no room
    assert room_of(actor.world, drifter.id) is None


# -- held_map_entity --------------------------------------------------------------------


def test_held_map_entity_finds_the_map():
    actor = WorldActor()
    room = _room(actor.world)
    holder = _character(actor.world, room)
    field_map = spawn_field_map(actor.world)
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), field_map.id)
    assert held_map_entity(actor.world, holder) == field_map


def test_held_map_entity_none_with_only_a_plain_item():
    actor = WorldActor()
    room = _room(actor.world)
    holder = _character(actor.world, room)
    plain = spawn_entity(actor.world, [IdentityComponent(name="rope", kind="item")])
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), plain.id)
    assert held_map_entity(actor.world, holder) is None


def test_held_map_entity_skips_dangling_ids():
    actor = WorldActor()
    room = _room(actor.world)
    holder = _character(actor.world, room)
    ghost = spawn_entity(actor.world, [IdentityComponent(name="ghost", kind="item")])
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), ghost.id)
    actor.world.remove(ghost.id)
    assert held_map_entity(actor.world, holder) is None
