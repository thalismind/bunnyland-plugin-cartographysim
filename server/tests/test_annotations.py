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
    AnnotateMapHandler,
    ChartedRoom,
    MapAnnotatedEvent,
    MapAnnotationsComponent,
    MapComponent,
    MapNote,
    annotation_fragments,
    spawn_field_map,
)

EPOCH = 100


def _room(world, *, title="Grotto"):
    return spawn_entity(world, [RoomComponent(title=title)])


def _character(world, room=None, name="Vin"):
    character = spawn_entity(
        world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    )
    if room is not None:
        room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def _map(world, character, charted_rooms=()):
    field_map = spawn_field_map(world)
    character.add_relationship(Contains(mode=ContainmentMode.INVENTORY), field_map.id)
    if charted_rooms:
        replace_component(
            field_map,
            MapComponent(
                rooms=tuple(ChartedRoom(room_id=str(r.id), title="R") for r in charted_rooms)
            ),
        )
    return field_map


def _ctx(actor):
    return HandlerContext(world=actor.world, epoch=EPOCH)


def _cmd(character_id, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type="annotate-map",
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _annotate(actor, character_id, payload):
    return execute_handler(AnnotateMapHandler(), _ctx(actor), _cmd(character_id, payload))


# -- value object -----------------------------------------------------------------------


def test_component_notes_for_and_with_note_dedup():
    note = MapNote(room_id="entity_1", text="here be danger", category="danger")
    component = MapAnnotationsComponent().with_note(note)
    assert component.notes_for("entity_1") == (note,)
    assert component.notes_for("entity_2") == ()
    # Adding the identical note again does not duplicate it.
    assert component.with_note(note) is component


def test_component_keeps_notes_sorted():
    a = MapNote(room_id="entity_2", text="b", category="note")
    b = MapNote(room_id="entity_1", text="a", category="note")
    component = MapAnnotationsComponent().with_note(a).with_note(b)
    assert [n.room_id for n in component.notes] == ["entity_1", "entity_2"]


# -- happy path -------------------------------------------------------------------------


def test_annotate_pins_a_note_to_the_charted_room():
    actor = WorldActor()
    room = _room(actor.world)
    scribe = _character(actor.world, room)
    field_map = _map(actor.world, scribe, charted_rooms=(room,))

    result = _annotate(actor, scribe.id, {"note": "cache buried here", "category": "cache"})

    assert result.ok
    notes = field_map.get_component(MapAnnotationsComponent).notes_for(str(room.id))
    assert notes[0].text == "cache buried here"
    assert notes[0].category == "cache"
    event = result.events[0]
    assert isinstance(event, MapAnnotatedEvent)
    assert event.room_id_annotated == str(room.id)
    assert event.category == "cache"


def test_annotate_defaults_category_to_note():
    actor = WorldActor()
    room = _room(actor.world)
    scribe = _character(actor.world, room)
    field_map = _map(actor.world, scribe, charted_rooms=(room,))

    _annotate(actor, scribe.id, {"note": "just a note"})

    note = field_map.get_component(MapAnnotationsComponent).notes_for(str(room.id))[0]
    assert note.category == "note"


def test_annotate_appends_to_existing_annotations():
    actor = WorldActor()
    room = _room(actor.world)
    scribe = _character(actor.world, room)
    field_map = _map(actor.world, scribe, charted_rooms=(room,))

    _annotate(actor, scribe.id, {"note": "first"})
    _annotate(actor, scribe.id, {"note": "second"})

    notes = field_map.get_component(MapAnnotationsComponent).notes_for(str(room.id))
    assert {n.text for n in notes} == {"first", "second"}


def test_annotate_blank_category_falls_back_to_note():
    actor = WorldActor()
    room = _room(actor.world)
    scribe = _character(actor.world, room)
    field_map = _map(actor.world, scribe, charted_rooms=(room,))

    _annotate(actor, scribe.id, {"note": "x", "category": "   "})

    note = field_map.get_component(MapAnnotationsComponent).notes_for(str(room.id))[0]
    assert note.category == "note"


# -- rejections -------------------------------------------------------------------------


def test_annotate_rejects_invalid_character():
    actor = WorldActor()
    result = _annotate(actor, "???", {"note": "x"})
    assert not result.ok
    assert result.reason == "invalid character id"


def test_annotate_rejects_without_a_map():
    actor = WorldActor()
    room = _room(actor.world)
    scribe = _character(actor.world, room)
    result = _annotate(actor, scribe.id, {"note": "x"})
    assert not result.ok
    assert result.reason == "you need a field map to annotate"


def test_annotate_rejects_without_a_room():
    actor = WorldActor()
    scribe = _character(actor.world)  # nowhere
    _map(actor.world, scribe)
    result = _annotate(actor, scribe.id, {"note": "x"})
    assert not result.ok
    assert result.reason == "you are not in a room"


def test_annotate_rejects_uncharted_room():
    actor = WorldActor()
    room = _room(actor.world)
    scribe = _character(actor.world, room)
    _map(actor.world, scribe)  # room not charted
    result = _annotate(actor, scribe.id, {"note": "x"})
    assert not result.ok
    assert result.reason == "you can only annotate a room you have charted"


def test_annotate_rejects_blank_note():
    actor = WorldActor()
    room = _room(actor.world)
    scribe = _character(actor.world, room)
    _map(actor.world, scribe, charted_rooms=(room,))
    result = _annotate(actor, scribe.id, {"note": "   "})
    assert not result.ok
    assert result.reason == "annotation text is required"


def test_annotate_rejects_missing_note():
    actor = WorldActor()
    room = _room(actor.world)
    scribe = _character(actor.world, room)
    _map(actor.world, scribe, charted_rooms=(room,))
    result = _annotate(actor, scribe.id, {})
    assert not result.ok
    assert result.reason == "annotation text is required"


# -- fragments --------------------------------------------------------------------------


def test_annotation_fragment_shows_notes_here():
    actor = WorldActor()
    room = _room(actor.world)
    scribe = _character(actor.world, room)
    _map(actor.world, scribe, charted_rooms=(room,))
    _annotate(actor, scribe.id, {"note": "danger here", "category": "danger"})

    lines = annotation_fragments(actor.world, scribe)
    assert lines == ["Your map note here (danger): danger here"]


def test_annotation_fragment_empty_when_no_map_or_none():
    actor = WorldActor()
    room = _room(actor.world)
    scribe = _character(actor.world, room)
    assert annotation_fragments(actor.world, None) == []
    assert annotation_fragments(actor.world, scribe) == []  # no map


def test_annotation_fragment_empty_without_notes_component():
    actor = WorldActor()
    room = _room(actor.world)
    scribe = _character(actor.world, room)
    _map(actor.world, scribe, charted_rooms=(room,))  # map, but no annotations yet
    assert annotation_fragments(actor.world, scribe) == []


def test_annotation_fragment_empty_when_not_in_a_room():
    actor = WorldActor()
    room = _room(actor.world)
    scribe = _character(actor.world, room)
    _map(actor.world, scribe, charted_rooms=(room,))
    _annotate(actor, scribe.id, {"note": "x"})
    # Move the scribe out of any room.
    room.remove_relationship(Contains, scribe.id)
    assert annotation_fragments(actor.world, scribe) == []
