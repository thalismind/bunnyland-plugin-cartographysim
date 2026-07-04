"""Field map mechanic: stamp the holder's current room into their map each tick.

:class:`MappingConsequence` is the per-tick heart of the pack. For every entity carrying a
:class:`~bunnyland_cartographysim.components.MapComponent` it resolves the room the map is
ultimately in (held by a walking character *or* resting on the floor), then records that
room's title, biome, and live ``ExitTo`` edges as a
:class:`~bunnyland_cartographysim.components.ChartedRoom`. Recording is idempotent: an
unchanged room is not re-stamped, so a stationary map produces no churn.

The recorded exit graph is deliberately the *only* thing fast-travel routes over, so the map
can never plot a course through an exit its holder has not personally charted.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import RoomComponent
from bunnyland.core.ecs import contents, replace_component
from bunnyland.core.edges import ExitTo
from bunnyland.core.events import DomainEvent
from bunnyland.prompts.context import ComponentPromptContext, PromptPerspective
from relics import Entity, World

from .components import ChartedExit, ChartedRoom, MapComponent
from .spatial import room_of


def charted_exits(room: Entity) -> tuple[ChartedExit, ...]:
    """Return ``room``'s ``ExitTo`` edges as sorted, immutable charted-exit records."""
    exits = [
        ChartedExit(direction=edge.direction, to_room_id=str(target), label=edge.label)
        for edge, target in room.get_relationships(ExitTo)
    ]
    exits.sort(key=lambda exit_: (exit_.direction, exit_.to_room_id))
    return tuple(exits)


def record_for_room(room: Entity) -> ChartedRoom:
    """Build the charted record for ``room`` from its live components and exits."""
    info = room.get_component(RoomComponent)
    return ChartedRoom(
        room_id=str(room.id),
        title=info.title,
        biome=info.biome,
        exits=charted_exits(room),
    )


class MappingConsequence:
    """Stamp each field map's current room into the map every tick."""

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        maps = sorted(
            world.query().with_all([MapComponent]).execute_entities(),
            key=lambda entity: str(entity.id),
        )
        for map_entity in maps:
            self._chart(world, map_entity)
        return []

    def _chart(self, world: World, map_entity: Entity) -> None:
        room = room_of(world, map_entity.id)
        if room is None or not room.has_component(RoomComponent):
            return
        component = map_entity.get_component(MapComponent)
        record = record_for_room(room)
        if component.get(record.room_id) == record:
            return
        replace_component(map_entity, replace(component, rooms=component.with_room(record).rooms))


def map_fragments(world: World, character: Entity) -> list[str]:
    """Render the charted-room tally for each field map the character is holding."""
    if character is None:
        return []
    lines: list[str] = []
    for item_id in contents(character):
        if not world.has_entity(item_id):
            continue
        item = world.get_entity(item_id)
        if not item.has_component(MapComponent):
            continue
        ctx = ComponentPromptContext.for_entity(
            world, item, perspective=PromptPerspective(viewer=item)
        )
        lines.extend(item.get_component(MapComponent).prompt_fragments(ctx))
    return sorted(dict.fromkeys(lines))


__all__ = ["MappingConsequence", "charted_exits", "map_fragments", "record_for_room"]
