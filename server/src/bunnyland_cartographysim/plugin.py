"""Bunnyland plugin entrypoint for the out-of-tree cartographysim extension."""

from __future__ import annotations

from bunnyland.plugins import (
    CommandContribution,
    ContentContribution,
    EcsContribution,
    Plugin,
    RuntimeContribution,
)

from .commands import CARTOGRAPHY_ACTION_DEFINITIONS, CARTOGRAPHY_ACTION_HANDLERS
from .compass import compass_fragments
from .components import CompassComponent, LandmarkComponent, MapComponent
from .enrichment import CartographyWorldgenHook
from .events import (
    LandmarkNamedEvent,
    TravelArrivedEvent,
    TravelStartedEvent,
    TravelStepEvent,
)
from .fog import fog_fragments
from .install import install_cartographysim
from .landmarks import landmark_fragments
from .mapping import map_fragments
from .travel import TravelPlanComponent

PLUGIN_ID = "bunnyland_cartographysim"


def plugin() -> Plugin:
    return Plugin(
        id=PLUGIN_ID,
        name="Bunnyland Cartographysim",
        version="0.1.0",
        default_enabled=True,
        ecs=EcsContribution(
            components=(
                MapComponent,
                CompassComponent,
                LandmarkComponent,
                TravelPlanComponent,
            ),
        ),
        commands=CommandContribution(
            action_handlers=CARTOGRAPHY_ACTION_HANDLERS,
            action_definitions=CARTOGRAPHY_ACTION_DEFINITIONS,
            typed_events=(
                LandmarkNamedEvent,
                TravelStartedEvent,
                TravelStepEvent,
                TravelArrivedEvent,
            ),
        ),
        runtime=RuntimeContribution(
            service_factories=(install_cartographysim,),
        ),
        content=ContentContribution(
            prompt_fragments=(
                map_fragments,
                compass_fragments,
                landmark_fragments,
                fog_fragments,
            ),
            worldgen_hooks=(CartographyWorldgenHook,),
        ),
    )


def bunnyland_plugins() -> list[Plugin]:
    return [plugin()]


__all__ = ["PLUGIN_ID", "bunnyland_plugins", "plugin"]
