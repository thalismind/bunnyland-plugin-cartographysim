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
from bunnyland.core.edges import ExitTo

from bunnyland_cartographysim import compass_fragments, spawn_compass, spawn_field_map


def _room(world, *, title="Hall"):
    return spawn_entity(world, [RoomComponent(title=title)])


def _character(world, room, name="Vin"):
    character = spawn_entity(
        world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def _hold(holder, item):
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), item.id)


def _exit(a, b, *, direction, label="", hidden=False):
    a.add_relationship(ExitTo(direction=direction, label=label, hidden=hidden), b.id)


def test_compass_names_exits_by_direction():
    actor = WorldActor()
    here = _room(actor.world)
    north = _room(actor.world, title="North")
    east = _room(actor.world, title="East")
    _exit(here, north, direction="north", label="a wooden door")
    _exit(here, east, direction="east")
    holder = _character(actor.world, here)
    _hold(holder, spawn_compass(actor.world))

    lines = compass_fragments(actor.world, holder)

    assert lines == [
        "Your compass points east.",
        "Your compass points north: a wooden door.",
    ]


def test_compass_skips_hidden_exits():
    actor = WorldActor()
    here = _room(actor.world)
    secret = _room(actor.world, title="Secret")
    _exit(here, secret, direction="down", hidden=True)
    holder = _character(actor.world, here)
    _hold(holder, spawn_compass(actor.world))

    assert compass_fragments(actor.world, holder) == ["Your compass finds no way out of here."]


def test_compass_requires_a_held_compass():
    actor = WorldActor()
    here = _room(actor.world)
    other = _room(actor.world, title="Other")
    _exit(here, other, direction="north")
    holder = _character(actor.world, here)
    _hold(holder, spawn_field_map(actor.world))  # a map, not a compass

    assert compass_fragments(actor.world, holder) == []


def test_compass_none_character():
    actor = WorldActor()
    assert compass_fragments(actor.world, None) == []


def test_compass_holder_without_a_room():
    actor = WorldActor()
    drifter = spawn_entity(
        actor.world, [IdentityComponent(name="drifter", kind="character"), CharacterComponent()]
    )
    _hold(drifter, spawn_compass(actor.world))

    assert compass_fragments(actor.world, drifter) == []
