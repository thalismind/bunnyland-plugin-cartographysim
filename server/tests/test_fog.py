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

from bunnyland_cartographysim import (
    MappingConsequence,
    fog_fragments,
    spawn_compass,
    spawn_field_map,
)

EPOCH = 100


def _room(world, *, title="Room"):
    return spawn_entity(world, [RoomComponent(title=title)])


def _character(world, room, name="Vin"):
    character = spawn_entity(
        world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def _hold(holder, item):
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), item.id)


def _exit(a, b, *, direction):
    a.add_relationship(ExitTo(direction=direction), b.id)


def test_uncharted_room_reads_as_uncharted():
    actor = WorldActor()
    room = _room(actor.world)
    holder = _character(actor.world, room)
    _hold(holder, spawn_field_map(actor.world))

    lines = fog_fragments(actor.world, holder)

    assert lines == ["This place is uncharted; it is not yet on your field map."]


def test_charted_room_reads_as_charted():
    actor = WorldActor()
    room = _room(actor.world)
    holder = _character(actor.world, room)
    _hold(holder, spawn_field_map(actor.world))
    MappingConsequence().process(actor.world, EPOCH)

    lines = fog_fragments(actor.world, holder)

    assert "This place is charted on your field map." in lines


def test_frontier_exits_are_flagged():
    actor = WorldActor()
    here = _room(actor.world, title="Here")
    beyond = _room(actor.world, title="Beyond")
    _exit(here, beyond, direction="north")
    holder = _character(actor.world, here)
    _hold(holder, spawn_field_map(actor.world))
    MappingConsequence().process(actor.world, EPOCH)  # charts "here" but not "beyond"

    lines = fog_fragments(actor.world, holder)

    assert "Beyond the north lies uncharted territory." in lines


def test_charted_frontier_exit_is_not_flagged():
    actor = WorldActor()
    here = _room(actor.world, title="Here")
    beyond = _room(actor.world, title="Beyond")
    _exit(here, beyond, direction="north")
    holder = _character(actor.world, here)
    field_map = spawn_field_map(actor.world)
    _hold(holder, field_map)
    consequence = MappingConsequence()
    consequence.process(actor.world, EPOCH)
    # Chart "beyond" too by moving the map's holder there.
    here.remove_relationship(Contains, holder.id)
    beyond.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), holder.id)
    consequence.process(actor.world, EPOCH + 1)
    # Return to "here"; both rooms are now charted.
    beyond.remove_relationship(Contains, holder.id)
    here.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), holder.id)

    lines = fog_fragments(actor.world, holder)

    assert lines == ["This place is charted on your field map."]


def test_fog_requires_a_map():
    actor = WorldActor()
    room = _room(actor.world)
    holder = _character(actor.world, room)
    _hold(holder, spawn_compass(actor.world))  # a compass, not a map

    assert fog_fragments(actor.world, holder) == []


def test_fog_none_character():
    actor = WorldActor()
    assert fog_fragments(actor.world, None) == []


def test_fog_holder_without_a_room():
    actor = WorldActor()
    drifter = spawn_entity(
        actor.world, [IdentityComponent(name="drifter", kind="character"), CharacterComponent()]
    )
    _hold(drifter, spawn_field_map(actor.world))

    assert fog_fragments(actor.world, drifter) == []
