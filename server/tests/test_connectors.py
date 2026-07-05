from __future__ import annotations

from types import SimpleNamespace

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.ecs import replace_component
from pydantic.dataclasses import dataclass
from relics import Component

from bunnyland_cartographysim import (
    ExpeditionDiscoveryReactor,
    MapComponent,
    expedition_pace,
    is_mounted,
    record_for_room,
    resolve_discovery_event_types,
    resolve_mount_component_types,
    spawn_field_map,
)
from bunnyland_cartographysim.connectors import _resolve_imports


@dataclass(frozen=True)
class _FakeMount(Component):
    name: str = "pony"


def _room(world, *, title="Room"):
    return spawn_entity(world, [RoomComponent(title=title)])


def _character(world, room=None):
    character = spawn_entity(
        world, [IdentityComponent(name="Vin", kind="character"), CharacterComponent()]
    )
    if room is not None:
        room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


# -- import resolution ------------------------------------------------------------------


def test_resolve_imports_picks_up_existing_types_and_skips_the_rest():
    resolved = _resolve_imports(
        (
            ("bunnyland_cartographysim", "MapComponent"),  # a real type
            ("bunnyland_cartographysim", "PLUGIN_ID"),  # exists but not a type
            ("definitely_not_a_real_module_xyz", "Anything"),  # missing module
            ("bunnyland_cartographysim", "NoSuchSymbol"),  # missing attribute
        )
    )
    assert resolved == (MapComponent,)


def test_resolvers_default_to_absent_partners():
    # None of the partner packs are installed in this repo, so both resolve to empty.
    assert resolve_discovery_event_types() == ()
    assert resolve_mount_component_types() == ()


def test_resolvers_accept_explicit_sources():
    resolved = resolve_discovery_event_types(
        (("bunnyland_cartographysim", "MapComponent"),)
    )
    assert resolved == (MapComponent,)


# -- mounts -----------------------------------------------------------------------------


def test_is_mounted_false_without_any_mount_types():
    actor = WorldActor()
    character = _character(actor.world)
    assert is_mounted(actor.world, character, ()) is False


def test_is_mounted_true_with_held_mount():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)
    mount = spawn_entity(
        actor.world, [IdentityComponent(name="pony", kind="creature"), _FakeMount()]
    )
    character.add_relationship(Contains(mode=ContainmentMode.INVENTORY), mount.id)
    assert is_mounted(actor.world, character, (_FakeMount,)) is True


def test_is_mounted_false_without_a_mount_item():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)
    plain = spawn_entity(actor.world, [IdentityComponent(name="rope", kind="item")])
    character.add_relationship(Contains(mode=ContainmentMode.INVENTORY), plain.id)
    assert is_mounted(actor.world, character, (_FakeMount,)) is False


def test_is_mounted_skips_dangling_ids():
    actor = WorldActor()
    room = _room(actor.world)
    character = _character(actor.world, room)
    ghost = spawn_entity(actor.world, [IdentityComponent(name="ghost", kind="item")])
    character.add_relationship(Contains(mode=ContainmentMode.INVENTORY), ghost.id)
    actor.world.remove(ghost.id)
    assert is_mounted(actor.world, character, (_FakeMount,)) is False


def test_expedition_pace_doubles_when_mounted():
    assert expedition_pace(False) == 1
    assert expedition_pace(True) == 2


# -- discovery reactor ------------------------------------------------------------------


class _FakeDiscoveryEvent:
    def __init__(self, location_id, actor_id):
        self.location_id = location_id
        self.actor_id = actor_id


def _reactor_with_fake_event(world):
    # Inject an event type so the loaded path runs without a partner pack installed.
    return ExpeditionDiscoveryReactor(world, event_types=(_FakeDiscoveryEvent,))


def test_reactor_dormant_without_partners():
    actor = WorldActor()
    reactor = ExpeditionDiscoveryReactor(actor.world)
    assert reactor.active is False


def test_reactor_active_with_injected_event_type():
    actor = WorldActor()
    reactor = _reactor_with_fake_event(actor.world)
    assert reactor.active is True


def test_reactor_charts_a_discovered_room():
    actor = WorldActor()
    home = _room(actor.world, title="Home")
    found = _room(actor.world, title="Sunken Grotto")
    discoverer = _character(actor.world, home)
    field_map = spawn_field_map(actor.world)
    discoverer.add_relationship(Contains(mode=ContainmentMode.INVENTORY), field_map.id)

    reactor = _reactor_with_fake_event(actor.world)
    record = reactor.chart_discovery(
        _FakeDiscoveryEvent(location_id=str(found.id), actor_id=str(discoverer.id))
    )
    assert record is not None
    assert str(found.id) in field_map.get_component(MapComponent).charted_ids()


def test_reactor_is_idempotent_for_an_already_charted_room():
    actor = WorldActor()
    home = _room(actor.world, title="Home")
    found = _room(actor.world, title="Grotto")
    discoverer = _character(actor.world, home)
    field_map = spawn_field_map(actor.world)
    discoverer.add_relationship(Contains(mode=ContainmentMode.INVENTORY), field_map.id)
    replace_component(field_map, MapComponent(rooms=(record_for_room(found),)))
    before = field_map.get_component(MapComponent)

    reactor = _reactor_with_fake_event(actor.world)
    record = reactor.chart_discovery(
        _FakeDiscoveryEvent(location_id=str(found.id), actor_id=str(discoverer.id))
    )
    assert record == record_for_room(found)
    # No churn: same charted set.
    assert field_map.get_component(MapComponent).charted_ids() == before.charted_ids()


def test_reactor_subscribe_wires_the_bus():
    actor = WorldActor()
    home = _room(actor.world, title="Home")
    found = _room(actor.world, title="Grotto")
    discoverer = _character(actor.world, home)
    field_map = spawn_field_map(actor.world)
    discoverer.add_relationship(Contains(mode=ContainmentMode.INVENTORY), field_map.id)

    reactor = _reactor_with_fake_event(actor.world)
    reactor.subscribe(actor.bus)
    import asyncio

    asyncio.run(
        actor.bus.publish(
            _FakeDiscoveryEvent(location_id=str(found.id), actor_id=str(discoverer.id))
        )
    )
    assert str(found.id) in field_map.get_component(MapComponent).charted_ids()


def test_reactor_ignores_bad_ids_and_shapes():
    actor = WorldActor()
    home = _room(actor.world, title="Home")
    found = _room(actor.world, title="Grotto")
    discoverer = _character(actor.world, home)
    field_map = spawn_field_map(actor.world)
    discoverer.add_relationship(Contains(mode=ContainmentMode.INVENTORY), field_map.id)
    reactor = _reactor_with_fake_event(actor.world)

    # Unparseable ids.
    assert reactor.chart_discovery(_FakeDiscoveryEvent("???", str(discoverer.id))) is None
    assert reactor.chart_discovery(_FakeDiscoveryEvent(str(found.id), "???")) is None
    # Missing entities.
    assert reactor.chart_discovery(_FakeDiscoveryEvent("entity_9999", str(discoverer.id))) is None
    assert reactor.chart_discovery(_FakeDiscoveryEvent(str(found.id), "entity_9999")) is None


def test_reactor_ignores_non_room_locations():
    actor = WorldActor()
    home = _room(actor.world, title="Home")
    discoverer = _character(actor.world, home)
    field_map = spawn_field_map(actor.world)
    discoverer.add_relationship(Contains(mode=ContainmentMode.INVENTORY), field_map.id)
    not_a_room = spawn_entity(actor.world, [IdentityComponent(name="rock", kind="item")])
    reactor = _reactor_with_fake_event(actor.world)
    assert (
        reactor.chart_discovery(
            _FakeDiscoveryEvent(str(not_a_room.id), str(discoverer.id))
        )
        is None
    )


def test_reactor_ignores_a_discoverer_without_a_map():
    actor = WorldActor()
    home = _room(actor.world, title="Home")
    found = _room(actor.world, title="Grotto")
    discoverer = _character(actor.world, home)  # holds no map
    reactor = _reactor_with_fake_event(actor.world)
    event = SimpleNamespace(location_id=str(found.id), actor_id=str(discoverer.id))
    assert reactor.chart_discovery(event) is None
