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
    MapComponent,
    MappingConsequence,
    spawn_field_map,
)

EPOCH = 100


def _room(world, *, title="Cellar", biome="cavern"):
    return spawn_entity(world, [RoomComponent(title=title, biome=biome)])


def _link(room, entity, mode=ContainmentMode.ROOM_CONTENT):
    room.add_relationship(Contains(mode=mode), entity.id)


def _exit(a, b, *, direction="north", label="a door"):
    a.add_relationship(ExitTo(direction=direction, label=label), b.id)


def _character(world, room, name="Vin"):
    character = spawn_entity(
        world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    )
    _link(room, character)
    return character


def _map(entity):
    return entity.get_component(MapComponent)


def test_loose_map_charts_the_room_it_rests_in():
    actor = WorldActor()
    room = _room(actor.world)
    field_map = spawn_field_map(actor.world, room_id=room.id)

    MappingConsequence().process(actor.world, EPOCH)

    charted = _map(field_map).get(str(room.id))
    assert charted is not None
    assert charted.title == "Cellar"
    assert charted.biome == "cavern"


def test_held_map_charts_its_holders_room():
    actor = WorldActor()
    room = _room(actor.world)
    holder = _character(actor.world, room)
    field_map = spawn_field_map(actor.world)
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), field_map.id)

    MappingConsequence().process(actor.world, EPOCH)

    assert str(room.id) in _map(field_map).charted_ids()


def test_charting_records_the_rooms_exits():
    actor = WorldActor()
    here = _room(actor.world, title="Hall")
    there = _room(actor.world, title="Vault")
    _exit(here, there, direction="east", label="an iron gate")
    field_map = spawn_field_map(actor.world, room_id=here.id)

    MappingConsequence().process(actor.world, EPOCH)

    record = _map(field_map).get(str(here.id))
    assert len(record.exits) == 1
    assert record.exits[0].direction == "east"
    assert record.exits[0].label == "an iron gate"
    assert record.exits[0].to_room_id == str(there.id)


def test_map_charts_new_rooms_as_holder_moves():
    actor = WorldActor()
    here = _room(actor.world, title="Hall")
    there = _room(actor.world, title="Vault")
    _exit(here, there, direction="east")
    holder = _character(actor.world, here)
    field_map = spawn_field_map(actor.world)
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), field_map.id)
    consequence = MappingConsequence()

    consequence.process(actor.world, EPOCH)
    here.remove_relationship(Contains, holder.id)
    there.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), holder.id)
    consequence.process(actor.world, EPOCH + 1)

    assert _map(field_map).charted_ids() == frozenset({str(here.id), str(there.id)})


def test_charting_is_idempotent_for_an_unchanged_room():
    actor = WorldActor()
    room = _room(actor.world)
    field_map = spawn_field_map(actor.world, room_id=room.id)
    consequence = MappingConsequence()

    consequence.process(actor.world, EPOCH)
    first = _map(field_map)
    consequence.process(actor.world, EPOCH + 1)
    second = _map(field_map)

    assert first is second  # unchanged room -> no replace_component churn


def test_uncontained_map_charts_nothing():
    actor = WorldActor()
    field_map = spawn_field_map(actor.world)  # not in any room

    assert MappingConsequence().process(actor.world, EPOCH) == []
    assert _map(field_map).rooms == ()


def test_map_fragment_reports_blank_map():
    from bunnyland_cartographysim import map_fragments

    actor = WorldActor()
    room = _room(actor.world)
    holder = _character(actor.world, room)
    field_map = spawn_field_map(actor.world)
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), field_map.id)

    lines = map_fragments(actor.world, holder)

    assert lines == ["Your field map is blank; you have charted no rooms yet."]


def test_map_fragment_reports_charted_count():
    from bunnyland_cartographysim import map_fragments

    actor = WorldActor()
    room = _room(actor.world)
    holder = _character(actor.world, room)
    field_map = spawn_field_map(actor.world)
    holder.add_relationship(Contains(mode=ContainmentMode.INVENTORY), field_map.id)

    MappingConsequence().process(actor.world, EPOCH)
    lines = map_fragments(actor.world, holder)

    assert lines == ["Your field map shows 1 charted room."]


def test_map_fragment_empty_without_a_map():
    from bunnyland_cartographysim import map_fragments

    actor = WorldActor()
    room = _room(actor.world)
    holder = _character(actor.world, room)

    assert map_fragments(actor.world, holder) == []
    assert map_fragments(actor.world, None) == []
