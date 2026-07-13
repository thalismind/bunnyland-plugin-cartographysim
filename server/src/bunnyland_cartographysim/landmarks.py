"""Landmark mechanic: pin a memorable name to the room you stand in.

The ``name-landmark`` verb draws a :class:`~bunnyland_cartographysim.components.LandmarkComponent`
straight onto the character's current room (renaming any existing landmark), and
:func:`landmark_fragments` renders that name for anyone standing there. Natural landmarks
seeded by the worldgen hook use the same component, so a player-named crossroads and a
generated ruin read identically.

Verb validation follows the project order: invalid id -> missing entity -> not in a room ->
invalid argument -> apply.
"""

from __future__ import annotations

from bunnyland.core.actions import ActionArgument, ActionDefinition, ActionEffort, effort_cost
from bunnyland.core.commands import Lane, SubmittedCommand
from bunnyland.core.events import EventVisibility
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    planned,
    rejected,
    require_character,
)
from bunnyland.core.mutations import MutationPlan, SetComponent
from bunnyland.prompts.context import ComponentPromptContext
from relics import Entity, World

from .components import LandmarkComponent
from .events import LandmarkNamedEvent
from .spatial import room_of


class NameLandmarkHandler:
    """Pin a landmark name onto the room the character is standing in."""

    command_type = "name-landmark"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, _character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        room = room_of(ctx.world, character_id)
        if room is None:
            return rejected("you are not in a room")
        raw_name = command.payload.get("name")
        name = raw_name.strip() if isinstance(raw_name, str) else ""
        if not name:
            return rejected("landmark name is required")
        shared = bool(command.payload.get("shared", True))
        return planned(
            MutationPlan(
                (SetComponent(room.id, LandmarkComponent(name=name, kind="marker", shared=shared)),)
            ),
            LandmarkNamedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character_id),
                    room_id=str(room.id),
                    target_ids=(str(room.id),),
                    room_id_named=str(room.id),
                    name=name,
                )
            )
        )


NAME_LANDMARK_DEF = ActionDefinition(
    command_type="name-landmark",
    title="Name landmark",
    description="Pin a memorable name to the room you are in.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.ROUTINE),
    arguments={
        "name": ActionArgument(
            title="Name",
            description="The name to pin to this place.",
            kind="string",
            required=True,
        ),
        "shared": ActionArgument(
            title="Shared",
            description="Whether the landmark is visible to others (default true).",
            kind="boolean",
        ),
    },
)

LANDMARK_ACTION_DEFINITIONS = (NAME_LANDMARK_DEF,)
LANDMARK_ACTION_HANDLERS = (NameLandmarkHandler,)


def landmark_fragments(world: World, character: Entity) -> list[str]:
    """Render the current room's landmark name for anyone standing in it."""
    if character is None:
        return []
    room = room_of(world, character.id)
    if room is None or not room.has_component(LandmarkComponent):
        return []
    ctx = ComponentPromptContext.for_entity(world, character, room=room)
    return list(room.get_component(LandmarkComponent).prompt_fragments(ctx))


__all__ = [
    "LANDMARK_ACTION_DEFINITIONS",
    "LANDMARK_ACTION_HANDLERS",
    "NAME_LANDMARK_DEF",
    "NameLandmarkHandler",
    "landmark_fragments",
]
