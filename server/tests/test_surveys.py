from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RegionComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.commands import CommandCost, Lane, build_submitted_command
from bunnyland.core.ecs import replace_component
from bunnyland.core.handlers import HandlerContext
from conftest import execute_handler

from bunnyland_cartographysim import (
    ChartedExit,
    ChartedRoom,
    LandmarkComponent,
    LastSurveyComponent,
    LocatedInRegion,
    MapComponent,
    RegionSurvey,
    RegionSurveyedEvent,
    SurveyMemoryReactor,
    SurveyRegionHandler,
    spawn_field_map,
    survey_fragments,
    survey_region,
    survey_summary,
)

EPOCH = 100


def _room(world, *, title="Room", biome="forest"):
    return spawn_entity(world, [RoomComponent(title=title, biome=biome)])


def _character(world, room=None, name="Vin"):
    character = spawn_entity(
        world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    )
    if room is not None:
        room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def _charted(room, exits=()):
    return ChartedRoom(
        room_id=str(room.id),
        title=room.get_component(RoomComponent).title,
        biome=room.get_component(RoomComponent).biome,
        exits=tuple(exits),
    )


def _map(world, character, records):
    field_map = spawn_field_map(world)
    character.add_relationship(Contains(mode=ContainmentMode.INVENTORY), field_map.id)
    replace_component(field_map, MapComponent(rooms=tuple(records)))
    return field_map


def _ctx(actor):
    return HandlerContext(world=actor.world, epoch=EPOCH)


def _cmd(character_id, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type="survey-region",
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _survey(actor, character_id, payload=None):
    return execute_handler(
        SurveyRegionHandler(), _ctx(actor), _cmd(character_id, payload or {})
    )


# -- BFS survey -------------------------------------------------------------------------


def test_survey_region_walks_the_charted_graph():
    actor = WorldActor()
    a = _room(actor.world, title="A", biome="forest")
    b = _room(actor.world, title="B", biome="forest")
    c = _room(actor.world, title="C", biome="swamp")
    records = (
        _charted(a, [ChartedExit(direction="east", to_room_id=str(b.id))]),
        _charted(b, [ChartedExit(direction="east", to_room_id=str(c.id))]),
        _charted(c),
    )
    map_component = MapComponent(rooms=records)

    survey = survey_region(actor.world, map_component, str(a.id), radius=1)
    assert set(survey.room_ids) == {str(a.id), str(b.id)}  # c is 2 hops out

    survey2 = survey_region(actor.world, map_component, str(a.id), radius=2)
    assert set(survey2.room_ids) == {str(a.id), str(b.id), str(c.id)}
    # biome tally: forest x2, swamp x1
    assert survey2.biomes[0] == ("forest", 2)


def test_survey_region_collects_landmarks_and_regions():
    actor = WorldActor()
    a = _room(actor.world, title="A")
    a.add_component(LandmarkComponent(name="the Crossroads"))
    region = spawn_entity(
        actor.world,
        [RegionComponent(name="the Whispering Wilds", climate="forest")],
    )
    a.add_relationship(LocatedInRegion(), region.id)
    map_component = MapComponent(rooms=(_charted(a),))

    survey = survey_region(actor.world, map_component, str(a.id), radius=2)
    assert survey.landmarks == ("the Crossroads",)
    assert survey.regions == ("the Whispering Wilds",)


def test_survey_region_ignores_exits_to_uncharted_rooms():
    actor = WorldActor()
    a = _room(actor.world, title="A")
    records = (_charted(a, [ChartedExit(direction="north", to_room_id="entity_9999")]),)
    survey = survey_region(actor.world, MapComponent(rooms=records), str(a.id), radius=3)
    assert set(survey.room_ids) == {str(a.id)}


def test_survey_region_empty_when_origin_uncharted():
    actor = WorldActor()
    a = _room(actor.world)
    survey = survey_region(actor.world, MapComponent(rooms=()), str(a.id), radius=2)
    assert survey.room_ids == ()


def test_survey_region_handles_a_diamond_without_revisiting():
    actor = WorldActor()
    a, b, c, d = (_room(actor.world, title=t) for t in "ABCD")
    records = (
        _charted(
            a,
            [
                ChartedExit(direction="east", to_room_id=str(b.id)),
                ChartedExit(direction="west", to_room_id=str(c.id)),
            ],
        ),
        _charted(b, [ChartedExit(direction="south", to_room_id=str(d.id))]),
        _charted(c, [ChartedExit(direction="south", to_room_id=str(d.id))]),
        _charted(d),
    )
    survey = survey_region(actor.world, MapComponent(rooms=records), str(a.id), radius=3)
    # d is reachable via both b and c but counted once.
    assert survey.room_ids.count(str(d.id)) == 1
    assert set(survey.room_ids) == {str(a.id), str(b.id), str(c.id), str(d.id)}


def test_survey_region_tolerates_charted_ids_without_live_entities():
    actor = WorldActor()
    a = _room(actor.world, title="A")
    # A charted room whose id no longer maps to a live entity is still tallied by biome.
    records = (
        _charted(a, [ChartedExit(direction="north", to_room_id="entity_8888")]),
        ChartedRoom(room_id="entity_8888", title="Ghost", biome="void"),
    )
    survey = survey_region(actor.world, MapComponent(rooms=records), str(a.id), radius=2)
    assert "entity_8888" in survey.room_ids
    assert survey.landmarks == ()


# -- summary ----------------------------------------------------------------------------


def test_survey_summary_lists_everything():
    survey = RegionSurvey(
        origin_room_id="entity_1",
        radius=2,
        room_ids=("entity_1", "entity_2"),
        biomes=(("forest", 2),),
        landmarks=("the Crossroads",),
        regions=("the Whispering Wilds",),
    )
    text = survey_summary(survey)
    assert "2 rooms" in text
    assert "biomes: forest x2" in text
    assert "regions: the Whispering Wilds" in text
    assert "landmarks: the Crossroads" in text
    assert text.endswith(".")


def test_survey_summary_singular_room_and_minimal():
    survey = RegionSurvey(origin_room_id="entity_1", radius=1, room_ids=("entity_1",))
    text = survey_summary(survey)
    assert "1 room" in text
    assert "biomes" not in text


# -- handler happy ----------------------------------------------------------------------


def test_survey_handler_stamps_last_survey_and_emits_event():
    actor = WorldActor()
    a = _room(actor.world, title="A")
    b = _room(actor.world, title="B")
    surveyor = _character(actor.world, a)
    _map(
        actor.world,
        surveyor,
        (
            _charted(a, [ChartedExit(direction="east", to_room_id=str(b.id))]),
            _charted(b),
        ),
    )

    result = _survey(actor, surveyor.id, {"radius": 2})
    assert result.ok
    comp = surveyor.get_component(LastSurveyComponent)
    assert comp.room_count == 2
    assert comp.origin_room_id == str(a.id)
    event = result.events[0]
    assert isinstance(event, RegionSurveyedEvent)
    assert event.room_count == 2
    assert event.radius == 2


def test_survey_handler_defaults_radius():
    actor = WorldActor()
    a = _room(actor.world)
    surveyor = _character(actor.world, a)
    _map(actor.world, surveyor, (_charted(a),))
    result = _survey(actor, surveyor.id, {})
    assert result.ok
    assert result.events[0].radius == 2


# -- handler rejections -----------------------------------------------------------------


def test_survey_rejects_invalid_character():
    actor = WorldActor()
    result = _survey(actor, "???")
    assert not result.ok
    assert result.reason == "invalid character id"


def test_survey_rejects_without_a_map():
    actor = WorldActor()
    a = _room(actor.world)
    surveyor = _character(actor.world, a)
    result = _survey(actor, surveyor.id)
    assert not result.ok
    assert result.reason == "you need a field map to survey"


def test_survey_rejects_without_a_room():
    actor = WorldActor()
    a = _room(actor.world)
    surveyor = _character(actor.world)  # nowhere
    _map(actor.world, surveyor, (_charted(a),))
    result = _survey(actor, surveyor.id)
    assert not result.ok
    assert result.reason == "you are not in a room"


def test_survey_rejects_uncharted_origin():
    actor = WorldActor()
    a = _room(actor.world)
    surveyor = _character(actor.world, a)
    _map(actor.world, surveyor, ())  # a not charted
    result = _survey(actor, surveyor.id)
    assert not result.ok
    assert result.reason == "you can only survey from a charted room"


def test_survey_rejects_bad_radius():
    actor = WorldActor()
    a = _room(actor.world)
    surveyor = _character(actor.world, a)
    _map(actor.world, surveyor, (_charted(a),))
    for bad in (0, 9, True, "two"):
        result = _survey(actor, surveyor.id, {"radius": bad})
        assert not result.ok
        assert result.reason == "survey radius must be between 1 and 8"


# -- fragments --------------------------------------------------------------------------


def test_survey_fragment_first_person_only():
    actor = WorldActor()
    a = _room(actor.world)
    surveyor = _character(actor.world, a)
    _map(actor.world, surveyor, (_charted(a),))
    _survey(actor, surveyor.id, {"radius": 1})
    lines = survey_fragments(actor.world, surveyor)
    assert lines and "Region survey" in lines[0]


def test_survey_fragment_empty_without_component_or_none():
    actor = WorldActor()
    a = _room(actor.world)
    surveyor = _character(actor.world, a)
    assert survey_fragments(actor.world, None) == []
    assert survey_fragments(actor.world, surveyor) == []


def test_last_survey_component_is_first_person_only():
    from bunnyland.prompts.context import ComponentPromptContext, PromptPerspective

    actor = WorldActor()
    a = _room(actor.world)
    surveyor = _character(actor.world, a, name="Vin")
    other = _character(actor.world, a, name="Elend")
    comp = LastSurveyComponent(origin_room_id=str(a.id), room_count=1, summary="a survey")

    first = ComponentPromptContext.for_entity(
        actor.world, surveyor, perspective=PromptPerspective(viewer=surveyor)
    )
    assert comp.prompt_fragments(first) == ("a survey",)

    bystander = ComponentPromptContext.for_entity(
        actor.world, surveyor, perspective=PromptPerspective(viewer=other)
    )
    assert comp.prompt_fragments(bystander) == ()


# -- memory reactor ---------------------------------------------------------------------


class _FakeStore:
    def __init__(self):
        self.added = []

    def add(self, collection, *, text, tags=(), created_at_epoch=0, source="manual"):
        self.added.append((collection, text, tags, created_at_epoch, source))


def _survey_event():
    from bunnyland.core.events import event_base

    return RegionSurveyedEvent(
        **event_base(EPOCH),
        origin_room_id="entity_1",
        room_count=3,
        radius=2,
        summary="Region survey within 2 of a charted point: 3 rooms.",
    )


def test_survey_memory_reactor_journals_to_store():
    store = _FakeStore()
    reactor = SurveyMemoryReactor(lambda: store)
    reactor._on_survey(_survey_event())
    assert len(store.added) == 1
    collection, text, tags, epoch, source = store.added[0]
    assert collection == SurveyMemoryReactor.COLLECTION
    assert "3 rooms" in text
    assert epoch == EPOCH
    assert source == "survey"


def test_survey_memory_reactor_noop_without_store():
    reactor = SurveyMemoryReactor(lambda: None)
    # Should simply not raise when no store is installed.
    assert reactor._on_survey(_survey_event()) is None


def test_survey_memory_reactor_subscribes_and_fires():
    store = _FakeStore()
    actor = WorldActor()
    reactor = SurveyMemoryReactor(lambda: store)
    reactor.subscribe(actor.bus)

    a = _room(actor.world)
    surveyor = _character(actor.world, a)
    _map(actor.world, surveyor, (_charted(a),))
    result = _survey(actor, surveyor.id, {"radius": 1})
    # Deliver the emitted event through the bus.
    import asyncio

    for event in result.events:
        asyncio.run(actor.bus.publish(event))
    assert store.added  # the survey was journalled
