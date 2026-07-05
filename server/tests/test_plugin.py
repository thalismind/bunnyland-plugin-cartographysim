from __future__ import annotations

from bunnyland.core.world_actor import WorldActor
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_cartographysim import (
    CartographyWorldgenHook,
    CompassComponent,
    ExpeditionArrivedEvent,
    ExpeditionLegEvent,
    ExpeditionPlanComponent,
    ExpeditionStartedEvent,
    LandmarkComponent,
    LastSurveyComponent,
    MapAnnotatedEvent,
    MapAnnotationsComponent,
    MapComponent,
    MapSharedEvent,
    RegionComponent,
    RegionSurveyedEvent,
    RegionWorldgenHook,
    SharedWith,
    TravelPlanComponent,
    annotation_fragments,
    compass_fragments,
    fog_fragments,
    landmark_fragments,
    map_fragments,
    region_fragments,
    share_fragments,
    survey_fragments,
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


# -- v2 wiring --------------------------------------------------------------------------


def test_plugin_declares_its_v2_components_and_edge():
    plugin = load_modules(["bunnyland_cartographysim"])[0]
    for component in (
        MapAnnotationsComponent,
        LastSurveyComponent,
        ExpeditionPlanComponent,
        RegionComponent,
    ):
        assert component in plugin.ecs.components
    assert SharedWith in plugin.ecs.edges


def test_plugin_recommends_conditional_partner_packs():
    plugin = load_modules(["bunnyland_cartographysim"])[0]
    recommends = plugin.dependencies.recommends
    for partner in (
        "bunnyland.petsim",
        "bunnyland.aquasim",
        "bunnyland.loresim",
        "bunnyland.cryptidsim",
    ):
        assert partner in recommends


def test_plugin_declares_its_v2_fragments_and_region_hook():
    plugin = load_modules(["bunnyland_cartographysim"])[0]
    for fragment in (share_fragments, annotation_fragments, survey_fragments, region_fragments):
        assert fragment in plugin.content.prompt_fragments
    assert RegionWorldgenHook in plugin.content.worldgen_hooks


def test_plugin_declares_its_v2_events():
    plugin = load_modules(["bunnyland_cartographysim"])[0]
    for event in (
        MapSharedEvent,
        MapAnnotatedEvent,
        RegionSurveyedEvent,
        ExpeditionStartedEvent,
        ExpeditionLegEvent,
        ExpeditionArrivedEvent,
    ):
        assert event in plugin.commands.typed_events


def test_plugin_registers_its_v2_verbs():
    actor = WorldActor()
    apply_plugins(load_modules(["bunnyland_cartographysim"]), actor)
    command_types = {definition.command_type for definition in actor.action_definitions()}
    assert {"share-map", "annotate-map", "survey-region", "launch-expedition"} <= command_types


def test_bunnyland_plugins_returns_single_plugin():
    from bunnyland_cartographysim import bunnyland_plugins

    plugins = bunnyland_plugins()
    assert len(plugins) == 1
    assert plugins[0].id == PLUGIN_ID
