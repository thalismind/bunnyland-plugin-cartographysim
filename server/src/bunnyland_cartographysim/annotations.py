"""Rich map annotations: pin notes to charted rooms on a field map.

A cartographer can scribble a categorised note ("danger", "cache", "note", ...) onto the
room they stand in, provided that room is already charted on their held map. Notes live in a
:class:`MapAnnotationsComponent` on the *map item* (one component per map, a sorted tuple of
:class:`MapNote` records) so they travel and persist with the map — and, because sharing
shares the map entity, a shared map carries its annotations too.

Verb validation order: invalid character -> no held map -> not in a room -> room not charted
-> empty note text -> apply.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core.actions import ActionArgument, ActionDefinition, ActionEffort, effort_cost
from bunnyland.core.commands import Lane, SubmittedCommand
from bunnyland.core.ecs import replace_component
from bunnyland.core.events import DomainEvent, EventVisibility
from bunnyland.core.handlers import HandlerContext, HandlerResult, ok, rejected, require_character
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World

from .components import MapComponent
from .holding import held_map_entity
from .spatial import room_of


@dataclass(frozen=True)
class MapNote:
    """A single categorised annotation pinned to a charted room."""

    room_id: str
    text: str
    category: str = "note"


def _sorted_notes(notes: tuple[MapNote, ...]) -> tuple[MapNote, ...]:
    return tuple(sorted(notes, key=lambda note: (note.room_id, note.category, note.text)))


@dataclass(frozen=True)
class MapAnnotationsComponent(Component):
    """Notes drawn onto a field map, kept sorted for deterministic iteration."""

    notes: tuple[MapNote, ...] = ()

    def notes_for(self, room_id: str) -> tuple[MapNote, ...]:
        """Every note pinned to ``room_id`` on this map."""
        return tuple(note for note in self.notes if note.room_id == room_id)

    def with_note(self, note: MapNote) -> MapAnnotationsComponent:
        """Return a new component with ``note`` added (identical notes are not duplicated)."""
        if note in self.notes:
            return self
        return MapAnnotationsComponent(notes=_sorted_notes((*self.notes, note)))


class MapAnnotatedEvent(DomainEvent):
    """A character annotated a charted room on their field map."""

    room_id_annotated: str
    text: str
    category: str


class AnnotateMapHandler:
    """Pin a note onto the charted room the caller is standing in."""

    command_type = "annotate-map"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        map_entity = held_map_entity(ctx.world, character)
        if map_entity is None:
            return rejected("you need a field map to annotate")
        room = room_of(ctx.world, character_id)
        if room is None:
            return rejected("you are not in a room")
        if str(room.id) not in map_entity.get_component(MapComponent).charted_ids():
            return rejected("you can only annotate a room you have charted")
        raw_text = command.payload.get("note")
        text = raw_text.strip() if isinstance(raw_text, str) else ""
        if not text:
            return rejected("annotation text is required")
        raw_category = command.payload.get("category")
        category = (
            raw_category.strip()
            if isinstance(raw_category, str) and raw_category.strip()
            else "note"
        )

        note = MapNote(room_id=str(room.id), text=text, category=category)
        existing = (
            map_entity.get_component(MapAnnotationsComponent)
            if map_entity.has_component(MapAnnotationsComponent)
            else MapAnnotationsComponent()
        )
        replace_component(map_entity, replace(existing, notes=existing.with_note(note).notes))
        return ok(
            MapAnnotatedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.PRIVATE,
                    actor_id=str(character_id),
                    room_id=str(room.id),
                    target_ids=(str(room.id),),
                    room_id_annotated=str(room.id),
                    text=text,
                    category=category,
                )
            )
        )


def annotation_fragments(world: World, character: Entity) -> list[str]:
    """Render the caller's own map notes for the room they are standing in."""
    if character is None:
        return []
    map_entity = held_map_entity(world, character)
    if map_entity is None or not map_entity.has_component(MapAnnotationsComponent):
        return []
    room = room_of(world, character.id)
    if room is None:
        return []
    notes = map_entity.get_component(MapAnnotationsComponent).notes_for(str(room.id))
    return [f"Your map note here ({note.category}): {note.text}" for note in notes]


ANNOTATE_MAP_DEF = ActionDefinition(
    command_type="annotate-map",
    title="Annotate map",
    description="Pin a categorised note to a charted room on your field map.",
    lane=Lane.FOCUS,
    cost=effort_cost(focus=ActionEffort.ROUTINE),
    arguments={
        "note": ActionArgument(
            title="Note",
            description="The annotation text to pin here.",
            kind="string",
            required=True,
        ),
        "category": ActionArgument(
            title="Category",
            description="An optional label such as 'danger' or 'cache' (default 'note').",
            kind="string",
        ),
    },
)

ANNOTATION_ACTION_DEFINITIONS = (ANNOTATE_MAP_DEF,)
ANNOTATION_ACTION_HANDLERS = (AnnotateMapHandler,)


__all__ = [
    "ANNOTATE_MAP_DEF",
    "ANNOTATION_ACTION_DEFINITIONS",
    "ANNOTATION_ACTION_HANDLERS",
    "AnnotateMapHandler",
    "MapAnnotatedEvent",
    "MapAnnotationsComponent",
    "MapNote",
    "annotation_fragments",
]
