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
from bunnyland.core.commands import CommandCost, Lane, build_submitted_command
from bunnyland.core.handlers import HandlerContext

from bunnyland_cartographysim import LandmarkComponent, NameLandmarkHandler, landmark_fragments

EPOCH = 100


def _room(world, *, title="Clearing"):
    return spawn_entity(world, [RoomComponent(title=title)])


def _character(world, room, name="Vin"):
    character = spawn_entity(
        world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def _cmd(character_id, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type="name-landmark",
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _ctx(actor):
    return HandlerContext(world=actor.world, epoch=EPOCH)


def test_name_landmark_pins_a_name_to_the_room():
    actor = WorldActor()
    room = _room(actor.world)
    caster = _character(actor.world, room)

    result = NameLandmarkHandler().execute(
        _ctx(actor), _cmd(caster.id, {"name": "Traveller's Rest"})
    )

    assert result.ok
    assert room.get_component(LandmarkComponent).name == "Traveller's Rest"
    assert result.events[0].room_id_named == str(room.id)
    assert result.events[0].name == "Traveller's Rest"


def test_name_landmark_renames_an_existing_landmark():
    actor = WorldActor()
    room = _room(actor.world)
    room.add_component(LandmarkComponent(name="Old Name"))
    caster = _character(actor.world, room)

    result = NameLandmarkHandler().execute(_ctx(actor), _cmd(caster.id, {"name": "New Name"}))

    assert result.ok
    assert room.get_component(LandmarkComponent).name == "New Name"


def test_name_landmark_rejects_invalid_character():
    actor = WorldActor()
    result = NameLandmarkHandler().execute(_ctx(actor), _cmd("???", {"name": "X"}))
    assert not result.ok
    assert result.reason == "invalid character id"


def test_name_landmark_rejects_missing_character():
    actor = WorldActor()
    result = NameLandmarkHandler().execute(_ctx(actor), _cmd("entity_9999", {"name": "X"}))
    assert not result.ok
    assert result.reason == "character does not exist"


def test_name_landmark_rejects_character_without_a_room():
    actor = WorldActor()
    drifter = spawn_entity(
        actor.world, [IdentityComponent(name="drifter", kind="character"), CharacterComponent()]
    )
    result = NameLandmarkHandler().execute(_ctx(actor), _cmd(drifter.id, {"name": "X"}))
    assert not result.ok
    assert result.reason == "you are not in a room"


def test_name_landmark_rejects_blank_name():
    actor = WorldActor()
    room = _room(actor.world)
    caster = _character(actor.world, room)

    result = NameLandmarkHandler().execute(_ctx(actor), _cmd(caster.id, {"name": "   "}))

    assert not result.ok
    assert result.reason == "landmark name is required"


def test_name_landmark_rejects_missing_name():
    actor = WorldActor()
    room = _room(actor.world)
    caster = _character(actor.world, room)

    result = NameLandmarkHandler().execute(_ctx(actor), _cmd(caster.id, {}))

    assert not result.ok
    assert result.reason == "landmark name is required"


def test_landmark_fragment_shows_the_rooms_name():
    actor = WorldActor()
    room = _room(actor.world)
    room.add_component(LandmarkComponent(name="the Crossroads"))
    visitor = _character(actor.world, room)

    lines = landmark_fragments(actor.world, visitor)

    assert lines == ["This place is known as 'the Crossroads'."]


def test_landmark_fragment_empty_in_plain_room():
    actor = WorldActor()
    room = _room(actor.world)
    visitor = _character(actor.world, room)

    assert landmark_fragments(actor.world, visitor) == []


def test_landmark_fragment_none_character():
    actor = WorldActor()
    assert landmark_fragments(actor.world, None) == []
