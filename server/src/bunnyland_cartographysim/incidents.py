"""Storyteller incident: the uncharted region at a map's frontier.

Cartography feeds world pressure back to the **core storyteller** rather than inventing its
own pacing. When any field map records an exit leading to a room no map has charted, that
room is a *frontier* into the unknown. :class:`UnchartedRegionIncidentConsequence` stages one
such room per tick as a core :class:`IncidentComponent` (kind ``uncharted_region``) so the
storyteller and prompt layer surface it like any other incident — a lure for explorers to go
map it. The incident entity is placed in the frontier room and reuses the core
:class:`IncidentStartedEvent`.
"""

from __future__ import annotations

from bunnyland.core import IdentityComponent, RoomComponent, container_of
from bunnyland.core.ecs import parse_entity_id, spawn_entity
from bunnyland.core.edges import ContainmentMode, Contains
from bunnyland.core.events import DomainEvent, EventVisibility, event_base
from bunnyland.foundation.storyteller.mechanics import IncidentComponent, IncidentStartedEvent
from relics import Entity, World

from .components import MapComponent

#: The incident kind cartography stages for an unexplored frontier room.
INCIDENT_KIND = "uncharted_region"


def _incident_room_ids(world: World) -> set[str]:
    """Room ids that already host an ``uncharted_region`` incident (resolved or not)."""
    ids: set[str] = set()
    for entity in world.query().with_all([IncidentComponent]).execute_entities():
        incident = entity.get_component(IncidentComponent)
        room_id = container_of(entity)
        if incident.kind == INCIDENT_KIND and room_id is not None:
            ids.add(str(room_id))
    return ids


def uncharted_frontier_rooms(world: World) -> list[Entity]:
    """Charted-map frontier rooms that no map has charted and host no incident yet."""
    maps = list(world.query().with_all([MapComponent]).execute_entities())
    charted_all: set[str] = set()
    for map_entity in maps:
        charted_all |= map_entity.get_component(MapComponent).charted_ids()
    staged = _incident_room_ids(world)

    frontier: dict[str, Entity] = {}
    for map_entity in maps:
        for room in map_entity.get_component(MapComponent).rooms:
            for exit_ in room.exits:
                target_id = exit_.to_room_id
                if target_id in charted_all or target_id in staged or target_id in frontier:
                    continue
                parsed = parse_entity_id(target_id)
                if parsed is None or not world.has_entity(parsed):
                    continue
                target = world.get_entity(parsed)
                if target.has_component(RoomComponent):
                    frontier[target_id] = target
    return [frontier[key] for key in sorted(frontier)]


def stage_uncharted_region_incident(
    world: World, epoch: int, room: Entity
) -> tuple[Entity, IncidentStartedEvent]:
    """Spawn an ``uncharted_region`` incident in ``room`` and return it with its start event."""
    incident = spawn_entity(
        world,
        [
            IdentityComponent(name="uncharted region", kind="incident"),
            IncidentComponent(
                kind=INCIDENT_KIND,
                budget_spent=0.0,
                started_at_epoch=epoch,
            ),
        ],
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), incident.id)
    event = IncidentStartedEvent(
        **event_base(
            epoch,
            default_visibility=EventVisibility.ROOM,
            actor_id=str(incident.id),
            room_id=str(room.id),
            target_ids=(str(incident.id),),
            incident_id=str(incident.id),
            kind=INCIDENT_KIND,
            room_id_started=str(room.id),
        )
    )
    return incident, event


class UnchartedRegionIncidentConsequence:
    """Stage one uncharted-frontier room per tick as a core storyteller incident."""

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        frontier = uncharted_frontier_rooms(world)
        if not frontier:
            return []
        _incident, event = stage_uncharted_region_incident(world, epoch, frontier[0])
        return [event]


__all__ = [
    "INCIDENT_KIND",
    "UnchartedRegionIncidentConsequence",
    "stage_uncharted_region_incident",
    "uncharted_frontier_rooms",
]
