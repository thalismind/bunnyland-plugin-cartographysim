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
from pydantic.dataclasses import dataclass
from relics import Component

from bunnyland_cartographysim import (
    ChartedRoom,
    ExpeditionArrivedEvent,
    ExpeditionConsequence,
    ExpeditionLegEvent,
    ExpeditionPlanComponent,
    ExpeditionStartedEvent,
    LaunchExpeditionHandler,
    MapComponent,
    record_for_room,
    spawn_field_map,
)

EPOCH = 100


@dataclass(frozen=True)
class _FakeMount(Component):
    """Stand-in for a petsim mount marker component."""

    name: str = "pony"


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
    field_map = spawn_field_map(world)
    character.add_relationship(Contains(mode=ContainmentMode.INVENTORY), field_map.id)
    replace_component(field_map, MapComponent(rooms=tuple(record_for_room(r) for r in rooms)))
    return field_map


def _ctx(actor):
    return HandlerContext(world=actor.world, epoch=EPOCH)


def _cmd(character_id, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type="launch-expedition",
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _launch(actor, character_id, destination_id):
    return execute_handler(
        LaunchExpeditionHandler(),
        _ctx(actor),
        _cmd(character_id, {"destination_id": str(destination_id)}),
    )


# -- launch happy -----------------------------------------------------------------------


def test_launch_plans_an_expedition_on_foot():
    actor = WorldActor()
    a, b, c = (_room(actor.world, title=t) for t in "ABC")
    _exit(a, b, direction="east")
    _exit(b, c, direction="east")
    traveller = _character(actor.world, a)
    _map_charting(actor.world, traveller, (a, b, c))

    result = _launch(actor, traveller.id, c.id)
    assert result.ok
    plan = traveller.get_component(ExpeditionPlanComponent)
    assert plan.route == (str(b.id), str(c.id))
    assert plan.pace == 1
    event = result.events[0]
    assert isinstance(event, ExpeditionStartedEvent)
    assert event.hops == 2
    assert event.pace == 1


def test_launch_doubles_pace_while_leading_a_mount():
    actor = WorldActor()
    a, b, c = (_room(actor.world, title=t) for t in "ABC")
    _exit(a, b, direction="east")
    _exit(b, c, direction="east")
    traveller = _character(actor.world, a)
    _map_charting(actor.world, traveller, (a, b, c))
    mount = spawn_entity(
        actor.world, [IdentityComponent(name="pony", kind="creature"), _FakeMount()]
    )
    traveller.add_relationship(Contains(mode=ContainmentMode.INVENTORY), mount.id)

    # Inject the fake mount type so the connector does not need petsim installed.
    from bunnyland_cartographysim import expeditions

    plan_pace = expeditions.is_mounted(actor.world, traveller, (_FakeMount,))
    assert plan_pace is True

    # Drive the handler with the mount type wired via a monkeypatch of is_mounted.
    original = expeditions.is_mounted
    expeditions.is_mounted = lambda world, character: original(world, character, (_FakeMount,))
    try:
        result = _launch(actor, traveller.id, c.id)
    finally:
        expeditions.is_mounted = original
    assert result.events[0].pace == 2


# -- launch rejections ------------------------------------------------------------------


def test_launch_rejects_invalid_character():
    actor = WorldActor()
    result = _launch(actor, "???", "entity_1")
    assert not result.ok
    assert result.reason == "invalid character id"


def test_launch_rejects_without_a_map():
    actor = WorldActor()
    a = _room(actor.world)
    traveller = _character(actor.world, a)
    result = _launch(actor, traveller.id, a.id)
    assert not result.ok
    assert result.reason == "you need a field map to launch an expedition"


def test_launch_rejects_without_a_room():
    actor = WorldActor()
    a = _room(actor.world)
    traveller = _character(actor.world)  # nowhere
    _map_charting(actor.world, traveller, (a,))
    result = _launch(actor, traveller.id, a.id)
    assert not result.ok
    assert result.reason == "you are not in a room"


def test_launch_rejects_invalid_destination():
    actor = WorldActor()
    a = _room(actor.world)
    traveller = _character(actor.world, a)
    _map_charting(actor.world, traveller, (a,))
    result = LaunchExpeditionHandler().execute(
        _ctx(actor), _cmd(traveller.id, {"destination_id": "???"})
    )
    assert not result.ok
    assert result.reason == "invalid destination id"


def test_launch_rejects_already_there():
    actor = WorldActor()
    a = _room(actor.world)
    traveller = _character(actor.world, a)
    _map_charting(actor.world, traveller, (a,))
    result = _launch(actor, traveller.id, a.id)
    assert not result.ok
    assert result.reason == "you are already there"


def test_launch_rejects_uncharted_destination():
    actor = WorldActor()
    a, b = _room(actor.world, title="A"), _room(actor.world, title="B")
    _exit(a, b, direction="east")
    traveller = _character(actor.world, a)
    _map_charting(actor.world, traveller, (a,))  # b uncharted
    result = _launch(actor, traveller.id, b.id)
    assert not result.ok
    assert result.reason == "you have not charted that destination"


def test_launch_rejects_unreachable_destination():
    actor = WorldActor()
    a, b = _room(actor.world, title="A"), _room(actor.world, title="B")
    _exit(a, b, direction="east")
    traveller = _character(actor.world, a)
    field_map = _map_charting(actor.world, traveller, ())
    replace_component(
        field_map,
        MapComponent(
            rooms=(
                ChartedRoom(room_id=str(a.id), title="A"),
                ChartedRoom(room_id=str(b.id), title="B"),
            )
        ),
    )
    result = _launch(actor, traveller.id, b.id)
    assert not result.ok
    assert result.reason == "no known route to that destination"


# -- consequence ------------------------------------------------------------------------


def test_expedition_consequence_walks_one_hop_on_foot():
    actor = WorldActor()
    a, b, c = (_room(actor.world, title=t) for t in "ABC")
    _exit(a, b, direction="east")
    _exit(b, c, direction="east")
    traveller = _character(actor.world, a)
    _map_charting(actor.world, traveller, (a, b, c))
    _launch(actor, traveller.id, c.id)
    consequence = ExpeditionConsequence()

    events = consequence.process(actor.world, EPOCH + 1)
    assert container_of(traveller) == b.id
    assert isinstance(events[0], ExpeditionLegEvent)
    assert events[0].to_room_id == str(b.id)
    assert traveller.has_component(ExpeditionPlanComponent)

    arrive = consequence.process(actor.world, EPOCH + 2)
    assert container_of(traveller) == c.id
    assert isinstance(arrive[-1], ExpeditionArrivedEvent)
    assert not traveller.has_component(ExpeditionPlanComponent)


def test_expedition_consequence_covers_two_hops_when_mounted():
    actor = WorldActor()
    a, b, c = (_room(actor.world, title=t) for t in "ABC")
    _exit(a, b, direction="east")
    _exit(b, c, direction="east")
    traveller = _character(actor.world, a)
    _map_charting(actor.world, traveller, (a, b, c))
    replace_component(
        traveller,
        ExpeditionPlanComponent(destination_id=str(c.id), route=(str(b.id), str(c.id)), pace=2),
    )
    events = ExpeditionConsequence().process(actor.world, EPOCH + 1)
    # Two hops in one tick -> arrives immediately.
    assert container_of(traveller) == c.id
    assert isinstance(events[-1], ExpeditionArrivedEvent)


def test_expedition_consequence_persists_remaining_hops_between_ticks():
    actor = WorldActor()
    a, b, c, d = (_room(actor.world, title=t) for t in "ABCD")
    _exit(a, b, direction="east")
    _exit(b, c, direction="east")
    _exit(c, d, direction="east")
    traveller = _character(actor.world, a)
    _map_charting(actor.world, traveller, (a, b, c, d))
    replace_component(
        traveller,
        ExpeditionPlanComponent(
            destination_id=str(d.id), route=(str(b.id), str(c.id), str(d.id)), pace=2
        ),
    )
    events = ExpeditionConsequence().process(actor.world, EPOCH + 1)
    # Pace 2 covers b and c this tick, d remains.
    assert container_of(traveller) == c.id
    assert isinstance(events[0], ExpeditionLegEvent)
    plan = traveller.get_component(ExpeditionPlanComponent)
    assert plan.route == (str(d.id),)


def test_expedition_consequence_aborts_when_a_charted_edge_vanishes():
    actor = WorldActor()
    a, b = _room(actor.world, title="A"), _room(actor.world, title="B")
    _exit(a, b, direction="east")
    traveller = _character(actor.world, a)
    _map_charting(actor.world, traveller, (a, b))
    _launch(actor, traveller.id, b.id)
    a.remove_relationship(ExitTo, b.id)  # the way is gone

    events = ExpeditionConsequence().process(actor.world, EPOCH + 1)
    assert events == []
    assert container_of(traveller) == a.id
    assert not traveller.has_component(ExpeditionPlanComponent)


def test_expedition_consequence_drops_a_plan_with_no_room():
    actor = WorldActor()
    b = _room(actor.world, title="B")
    traveller = _character(actor.world)  # no room
    replace_component(
        traveller, ExpeditionPlanComponent(destination_id=str(b.id), route=(str(b.id),), pace=1)
    )
    assert ExpeditionConsequence().process(actor.world, EPOCH + 1) == []
    assert not traveller.has_component(ExpeditionPlanComponent)


def test_expedition_consequence_drops_an_empty_route():
    actor = WorldActor()
    a = _room(actor.world, title="A")
    traveller = _character(actor.world, a)
    replace_component(
        traveller, ExpeditionPlanComponent(destination_id=str(a.id), route=(), pace=1)
    )
    assert ExpeditionConsequence().process(actor.world, EPOCH + 1) == []
    assert not traveller.has_component(ExpeditionPlanComponent)
