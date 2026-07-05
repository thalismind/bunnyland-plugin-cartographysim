"""Optional synergy connectors — safe, dormant when partner packs are absent.

Cartography **consumes** two partner surfaces, both entirely optional (declared as plugin
``recommends``, never ``requires``): the pack runs standalone with these features simply
switched off.

- **Discovery** — expedition packs (aqua / lore / cryptid) publish an event announcing a
  found location. When such a pack is loaded, :class:`ExpeditionDiscoveryReactor` charts the
  discovered room onto the discoverer's held field map. The expected event shape exposes a
  ``location_id`` (the found room) and the standard ``actor_id`` (the discoverer).
- **Mounts** — petsim publishes a mount marker component; :func:`is_mounted` reports whether a
  character leads a mount so expeditions can travel at a faster pace.

Both partner surfaces are resolved by a safe conditional import: a missing partner is skipped
and the feature stays dormant. The resolvers accept an explicit ``sources`` list so the loaded
path is exercised deterministically in tests without installing a partner pack.
"""

from __future__ import annotations

import importlib
from dataclasses import replace

from bunnyland.core import RoomComponent
from bunnyland.core.ecs import contents, parse_entity_id, replace_component
from relics import Entity, World

from .components import MapComponent
from .holding import held_map_entity
from .mapping import record_for_room

#: Partner expedition packs that publish a location-discovery event ``(module, class)``.
DISCOVERY_EVENT_SOURCES: tuple[tuple[str, str], ...] = (
    ("bunnyland_aquasim", "DiveSiteDiscoveredEvent"),
    ("bunnyland_loresim", "LocationDiscoveredEvent"),
    ("bunnyland_cryptidsim", "LairDiscoveredEvent"),
)

#: Partner packs that publish a mount marker component ``(module, class)``.
MOUNT_COMPONENT_SOURCES: tuple[tuple[str, str], ...] = (
    ("bunnyland_petsim", "MountComponent"),
)


def _resolve_imports(sources: tuple[tuple[str, str], ...]) -> tuple[type, ...]:
    """Import each ``(module, class)`` that is available; skip any missing partner pack."""
    resolved: list[type] = []
    for module_name, class_name in sources:
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue
        symbol = getattr(module, class_name, None)
        if isinstance(symbol, type):
            resolved.append(symbol)
    return tuple(resolved)


def resolve_discovery_event_types(sources=DISCOVERY_EVENT_SOURCES) -> tuple[type, ...]:
    """Discovery event classes from whichever expedition partner packs are installed."""
    return _resolve_imports(sources)


def resolve_mount_component_types(sources=MOUNT_COMPONENT_SOURCES) -> tuple[type, ...]:
    """Mount marker component classes from the petsim partner pack, if installed."""
    return _resolve_imports(sources)


def is_mounted(
    world: World, character: Entity, mount_types: tuple[type, ...] | None = None
) -> bool:
    """Whether ``character`` leads a mount (a held entity carrying a mount marker component)."""
    types = resolve_mount_component_types() if mount_types is None else mount_types
    if not types:
        return False
    for item_id in contents(character):
        if not world.has_entity(item_id):
            continue
        item = world.get_entity(item_id)
        if any(item.has_component(mount_type) for mount_type in types):
            return True
    return False


def expedition_pace(mounted: bool) -> int:
    """Hops an expedition covers per tick: mounts double the pace."""
    return 2 if mounted else 1


def _discovery_location_id(event) -> str | None:
    return getattr(event, "location_id", None)


class ExpeditionDiscoveryReactor:
    """Chart a partner pack's discovered location onto the discoverer's held field map."""

    def __init__(self, world: World, event_types: tuple[type, ...] | None = None):
        self.world = world
        self.event_types = (
            resolve_discovery_event_types() if event_types is None else tuple(event_types)
        )

    @property
    def active(self) -> bool:
        """Whether any partner discovery surface was resolved (feature is live)."""
        return bool(self.event_types)

    def subscribe(self, bus) -> None:
        for event_type in self.event_types:
            bus.subscribe(event_type, self.chart_discovery)

    def chart_discovery(self, event):
        """Record the discovered room onto the discoverer's map; return the charted record."""
        location_id = parse_entity_id(_discovery_location_id(event))
        actor_id = parse_entity_id(getattr(event, "actor_id", None))
        if location_id is None or actor_id is None:
            return None
        if not self.world.has_entity(location_id) or not self.world.has_entity(actor_id):
            return None
        room = self.world.get_entity(location_id)
        if not room.has_component(RoomComponent):
            return None
        discoverer = self.world.get_entity(actor_id)
        map_entity = held_map_entity(self.world, discoverer)
        if map_entity is None:
            return None
        component = map_entity.get_component(MapComponent)
        record = record_for_room(room)
        if component.get(record.room_id) == record:
            return record
        replace_component(map_entity, replace(component, rooms=component.with_room(record).rooms))
        return record


__all__ = [
    "DISCOVERY_EVENT_SOURCES",
    "MOUNT_COMPONENT_SOURCES",
    "ExpeditionDiscoveryReactor",
    "expedition_pace",
    "is_mounted",
    "resolve_discovery_event_types",
    "resolve_mount_component_types",
]
