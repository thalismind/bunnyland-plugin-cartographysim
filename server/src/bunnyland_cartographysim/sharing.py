"""Shareable maps — the v2 headline mechanic.

A cartographer can **share** a field map with another character standing with them. Sharing
is modelled as a :class:`SharedWith` **typed edge** from the map item to the recipient (one
index per edge type, never a component list), carrying who shared it and when. The recipient
then reads the map's charted-room tally through :func:`share_fragments`, so a party can pool
one explorer's survey work without copying components around.

This is the pack's published connector surface: any other pack can read ``SharedWith`` edges
to discover which characters have access to which maps, and cartography publishes a
:class:`MapSharedEvent` when a share happens.

Verb validation order: invalid character -> no held map -> invalid recipient id -> recipient
missing -> recipient unreachable -> recipient is self -> recipient is not a character ->
already shared -> apply.
"""

from __future__ import annotations

from bunnyland.core import CharacterComponent
from bunnyland.core.actions import ActionArgument, ActionDefinition, ActionEffort, effort_cost
from bunnyland.core.commands import Lane, SubmittedCommand
from bunnyland.core.events import DomainEvent, EventVisibility
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    ok,
    rejected,
    require_character,
    require_reachable_entity,
)
from pydantic.dataclasses import dataclass
from relics import Edge, Entity, World

from .components import MapComponent
from .holding import held_map_entity
from .spatial import room_of


@dataclass(frozen=True)
class SharedWith(Edge):
    """A field map -> character it has been shared with (directed, one index per type)."""

    shared_by: str = ""
    since_epoch: int = 0
    can_edit: bool = False


class MapSharedEvent(DomainEvent):
    """A character shared their field map with another character."""

    map_id: str
    recipient_id: str
    sharer_id: str


def is_shared_with(map_entity: Entity, recipient_id: str) -> bool:
    """Whether ``map_entity`` already carries a :class:`SharedWith` edge to ``recipient_id``."""
    return any(
        str(target) == recipient_id for _edge, target in map_entity.get_relationships(SharedWith)
    )


def maps_shared_with(world: World, character: Entity) -> list[Entity]:
    """Every field-map entity shared with ``character``, sorted by id (deterministic)."""
    character_id = str(character.id)
    shared = [
        map_entity
        for map_entity in world.query().with_all([MapComponent]).execute_entities()
        if is_shared_with(map_entity, character_id)
    ]
    shared.sort(key=lambda entity: str(entity.id))
    return shared


class ShareMapHandler:
    """Share the caller's held field map with a reachable character."""

    command_type = "share-map"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        sharer_id, sharer, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        map_entity = held_map_entity(ctx.world, sharer)
        if map_entity is None:
            return rejected("you need a field map to share")
        recipient_id, recipient, rejection = require_reachable_entity(
            ctx,
            sharer,
            command.payload.get("recipient_id"),
            invalid_reason="invalid recipient id",
            missing_reason="that character is not here",
            unreachable_reason="that character is not here",
        )
        if rejection is not None:
            return rejection
        if recipient_id == sharer_id:
            return rejected("you cannot share a map with yourself")
        if not recipient.has_component(CharacterComponent):
            return rejected("you can only share a map with a character")
        if is_shared_with(map_entity, str(recipient_id)):
            return rejected("that map is already shared with them")

        map_entity.add_relationship(
            SharedWith(shared_by=str(sharer_id), since_epoch=ctx.epoch), recipient.id
        )
        room = room_of(ctx.world, sharer_id)
        return ok(
            MapSharedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(sharer_id),
                    room_id=str(room.id) if room is not None else None,
                    target_ids=(str(recipient_id),),
                    map_id=str(map_entity.id),
                    recipient_id=str(recipient_id),
                    sharer_id=str(sharer_id),
                )
            )
        )


def share_fragments(world: World, character: Entity) -> list[str]:
    """Tell a character which maps are shared with them, and how widely they've shared."""
    if character is None:
        return []
    lines: list[str] = []
    for map_entity in maps_shared_with(world, character):
        count = len(map_entity.get_component(MapComponent).rooms)
        noun = "room" if count == 1 else "rooms"
        lines.append(f"A shared field map grants you {count} charted {noun}.")
    held = held_map_entity(world, character)
    if held is not None:
        recipients = sum(1 for _edge, _target in held.get_relationships(SharedWith))
        if recipients:
            noun = "explorer" if recipients == 1 else "explorers"
            lines.append(f"You have shared your field map with {recipients} {noun}.")
    return sorted(dict.fromkeys(lines))


SHARE_MAP_DEF = ActionDefinition(
    command_type="share-map",
    title="Share map",
    description="Share your field map with another character here, granting them your charts.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.ROUTINE),
    arguments={
        "recipient_id": ActionArgument(
            title="Recipient",
            description="A character standing with you to share the map with.",
            kind="entity",
            required=True,
        ),
    },
)

SHARE_ACTION_DEFINITIONS = (SHARE_MAP_DEF,)
SHARE_ACTION_HANDLERS = (ShareMapHandler,)


__all__ = [
    "SHARE_ACTION_DEFINITIONS",
    "SHARE_ACTION_HANDLERS",
    "SHARE_MAP_DEF",
    "MapSharedEvent",
    "ShareMapHandler",
    "SharedWith",
    "is_shared_with",
    "maps_shared_with",
    "share_fragments",
]
