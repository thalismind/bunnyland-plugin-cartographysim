"""Expeditions: mount-boosted travel legs over the charted exit graph.

An expedition is fast-travel's longer-range cousin. ``launch-expedition`` plans a
deterministic BFS route to a charted destination (reusing :func:`~.travel.plan_route`), and
:class:`ExpeditionConsequence` walks it by moving the traveller's ``Contains`` edge — reusing
core movement rather than teleporting. The one difference from v1 fast-travel is **pace**: a
character leading a petsim mount covers two charted hops per tick instead of one (the optional
mount connector), so a mounted expedition arrives in half the ticks.

Verb validation order: invalid character -> no held map -> not in a room -> invalid
destination -> already there -> uncharted destination -> unreachable destination -> apply.
"""

from __future__ import annotations

from bunnyland.core.actions import ActionArgument, ActionDefinition, ActionEffort, effort_cost
from bunnyland.core.commands import Lane, SubmittedCommand
from bunnyland.core.ecs import replace_component
from bunnyland.core.edges import ContainmentMode, Contains, ExitTo
from bunnyland.core.events import DomainEvent, EventVisibility, event_base
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    planned,
    rejected,
    require_character,
)
from bunnyland.core.mutations import MutationPlan, SetComponent
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World

from .components import MapComponent
from .connectors import expedition_pace, is_mounted
from .holding import held_map_entity
from .spatial import room_of
from .travel import plan_route, require_destination


@dataclass(frozen=True)
class ExpeditionPlanComponent(Component):
    """A queued expedition: remaining room ids to enter, and hops covered per tick."""

    destination_id: str
    route: tuple[str, ...] = ()
    pace: int = 1


class ExpeditionStartedEvent(DomainEvent):
    """A character set out on an expedition toward a charted destination."""

    destination_id: str
    hops: int
    pace: int


class ExpeditionLegEvent(DomainEvent):
    """An expedition advanced one hop of its route this tick."""

    from_room_id: str
    to_room_id: str
    direction: str = ""


class ExpeditionArrivedEvent(DomainEvent):
    """An expedition reached its destination."""

    destination_id: str


class LaunchExpeditionHandler:
    """Plan a mount-aware expedition to a charted destination room."""

    command_type = "launch-expedition"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        map_entity = held_map_entity(ctx.world, character)
        if map_entity is None:
            return rejected("you need a field map to launch an expedition")
        room = room_of(ctx.world, character_id)
        if room is None:
            return rejected("you are not in a room")

        destination_id, _destination, rejection = require_destination(ctx, command)
        if rejection is not None:
            return rejection
        map_component = map_entity.get_component(MapComponent)
        if destination_id == str(room.id):
            return rejected("you are already there")
        if destination_id not in map_component.charted_ids():
            return rejected("you have not charted that destination")
        route = plan_route(map_component, str(room.id), destination_id)
        if not route:
            return rejected("no known route to that destination")

        pace = expedition_pace(is_mounted(ctx.world, character))
        return planned(
            MutationPlan(
                (
                    SetComponent(
                        character.id,
                        ExpeditionPlanComponent(
                            destination_id=destination_id,
                            route=tuple(route),
                            pace=pace,
                        ),
                    ),
                )
            ),
            ExpeditionStartedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.PRIVATE,
                    actor_id=str(character_id),
                    room_id=str(room.id),
                    destination_id=destination_id,
                    hops=len(route),
                    pace=pace,
                )
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


class ExpeditionConsequence:
    """Advance every expedition up to its pace in charted hops each tick."""

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        travellers = sorted(
            world.query().with_all([ExpeditionPlanComponent]).execute_entities(),
            key=lambda entity: str(entity.id),
        )
        events: list[DomainEvent] = []
        for traveller in travellers:
            events.extend(self._advance(world, epoch, traveller))
        return events

    def _advance(self, world: World, epoch: int, traveller: Entity) -> list[DomainEvent]:
        plan = traveller.get_component(ExpeditionPlanComponent)
        route = list(plan.route)
        events: list[DomainEvent] = []
        for _ in range(max(1, plan.pace)):
            room = room_of(world, traveller.id)
            if room is None or not route:
                traveller.remove_component(ExpeditionPlanComponent)
                return events
            next_id = route[0]
            direction, moved = _step(world, room, traveller, next_id)
            if not moved:
                # The charted edge is gone (the world changed); abandon rather than teleport.
                traveller.remove_component(ExpeditionPlanComponent)
                return events
            route.pop(0)
            if route:
                events.append(
                    ExpeditionLegEvent(
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
                )
            else:
                traveller.remove_component(ExpeditionPlanComponent)
                events.append(
                    ExpeditionArrivedEvent(
                        **event_base(
                            epoch,
                            default_visibility=EventVisibility.PRIVATE,
                            actor_id=str(traveller.id),
                            room_id=next_id,
                            destination_id=plan.destination_id,
                        )
                    )
                )
                return events
        # Pace exhausted mid-route: persist remaining hops for the next tick.
        replace_component(
            traveller,
            ExpeditionPlanComponent(plan.destination_id, tuple(route), plan.pace),
        )
        return events


LAUNCH_EXPEDITION_DEF = ActionDefinition(
    command_type="launch-expedition",
    title="Launch expedition",
    description="Set out for a charted room, faster while leading a mount.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.MAJOR),
    arguments={
        "destination_id": ActionArgument(
            title="Destination",
            description="A room you have charted on your field map.",
            kind="entity",
            required=True,
        ),
    },
)

EXPEDITION_ACTION_DEFINITIONS = (LAUNCH_EXPEDITION_DEF,)
EXPEDITION_ACTION_HANDLERS = (LaunchExpeditionHandler,)


__all__ = [
    "EXPEDITION_ACTION_DEFINITIONS",
    "EXPEDITION_ACTION_HANDLERS",
    "LAUNCH_EXPEDITION_DEF",
    "ExpeditionArrivedEvent",
    "ExpeditionConsequence",
    "ExpeditionLegEvent",
    "ExpeditionPlanComponent",
    "ExpeditionStartedEvent",
    "LaunchExpeditionHandler",
]
