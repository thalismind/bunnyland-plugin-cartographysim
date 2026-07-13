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
from bunnyland.core.ecs import replace_component
from bunnyland.core.handlers import HandlerContext
from conftest import execute_handler

from bunnyland_cartographysim import (
    ChartedRoom,
    MapComponent,
    MapSharedEvent,
    SharedWith,
    ShareMapHandler,
    is_shared_with,
    maps_shared_with,
    share_fragments,
    spawn_field_map,
)

EPOCH = 100


def _room(world, *, title="Camp"):
    return spawn_entity(world, [RoomComponent(title=title)])


def _character(world, room=None, name="Vin"):
    character = spawn_entity(
        world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    )
    if room is not None:
        room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def _map(world, character, rooms=()):
    field_map = spawn_field_map(world)
    character.add_relationship(Contains(mode=ContainmentMode.INVENTORY), field_map.id)
    if rooms:
        replace_component(field_map, MapComponent(rooms=tuple(rooms)))
    return field_map


def _ctx(actor):
    return HandlerContext(world=actor.world, epoch=EPOCH)


def _cmd(character_id, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type="share-map",
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _share(actor, sharer_id, recipient_id):
    return execute_handler(
        ShareMapHandler(), _ctx(actor), _cmd(sharer_id, {"recipient_id": str(recipient_id)})
    )


# -- happy path -------------------------------------------------------------------------


def test_share_map_creates_a_shared_edge_and_event():
    actor = WorldActor()
    room = _room(actor.world)
    sharer = _character(actor.world, room, name="Vin")
    field_map = _map(actor.world, sharer, rooms=(ChartedRoom(room_id=str(room.id), title="Camp"),))
    recipient = _character(actor.world, room, name="Elend")

    result = _share(actor, sharer.id, recipient.id)

    assert result.ok
    assert is_shared_with(field_map, str(recipient.id))
    event = result.events[0]
    assert isinstance(event, MapSharedEvent)
    assert event.recipient_id == str(recipient.id)
    assert event.sharer_id == str(sharer.id)
    assert event.map_id == str(field_map.id)
    edge_meta = next(edge for edge, _t in field_map.get_relationships(SharedWith))
    assert edge_meta.shared_by == str(sharer.id)
    assert edge_meta.since_epoch == EPOCH


def test_maps_shared_with_lists_shared_maps():
    actor = WorldActor()
    room = _room(actor.world)
    sharer = _character(actor.world, room, name="Vin")
    field_map = _map(actor.world, sharer, rooms=(ChartedRoom(room_id=str(room.id), title="Camp"),))
    recipient = _character(actor.world, room, name="Elend")
    _share(actor, sharer.id, recipient.id)

    shared = maps_shared_with(actor.world, recipient)
    assert [m.id for m in shared] == [field_map.id]


# -- rejections -------------------------------------------------------------------------


def test_share_rejects_invalid_character():
    actor = WorldActor()
    result = _share(actor, "???", "entity_1")
    assert not result.ok
    assert result.reason == "invalid character id"


def test_share_rejects_without_a_map():
    actor = WorldActor()
    room = _room(actor.world)
    sharer = _character(actor.world, room)
    recipient = _character(actor.world, room, name="Elend")
    result = _share(actor, sharer.id, recipient.id)
    assert not result.ok
    assert result.reason == "you need a field map to share"


def test_share_rejects_invalid_recipient_id():
    actor = WorldActor()
    room = _room(actor.world)
    sharer = _character(actor.world, room)
    _map(actor.world, sharer)
    result = ShareMapHandler().execute(_ctx(actor), _cmd(sharer.id, {"recipient_id": "???"}))
    assert not result.ok
    assert result.reason == "invalid recipient id"


def test_share_rejects_missing_recipient():
    actor = WorldActor()
    room = _room(actor.world)
    sharer = _character(actor.world, room)
    _map(actor.world, sharer)
    result = ShareMapHandler().execute(
        _ctx(actor), _cmd(sharer.id, {"recipient_id": "entity_9999"})
    )
    assert not result.ok
    assert result.reason == "that character is not here"


def test_share_rejects_unreachable_recipient():
    actor = WorldActor()
    here = _room(actor.world)
    there = _room(actor.world, title="Far")
    sharer = _character(actor.world, here)
    _map(actor.world, sharer)
    stranger = _character(actor.world, there, name="Stranger")
    result = _share(actor, sharer.id, stranger.id)
    assert not result.ok
    assert result.reason == "that character is not here"


def test_share_rejects_sharing_with_self():
    actor = WorldActor()
    room = _room(actor.world)
    sharer = _character(actor.world, room)
    _map(actor.world, sharer)
    result = _share(actor, sharer.id, sharer.id)
    assert not result.ok
    assert result.reason == "you cannot share a map with yourself"


def test_share_rejects_non_character_recipient():
    actor = WorldActor()
    room = _room(actor.world)
    sharer = _character(actor.world, room)
    _map(actor.world, sharer)
    rock = spawn_entity(actor.world, [IdentityComponent(name="rock", kind="item")])
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), rock.id)
    result = _share(actor, sharer.id, rock.id)
    assert not result.ok
    assert result.reason == "you can only share a map with a character"


def test_share_rejects_already_shared():
    actor = WorldActor()
    room = _room(actor.world)
    sharer = _character(actor.world, room)
    _map(actor.world, sharer)
    recipient = _character(actor.world, room, name="Elend")
    assert _share(actor, sharer.id, recipient.id).ok
    result = _share(actor, sharer.id, recipient.id)
    assert not result.ok
    assert result.reason == "that map is already shared with them"


# -- fragments --------------------------------------------------------------------------


def test_share_fragment_tells_recipient_and_sharer():
    actor = WorldActor()
    room = _room(actor.world)
    sharer = _character(actor.world, room, name="Vin")
    _map(
        actor.world,
        sharer,
        rooms=(
            ChartedRoom(room_id=str(room.id), title="Camp"),
            ChartedRoom(room_id="entity_777", title="Ridge"),
        ),
    )
    recipient = _character(actor.world, room, name="Elend")
    _share(actor, sharer.id, recipient.id)

    recipient_lines = share_fragments(actor.world, recipient)
    assert recipient_lines == ["A shared field map grants you 2 charted rooms."]

    sharer_lines = share_fragments(actor.world, sharer)
    assert sharer_lines == ["You have shared your field map with 1 explorer."]


def test_share_fragment_singular_room_and_plural_explorers():
    actor = WorldActor()
    room = _room(actor.world)
    sharer = _character(actor.world, room, name="Vin")
    _map(actor.world, sharer, rooms=(ChartedRoom(room_id=str(room.id), title="Camp"),))
    a = _character(actor.world, room, name="A")
    b = _character(actor.world, room, name="B")
    _share(actor, sharer.id, a.id)
    _share(actor, sharer.id, b.id)

    assert share_fragments(actor.world, a) == ["A shared field map grants you 1 charted room."]
    assert share_fragments(actor.world, sharer) == [
        "You have shared your field map with 2 explorers."
    ]


def test_share_fragment_empty_for_none_and_unshared():
    actor = WorldActor()
    room = _room(actor.world)
    loner = _character(actor.world, room)
    assert share_fragments(actor.world, None) == []
    assert share_fragments(actor.world, loner) == []
