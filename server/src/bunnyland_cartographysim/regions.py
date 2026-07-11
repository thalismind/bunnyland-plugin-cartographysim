"""Named region entities and room-to-region relationships."""

from __future__ import annotations

from bunnyland.core import IdentityComponent, RegionComponent
from bunnyland.core.generation import (
    GenerationChild,
    GenerationDelta,
    GenerationRequest,
)
from pydantic.dataclasses import dataclass
from relics import Edge

from .spatial import room_of

REGION_NAMES: dict[str, str] = {
    "forest": "the Whispering Wilds",
    "desert": "the Sunscoured Waste",
    "mountain": "the Cloudpiercer Range",
    "swamp": "the Sunken Mire",
    "tundra": "the Frostbound Reach",
    "coast": "the Salt-Worn Shore",
    "cave": "the Underdark Hollows",
    "plains": "the Open Steppe",
}


@dataclass(frozen=True)
class LocatedInRegion(Edge):
    """A room belongs to a generated region entity."""


def region_name_for(biome: str) -> str:
    """Return the deterministic region name for ``biome``."""
    known = REGION_NAMES.get(biome.casefold())
    if known is not None:
        return known
    label = biome.strip() or "unknown"
    return f"the {label.title()} Reaches"


class RegionGenerationEnricher:
    """Create one shared region entity for generated rooms of each biome."""

    capabilities: tuple[str, ...] = ()

    def applies(self, request: GenerationRequest) -> bool:
        return request.entity_kind == "room"

    def enrich(self, request: GenerationRequest) -> GenerationDelta:
        room = next(
            (
                component
                for component in request.context.get("base_components", ())
                if component.__class__.__name__ == "RoomComponent"
            ),
            None,
        )
        biome = str(getattr(room, "biome", "unknown")) or "unknown"
        name = region_name_for(biome)
        return GenerationDelta(
            children=(
                GenerationChild(
                    request=GenerationRequest(
                        entity_kind="region",
                        description=name,
                        source_seed=request.source_seed,
                        source_key=f"region:{biome.casefold()}",
                    ),
                    parent_edge=LocatedInRegion(),
                    components=(
                        IdentityComponent(name=name, kind="region"),
                        RegionComponent(name=name, climate=biome),
                    ),
                    singleton_key=f"cartography.region:{biome.casefold()}",
                ),
            )
        )


def _region_entity(world, room):
    relationships = room.get_relationships(LocatedInRegion)
    if not relationships:
        return None
    region_id = relationships[0][1]
    if not world.has_entity(region_id):
        return None
    region = world.get_entity(region_id)
    if not region.has_component(RegionComponent):
        return None
    return region


def region_fragments(world, character) -> list[str]:
    """Render the current room's region name for anyone standing in it."""
    if character is None:
        return []
    room = room_of(world, character.id)
    if room is None:
        return []
    region = _region_entity(world, room)
    if region is None:
        return []
    component = region.get_component(RegionComponent)
    return [f"This lies within {component.name}."]


__all__ = [
    "LocatedInRegion",
    "REGION_NAMES",
    "RegionGenerationEnricher",
    "region_fragments",
    "region_name_for",
]
