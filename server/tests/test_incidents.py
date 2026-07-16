from __future__ import annotations

from bunnyland.core import (
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    container_of,
    spawn_entity,
)
from bunnyland.core.ecs import replace_component
from bunnyland.foundation.storyteller.mechanics import IncidentComponent, IncidentStartedEvent

from bunnyland_cartographysim import (
    INCIDENT_KIND,
    ChartedExit,
    ChartedRoom,
    MapComponent,
    UnchartedRegionIncidentConsequence,
    spawn_field_map,
    stage_uncharted_region_incident,
    uncharted_frontier_rooms,
)

EPOCH = 100


def _room(world, *, title="Room"):
    return spawn_entity(world, [RoomComponent(title=title)])


def _map_with(world, records, *, room=None):
    field_map = spawn_field_map(world, room_id=room.id if room is not None else None)
    replace_component(field_map, MapComponent(rooms=tuple(records)))
    return field_map


def test_frontier_room_is_detected():
    actor = WorldActor()
    here = _room(actor.world, title="Hall")
    beyond = _room(actor.world, title="Unknown")
    _map_with(
        actor.world,
        (
            ChartedRoom(
                room_id=str(here.id),
                title="Hall",
                exits=(ChartedExit(direction="north", to_room_id=str(beyond.id)),),
            ),
        ),
    )
    frontier = uncharted_frontier_rooms(actor.world)
    assert [r.id for r in frontier] == [beyond.id]


def test_frontier_skips_charted_missing_and_non_room_targets():
    actor = WorldActor()
    here = _room(actor.world, title="Hall")
    charted_neighbour = _room(actor.world, title="Known")
    item = spawn_entity(actor.world, [IdentityComponent(name="thing", kind="item")])
    _map_with(
        actor.world,
        (
            ChartedRoom(
                room_id=str(here.id),
                title="Hall",
                exits=(
                    ChartedExit(direction="north", to_room_id=str(charted_neighbour.id)),
                    ChartedExit(direction="south", to_room_id="entity_9999"),  # missing
                    ChartedExit(direction="east", to_room_id=str(item.id)),  # not a room
                ),
            ),
            ChartedRoom(room_id=str(charted_neighbour.id), title="Known"),  # charted
        ),
    )
    assert uncharted_frontier_rooms(actor.world) == []


def test_stage_incident_spawns_a_core_incident_in_the_room():
    actor = WorldActor()
    room = _room(actor.world, title="Unknown")
    incident, event = stage_uncharted_region_incident(actor.world, EPOCH, room)
    comp = incident.get_component(IncidentComponent)
    assert comp.kind == INCIDENT_KIND
    assert container_of(incident) == room.id
    assert isinstance(event, IncidentStartedEvent)
    assert event.kind == INCIDENT_KIND
    assert event.room_id_started == str(room.id)
    # The incident entity is placed in the frontier room.
    contained = {t for _e, t in room.get_relationships(Contains)}
    assert incident.id in contained


def test_consequence_stages_one_frontier_room():
    actor = WorldActor()
    here = _room(actor.world, title="Hall")
    beyond = _room(actor.world, title="Unknown")
    _map_with(
        actor.world,
        (
            ChartedRoom(
                room_id=str(here.id),
                title="Hall",
                exits=(ChartedExit(direction="north", to_room_id=str(beyond.id)),),
            ),
        ),
    )
    consequence = UnchartedRegionIncidentConsequence()
    events = consequence.process(actor.world, EPOCH)
    assert len(events) == 1
    assert isinstance(events[0], IncidentStartedEvent)

    # A second pass does not re-stage the same frontier room (an incident now guards it).
    assert consequence.process(actor.world, EPOCH + 1) == []


def test_consequence_noop_without_a_frontier():
    actor = WorldActor()
    room = _room(actor.world, title="Hall")
    _map_with(actor.world, (ChartedRoom(room_id=str(room.id), title="Hall"),), room=room)
    assert UnchartedRegionIncidentConsequence().process(actor.world, EPOCH) == []
