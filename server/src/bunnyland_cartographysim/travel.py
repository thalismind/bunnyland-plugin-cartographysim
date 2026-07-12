"""Fast-travel mechanic: route to an already-charted room over known exits.

The ``travel-to`` verb plans a shortest path from the character's current room to any room
their field map has charted, using a deterministic breadth-first search over the map's
*recorded* exit graph (never live edges the holder has not walked). The path is stored as a
:class:`TravelPlanComponent` on the character, and :class:`TravelConsequence` walks it one
hop per tick — queued movement that removes the tedium of retracing known ground while still
rejecting unknown or unreachable destinations up front with exact reasons.

Verb validation order: invalid id -> missing entity -> no map -> not in a room -> already
there -> uncharted destination -> unreachable destination -> apply.
"""

from __future__ import annotations

from collections import deque

from bunnyland.core.actions import ActionArgument, ActionDefinition, ActionEffort, effort_cost
from bunnyland.core.commands import Lane, SubmittedCommand
from bunnyland.core.ecs import contents, parse_entity_id, replace_component
from bunnyland.core.edges import ContainmentMode, Contains, ExitTo
from bunnyland.core.events import DomainEvent, EventVisibility, event_base
from bunnyland.core.handlers import HandlerContext, HandlerResult, ok, rejected, require_character
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World

from .components import MapComponent
from .events import TravelArrivedEvent, TravelStartedEvent, TravelStepEvent
from .spatial import room_of


@dataclass(frozen=True)
class TravelPlanComponent(Component):
    """A queued fast-travel route: the remaining room ids to enter, in order."""

    destination_id: str
    route: tuple[str, ...] = ()


def plan_route(map_component: MapComponent, start_id: str, destination_id: str) -> list[str] | None:
    """Deterministic BFS over charted exits; the room-id hops from ``start`` to ``dest``.

    Returns the list of room ids to enter (excluding ``start``, ending at ``destination_id``),
    or ``None`` when no route exists over the map's recorded exits.
    """
    if start_id == destination_id:
        return []
    charted = {room.room_id: room for room in map_component.rooms}
    if start_id not in charted or destination_id not in charted:
        return None
    previous: dict[str, str] = {}
    visited = {start_id}
    queue: deque[str] = deque([start_id])
    while queue:
        current = queue.popleft()
        room = charted.get(current)
        if room is None:
            continue
        neighbors = sorted(
            {exit_.to_room_id for exit_ in room.exits if exit_.to_room_id in charted}
        )
        for neighbor in neighbors:
            if neighbor in visited:
                continue
            visited.add(neighbor)
            previous[neighbor] = current
            if neighbor == destination_id:
                return _unwind(previous, start_id, destination_id)
            queue.append(neighbor)
    return None


def _unwind(previous: dict[str, str], start_id: str, destination_id: str) -> list[str]:
    hops: list[str] = []
    node = destination_id
    while node != start_id:
        hops.append(node)
        node = previous[node]
    hops.reverse()
    return hops


class TravelToHandler:
    """Plan a fast-travel route to a charted destination room."""

    command_type = "travel-to"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        map_component = _held_map(ctx.world, character)
        if map_component is None:
            return rejected("you need a field map to fast-travel")
        room = room_of(ctx.world, character_id)
        if room is None:
            return rejected("you are not in a room")

        destination_id, _destination, rejection = require_destination(ctx, command)
        if rejection is not None:
            return rejection
        if destination_id == str(room.id):
            return rejected("you are already there")
        if destination_id not in map_component.charted_ids():
            return rejected("you have not charted that destination")
        route = plan_route(map_component, str(room.id), destination_id)
        if not route:
            return rejected("no known route to that destination")

        replace_component(
            character, TravelPlanComponent(destination_id=destination_id, route=tuple(route))
        )
        return ok(
            TravelStartedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.PRIVATE,
                    actor_id=str(character_id),
                    room_id=str(room.id),
                    destination_id=destination_id,
                    hops=len(route),
                )
            )
        )


def require_destination(ctx: HandlerContext, command: SubmittedCommand):
    """Resolve the destination room id from the payload with cartography-specific reasons."""
    raw = command.payload.get("destination_id")
    parsed = parse_entity_id(raw)
    if parsed is None:
        return None, None, rejected("invalid destination id")
    if not ctx.world.has_entity(parsed):
        return None, None, rejected("destination does not exist")
    return str(parsed), ctx.entity(parsed), None


def _held_map(world: World, character: Entity) -> MapComponent | None:
    for item_id in contents(character):
        if not world.has_entity(item_id):
            continue
        item = world.get_entity(item_id)
        if item.has_component(MapComponent):
            return item.get_component(MapComponent)
    return None


class TravelConsequence:
    """Advance every fast-travelling character one hop along its planned route each tick."""

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        travellers = sorted(
            world.query().with_all([TravelPlanComponent]).execute_entities(),
            key=lambda entity: str(entity.id),
        )
        events: list[DomainEvent] = []
        for traveller in travellers:
            event = self._advance(world, epoch, traveller)
            if event is not None:
                events.append(event)
        return events

    def _advance(self, world: World, epoch: int, traveller: Entity) -> DomainEvent | None:
        plan = traveller.get_component(TravelPlanComponent)
        room = room_of(world, traveller.id)
        if room is None or not plan.route:
            traveller.remove_component(TravelPlanComponent)
            return None
        next_id, *rest = plan.route
        direction, moved = _step(world, room, traveller, next_id)
        if not moved:
            # The charted edge is gone (world changed); abandon the plan rather than teleport.
            traveller.remove_component(TravelPlanComponent)
            return None
        if rest:
            replace_component(traveller, TravelPlanComponent(plan.destination_id, tuple(rest)))
            return TravelStepEvent(
                **event_base(
                    epoch,
                    default_visibility=EventVisibility.ROOM,
                    actor_id=str(traveller.id),
                    room_id=next_id,
                    from_room_id=str(room.id),
                    to_room_id=next_id,
                    direction=direction,
                )
            )
        traveller.remove_component(TravelPlanComponent)
        return TravelArrivedEvent(
            **event_base(
                epoch,
                default_visibility=EventVisibility.PRIVATE,
                actor_id=str(traveller.id),
                room_id=next_id,
                destination_id=plan.destination_id,
            )
        )


def _step(world: World, room: Entity, traveller: Entity, next_id: str) -> tuple[str, bool]:
    """Move ``traveller`` from ``room`` to ``next_id`` along a live exit; report direction."""
    for edge, target in room.get_relationships(ExitTo):
        if str(target) == next_id and world.has_entity(target):
            room.remove_relationship(Contains, traveller.id)
            world.get_entity(target).add_relationship(
                Contains(mode=ContainmentMode.ROOM_CONTENT), traveller.id
            )
            return edge.direction, True
    return "", False


TRAVEL_TO_DEF = ActionDefinition(
    command_type="travel-to",
    title="Travel to",
    description="Fast-travel to a room you have already charted, along known exits.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.ROUTINE),
    arguments={
        "destination_id": ActionArgument(
            title="Destination",
            description="A room you have charted on your field map.",
            kind="entity",
            required=True,
        ),
    },
)

TRAVEL_ACTION_DEFINITIONS = (TRAVEL_TO_DEF,)
TRAVEL_ACTION_HANDLERS = (TravelToHandler,)


__all__ = [
    "TRAVEL_ACTION_DEFINITIONS",
    "TRAVEL_ACTION_HANDLERS",
    "TRAVEL_TO_DEF",
    "TravelConsequence",
    "TravelPlanComponent",
    "TravelToHandler",
    "plan_route",
    "require_destination",
]
