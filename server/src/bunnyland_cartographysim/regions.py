"""Named regions: v2 worldgen enrichment that groups generated rooms into regions.

Where v1's worldgen hook pins single-room *landmarks*, this v2 hook paints every generated
room with the broader **region** it belongs to, derived deterministically from the room's
biome. Regions give surveys something to name ("the Whispering Wilds") and give a shared map a
sense of place. The core generator stays ignorant of this plugin — the hook only reacts to
``RoomGeneratedEvent`` on the bus, and rooms that already carry a region are left untouched.
"""

from __future__ import annotations

from bunnyland.core import RoomComponent
from bunnyland.core.ecs import parse_entity_id, replace_component
from bunnyland.core.events import RoomGeneratedEvent
from bunnyland.core.world_actor import WorldActor
from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component

from .spatial import room_of

#: Deterministic ``biome -> region name`` map; unlisted biomes fall back to a titled name.
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
class RegionComponent(Component):
    """The named region a room belongs to."""

    name: str
    biome: str = "unknown"

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        return (f"This lies within {self.name}.",)


def region_name_for(biome: str) -> str:
    """The deterministic region name for ``biome``."""
    known = REGION_NAMES.get(biome.casefold())
    if known is not None:
        return known
    label = biome.strip() or "unknown"
    return f"the {label.title()} Reaches"


class RegionWorldgenHook:
    """Paint each generated room with the region its biome implies."""

    def subscribe(self, actor: WorldActor) -> None:
        self._actor = actor
        actor.bus.subscribe(RoomGeneratedEvent, self._on_room)

    def _on_room(self, event: RoomGeneratedEvent) -> None:
        parsed = parse_entity_id(event.entity_id)
        if parsed is None or not self._actor.world.has_entity(parsed):
            return
        room = self._actor.world.get_entity(parsed)
        if not room.has_component(RoomComponent) or room.has_component(RegionComponent):
            return
        replace_component(
            room, RegionComponent(name=region_name_for(event.biome), biome=event.biome)
        )


def region_fragments(world, character) -> list[str]:
    """Render the current room's region name for anyone standing in it."""
    if character is None:
        return []
    room = room_of(world, character.id)
    if room is None or not room.has_component(RegionComponent):
        return []
    ctx = ComponentPromptContext.for_entity(world, character, room=room)
    return list(room.get_component(RegionComponent).prompt_fragments(ctx))


__all__ = [
    "REGION_NAMES",
    "RegionComponent",
    "RegionWorldgenHook",
    "region_fragments",
    "region_name_for",
]
