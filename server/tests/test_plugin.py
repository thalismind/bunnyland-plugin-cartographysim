from __future__ import annotations

from bunnyland.core.world_actor import WorldActor
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_cartographysim import (
    CartographyWorldgenHook,
    CompassComponent,
    LandmarkComponent,
    MapComponent,
    TravelPlanComponent,
    compass_fragments,
    fog_fragments,
    landmark_fragments,
    map_fragments,
)
from bunnyland_cartographysim.plugin import PLUGIN_ID


def test_plugin_loads_with_module_qualified_id():
    plugins = load_modules(["bunnyland_cartographysim"])
    assert [p.id for p in plugins] == [PLUGIN_ID]


def test_plugin_declares_its_components():
    plugin = load_modules(["bunnyland_cartographysim"])[0]
    for component in (
        MapComponent,
        CompassComponent,
        LandmarkComponent,
        TravelPlanComponent,
    ):
        assert component in plugin.ecs.components


def test_plugin_declares_its_fragments_and_hook():
    plugin = load_modules(["bunnyland_cartographysim"])[0]
    for fragment in (map_fragments, compass_fragments, landmark_fragments, fog_fragments):
        assert fragment in plugin.content.prompt_fragments
    assert CartographyWorldgenHook in plugin.content.worldgen_hooks


def test_plugin_version():
    plugin = load_modules(["bunnyland_cartographysim"])[0]
    assert plugin.version == "0.2.0"


def test_plugin_applies_and_registers_verbs():
    actor = WorldActor()
    applied = apply_plugins(load_modules(["bunnyland_cartographysim"]), actor)
    assert applied[0].id == PLUGIN_ID
    command_types = {definition.command_type for definition in actor.action_definitions()}
    assert {"name-landmark", "travel-to"} <= command_types
