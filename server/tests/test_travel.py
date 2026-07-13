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
from bunnyland.core.ecs import container_of, replace_component
from bunnyland.core.edges import ExitTo
from bunnyland.core.handlers import HandlerContext
from conftest import execute_handler

from bunnyland_cartographysim import (
    MapComponent,
    TravelArrivedEvent,
    TravelConsequence,
    TravelPlanComponent,
    TravelStartedEvent,
    TravelStepEvent,
    TravelToHandler,
    plan_route,
    record_for_room,
    spawn_field_map,
)

EPOCH = 100


def _room(world, *, title="Room"):
    return spawn_entity(world, [RoomComponent(title=title)])


def _exit(a, b, *, direction, back=None):
    a.add_relationship(ExitTo(direction=direction), b.id)
    if back is not None:
        b.add_relationship(ExitTo(direction=back), a.id)


def _character(world, room=None, name="Vin"):
    character = spawn_entity(
        world, [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    )
    if room is not None:
        room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def _map_charting(world, character, rooms):
    """Give ``character`` a held field map already charting every room in ``rooms``."""
    field_map = spawn_field_map(world)
    character.add_relationship(Contains(mode=ContainmentMode.INVENTORY), field_map.id)
    replace_component(field_map, MapComponent(rooms=tuple(record_for_room(room) for room in rooms)))
    return field_map


def _cmd(character_id, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type="travel-to",
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _ctx(actor):
    return HandlerContext(world=actor.world, epoch=EPOCH)


def _travel(actor, character_id, destination_id):
    return execute_handler(
        TravelToHandler(), _ctx(actor), _cmd(character_id, {"destination_id": destination_id})
    )


# -- BFS routing ------------------------------------------------------------------------


def test_plan_route_finds_shortest_path():
    actor = WorldActor()
    a, b, c = (_room(actor.world, title=t) for t in "ABC")
    _exit(a, b, direction="east")
    _exit(b, c, direction="east")
    map_component = MapComponent(rooms=tuple(record_for_room(r) for r in (a, b, c)))

    route = plan_route(map_component, str(a.id), str(c.id))

    assert route == [str(b.id), str(c.id)]


def test_plan_route_same_room_is_empty():
    actor = WorldActor()
    a = _room(actor.world)
    map_component = MapComponent(rooms=(record_for_room(a),))
    assert plan_route(map_component, str(a.id), str(a.id)) == []


def test_plan_route_none_when_disconnected():
    actor = WorldActor()
    a = _room(actor.world, title="A")
    b = _room(actor.world, title="B")  # charted but no charted path from A
    map_component = MapComponent(rooms=(record_for_room(a), record_for_room(b)))
    assert plan_route(map_component, str(a.id), str(b.id)) is None


# -- travel-to handler (happy) ----------------------------------------------------------


def test_travel_to_plans_a_route():
    actor = WorldActor()
    a, b, c = (_room(actor.world, title=t) for t in "ABC")
    _exit(a, b, direction="east")
    _exit(b, c, direction="east")
    traveller = _character(actor.world, a)
    _map_charting(actor.world, traveller, (a, b, c))

    result = _travel(actor, traveller.id, str(c.id))

    assert result.ok
    plan = traveller.get_component(TravelPlanComponent)
    assert plan.destination_id == str(c.id)
    assert plan.route == (str(b.id), str(c.id))
    assert isinstance(result.events[0], TravelStartedEvent)
    assert result.events[0].hops == 2


# -- travel consequence -----------------------------------------------------------------


def test_travel_consequence_walks_one_hop_per_tick():
    actor = WorldActor()
    a, b, c = (_room(actor.world, title=t) for t in "ABC")
    _exit(a, b, direction="east")
    _exit(b, c, direction="east")
    traveller = _character(actor.world, a)
    _map_charting(actor.world, traveller, (a, b, c))
    _travel(actor, traveller.id, str(c.id))
    consequence = TravelConsequence()

    step = consequence.process(actor.world, EPOCH + 1)
    assert container_of(traveller) == b.id
    assert isinstance(step[0], TravelStepEvent)
    assert step[0].to_room_id == str(b.id)
    assert step[0].direction == "east"
    assert traveller.has_component(TravelPlanComponent)

    arrive = consequence.process(actor.world, EPOCH + 2)
    assert container_of(traveller) == c.id
    assert isinstance(arrive[0], TravelArrivedEvent)
    assert arrive[0].destination_id == str(c.id)
    assert not traveller.has_component(TravelPlanComponent)


def test_travel_consequence_aborts_when_a_charted_edge_vanishes():
    actor = WorldActor()
    a, b = _room(actor.world, title="A"), _room(actor.world, title="B")
    _exit(a, b, direction="east")
    traveller = _character(actor.world, a)
    _map_charting(actor.world, traveller, (a, b))
    TravelToHandler().execute(_ctx(actor), _cmd(traveller.id, {"destination_id": str(b.id)}))
    a.remove_relationship(ExitTo, b.id)  # the way is gone

    events = TravelConsequence().process(actor.world, EPOCH + 1)

    assert events == []
    assert container_of(traveller) == a.id
    assert not traveller.has_component(TravelPlanComponent)


# -- travel-to handler (rejections) -----------------------------------------------------


def test_travel_to_rejects_invalid_character():
    actor = WorldActor()
    result = TravelToHandler().execute(_ctx(actor), _cmd("???", {"destination_id": "entity_1"}))
    assert not result.ok
    assert result.reason == "invalid character id"


def test_travel_to_rejects_without_a_map():
    actor = WorldActor()
    room = _room(actor.world)
    traveller = _character(actor.world, room)
    result = _travel(actor, traveller.id, str(room.id))
    assert not result.ok
    assert result.reason == "you need a field map to fast-travel"


def test_travel_to_rejects_character_without_a_room():
    actor = WorldActor()
    a = _room(actor.world)
    traveller = _character(actor.world)  # holds a map but stands nowhere
    _map_charting(actor.world, traveller, (a,))
    result = _travel(actor, traveller.id, str(a.id))
    assert not result.ok
    assert result.reason == "you are not in a room"


def test_travel_to_rejects_invalid_destination():
    actor = WorldActor()
    a = _room(actor.world)
    traveller = _character(actor.world, a)
    _map_charting(actor.world, traveller, (a,))
    result = TravelToHandler().execute(_ctx(actor), _cmd(traveller.id, {"destination_id": "???"}))
    assert not result.ok
    assert result.reason == "invalid destination id"


def test_travel_to_rejects_missing_destination():
    actor = WorldActor()
    a = _room(actor.world)
    traveller = _character(actor.world, a)
    _map_charting(actor.world, traveller, (a,))
    result = TravelToHandler().execute(
        _ctx(actor), _cmd(traveller.id, {"destination_id": "entity_9999"})
    )
    assert not result.ok
    assert result.reason == "destination does not exist"


def test_travel_to_rejects_current_room():
    actor = WorldActor()
    a = _room(actor.world)
    traveller = _character(actor.world, a)
    _map_charting(actor.world, traveller, (a,))
    result = _travel(actor, traveller.id, str(a.id))
    assert not result.ok
    assert result.reason == "you are already there"


def test_travel_to_rejects_uncharted_destination():
    actor = WorldActor()
    a, b = _room(actor.world, title="A"), _room(actor.world, title="B")
    _exit(a, b, direction="east")
    traveller = _character(actor.world, a)
    _map_charting(actor.world, traveller, (a,))  # b never charted
    result = _travel(actor, traveller.id, str(b.id))
    assert not result.ok
    assert result.reason == "you have not charted that destination"


def test_travel_to_rejects_unreachable_destination():
    actor = WorldActor()
    a, b = _room(actor.world, title="A"), _room(actor.world, title="B")
    _exit(a, b, direction="east")
    traveller = _character(actor.world, a)
    # Both charted, but the map records no exit connecting them (charted separately).
    field_map = _map_charting(actor.world, traveller, ())
    from bunnyland_cartographysim import ChartedRoom

    replace_component(
        field_map,
        MapComponent(
            rooms=(
                ChartedRoom(room_id=str(a.id), title="A"),
                ChartedRoom(room_id=str(b.id), title="B"),
            )
        ),
    )
    result = _travel(actor, traveller.id, str(b.id))
    assert not result.ok
    assert result.reason == "no known route to that destination"
