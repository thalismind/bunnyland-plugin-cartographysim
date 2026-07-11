"""Region surveys: summarise a charted neighbourhood and journal it to core memory.

A ``survey-region`` reads the caller's held field map, walks its *recorded* exit graph
breadth-first out to a radius from the current room (deterministic — the same charted graph
fast-travel routes over), and produces a :class:`RegionSurvey`: the rooms in reach, a biome
tally, and any landmark names. The summary is stamped onto the surveyor as a
:class:`LastSurveyComponent` (visible in prompts) and — via :class:`SurveyMemoryReactor` —
written to the **core memory store** so it is recall-able later, satisfying the map-persistence
core-reuse mandate without a bespoke store.

Verb validation order: invalid character -> no held map -> not in a room -> room not charted
-> bad radius -> apply.
"""

from __future__ import annotations

from collections import deque

from bunnyland.core.actions import ActionArgument, ActionDefinition
from bunnyland.core.commands import CommandCost, Lane, SubmittedCommand
from bunnyland.core.components import RegionComponent
from bunnyland.core.ecs import parse_entity_id, replace_component
from bunnyland.core.events import DomainEvent, EventVisibility
from bunnyland.core.handlers import HandlerContext, HandlerResult, ok, rejected, require_character
from bunnyland.prompts.context import ComponentPromptContext, PromptPerspective
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World

from .components import LandmarkComponent, MapComponent
from .holding import held_map_entity
from .regions import LocatedInRegion
from .spatial import room_of

#: Default and maximum survey radius (hops over the charted exit graph).
DEFAULT_RADIUS = 2
MAX_RADIUS = 8


@dataclass(frozen=True)
class RegionSurvey:
    """The immutable result of surveying a charted neighbourhood."""

    origin_room_id: str
    radius: int
    room_ids: tuple[str, ...] = ()
    biomes: tuple[tuple[str, int], ...] = ()
    landmarks: tuple[str, ...] = ()
    regions: tuple[str, ...] = ()


@dataclass(frozen=True)
class LastSurveyComponent(Component):
    """The caller's most recent region survey, surfaced in first-person prompts."""

    origin_room_id: str
    room_count: int
    summary: str

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        if not ctx.is_first_person:
            return ()
        return (self.summary,)


class RegionSurveyedEvent(DomainEvent):
    """A character completed a region survey from a charted room."""

    origin_room_id: str
    room_count: int
    radius: int
    summary: str


def survey_region(
    world: World, map_component: MapComponent, origin_id: str, radius: int
) -> RegionSurvey:
    """Breadth-first collect charted rooms within ``radius`` hops of ``origin_id``."""
    charted = {room.room_id: room for room in map_component.rooms}
    reached: set[str] = set()
    queue: deque[tuple[str, int]] = deque()
    if origin_id in charted:
        reached.add(origin_id)
        queue.append((origin_id, 0))
    while queue:
        current, depth = queue.popleft()
        if depth >= radius:
            continue
        room = charted[current]
        neighbors = sorted(
            {exit_.to_room_id for exit_ in room.exits if exit_.to_room_id in charted}
        )
        for neighbor in neighbors:
            if neighbor in reached:
                continue
            reached.add(neighbor)
            queue.append((neighbor, depth + 1))

    biome_counts: dict[str, int] = {}
    landmarks: list[str] = []
    regions: list[str] = []
    for room_id in reached:
        biome = charted[room_id].biome
        biome_counts[biome] = biome_counts.get(biome, 0) + 1
        parsed = parse_entity_id(room_id)
        if parsed is not None and world.has_entity(parsed):
            entity = world.get_entity(parsed)
            if entity.has_component(LandmarkComponent):
                landmarks.append(entity.get_component(LandmarkComponent).name)
            for _edge, region_id in entity.get_relationships(LocatedInRegion):
                if world.has_entity(region_id):
                    region = world.get_entity(region_id)
                    if region.has_component(RegionComponent):
                        regions.append(region.get_component(RegionComponent).name)
    biomes = tuple(sorted(biome_counts.items(), key=lambda item: (-item[1], item[0])))
    return RegionSurvey(
        origin_room_id=origin_id,
        radius=radius,
        room_ids=tuple(sorted(reached)),
        biomes=biomes,
        landmarks=tuple(sorted(dict.fromkeys(landmarks))),
        regions=tuple(sorted(dict.fromkeys(regions))),
    )


def survey_summary(survey: RegionSurvey) -> str:
    """A deterministic one-line description of ``survey``."""
    count = len(survey.room_ids)
    noun = "room" if count == 1 else "rooms"
    parts = [f"Region survey within {survey.radius} of a charted point: {count} {noun}"]
    if survey.biomes:
        biomes = ", ".join(f"{biome} x{tally}" for biome, tally in survey.biomes)
        parts.append(f"biomes: {biomes}")
    if survey.regions:
        parts.append("regions: " + ", ".join(survey.regions))
    if survey.landmarks:
        parts.append("landmarks: " + ", ".join(survey.landmarks))
    return "; ".join(parts) + "."


def _parse_radius(raw: object) -> int | None:
    if raw is None:
        return DEFAULT_RADIUS
    if isinstance(raw, bool) or not isinstance(raw, int):
        return None
    if raw < 1 or raw > MAX_RADIUS:
        return None
    return raw


class SurveyRegionHandler:
    """Survey the charted neighbourhood around the caller's current room."""

    command_type = "survey-region"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        map_entity = held_map_entity(ctx.world, character)
        if map_entity is None:
            return rejected("you need a field map to survey")
        room = room_of(ctx.world, character_id)
        if room is None:
            return rejected("you are not in a room")
        map_component = map_entity.get_component(MapComponent)
        if str(room.id) not in map_component.charted_ids():
            return rejected("you can only survey from a charted room")
        radius = _parse_radius(command.payload.get("radius"))
        if radius is None:
            return rejected("survey radius must be between 1 and 8")

        survey = survey_region(ctx.world, map_component, str(room.id), radius)
        summary = survey_summary(survey)
        replace_component(
            character,
            LastSurveyComponent(
                origin_room_id=str(room.id),
                room_count=len(survey.room_ids),
                summary=summary,
            ),
        )
        return ok(
            RegionSurveyedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.PRIVATE,
                    actor_id=str(character_id),
                    room_id=str(room.id),
                    origin_room_id=str(room.id),
                    room_count=len(survey.room_ids),
                    radius=radius,
                    summary=summary,
                )
            )
        )


def survey_fragments(world: World, character: Entity) -> list[str]:
    """Render the caller's most recent region survey, first-person only."""
    if character is None or not character.has_component(LastSurveyComponent):
        return []
    ctx = ComponentPromptContext.for_entity(
        world, character, perspective=PromptPerspective(viewer=character)
    )
    return list(character.get_component(LastSurveyComponent).prompt_fragments(ctx))


class SurveyMemoryReactor:
    """Journal every completed region survey into the core memory store, when present.

    ``store_provider`` is called lazily at event time so the reactor works regardless of the
    order in which the memory and cartography plugins are applied; if no store is installed
    the survey simply is not journalled.
    """

    COLLECTION = "cartography-surveys"

    def __init__(self, store_provider):
        self._store_provider = store_provider

    def subscribe(self, bus) -> None:
        bus.subscribe(RegionSurveyedEvent, self._on_survey)

    def _on_survey(self, event: RegionSurveyedEvent) -> None:
        store = self._store_provider()
        if store is None:
            return
        store.add(
            self.COLLECTION,
            text=event.summary,
            tags=("cartography", "survey"),
            created_at_epoch=event.world_epoch,
            source="survey",
        )


SURVEY_REGION_DEF = ActionDefinition(
    command_type="survey-region",
    title="Survey region",
    description="Summarise the charted rooms around you and record the survey to memory.",
    lane=Lane.WORLD,
    cost=CommandCost(action=1),
    arguments={
        "radius": ActionArgument(
            title="Radius",
            description="How many charted hops to survey outward (1-8, default 2).",
            kind="integer",
        ),
    },
)

SURVEY_ACTION_DEFINITIONS = (SURVEY_REGION_DEF,)
SURVEY_ACTION_HANDLERS = (SurveyRegionHandler,)


__all__ = [
    "DEFAULT_RADIUS",
    "MAX_RADIUS",
    "SURVEY_ACTION_DEFINITIONS",
    "SURVEY_ACTION_HANDLERS",
    "SURVEY_REGION_DEF",
    "LastSurveyComponent",
    "RegionSurvey",
    "RegionSurveyedEvent",
    "SurveyMemoryReactor",
    "SurveyRegionHandler",
    "survey_fragments",
    "survey_region",
    "survey_summary",
]
