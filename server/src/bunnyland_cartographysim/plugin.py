"""Bunnyland plugin entrypoint for the out-of-tree cartographysim extension."""

from __future__ import annotations

from bunnyland.plugins import (
    CommandContribution,
    ContentContribution,
    DependencyContribution,
    EcsContribution,
    Plugin,
    RuntimeContribution,
)

from .annotations import (
    MapAnnotatedEvent,
    MapAnnotationsComponent,
    annotation_fragments,
)
from .commands import CARTOGRAPHY_ACTION_DEFINITIONS, CARTOGRAPHY_ACTION_HANDLERS
from .compass import compass_fragments
from .components import CompassComponent, LandmarkComponent, MapComponent
from .enrichment import CartographyGenerationEnricher
from .events import (
    LandmarkNamedEvent,
    TravelArrivedEvent,
    TravelStartedEvent,
    TravelStepEvent,
)
from .expeditions import (
    ExpeditionArrivedEvent,
    ExpeditionLegEvent,
    ExpeditionPlanComponent,
    ExpeditionStartedEvent,
)
from .fog import fog_fragments
from .install import install_cartographysim
from .landmarks import landmark_fragments
from .mapping import map_fragments
from .regions import LocatedInRegion, RegionGenerationEnricher, region_fragments
from .sharing import MapSharedEvent, SharedWith, share_fragments
from .surveys import LastSurveyComponent, RegionSurveyedEvent, survey_fragments
from .travel import TravelPlanComponent

PLUGIN_ID = "bunnyland.cartographysim"


def plugin() -> Plugin:
    return Plugin(
        id=PLUGIN_ID,
        name="Bunnyland Cartographysim",
        version="0.2.0",
        default_enabled=True,
        dependencies=DependencyContribution(
            recommends=(
                "bunnyland.memory",
                "bunnyland.storyteller",
                "bunnyland.petsim",
                "bunnyland.aquasim",
                "bunnyland.loresim",
                "bunnyland.cryptidsim",
            ),
        ),
        ecs=EcsContribution(
            components=(
                MapComponent,
                CompassComponent,
                LandmarkComponent,
                TravelPlanComponent,
                MapAnnotationsComponent,
                LastSurveyComponent,
                ExpeditionPlanComponent,
            ),
            edges=(LocatedInRegion, SharedWith),
        ),
        commands=CommandContribution(
            action_handlers=CARTOGRAPHY_ACTION_HANDLERS,
            action_definitions=CARTOGRAPHY_ACTION_DEFINITIONS,
            typed_events=(
                LandmarkNamedEvent,
                TravelStartedEvent,
                TravelStepEvent,
                TravelArrivedEvent,
                MapSharedEvent,
                MapAnnotatedEvent,
                RegionSurveyedEvent,
                ExpeditionStartedEvent,
                ExpeditionLegEvent,
                ExpeditionArrivedEvent,
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
                share_fragments,
                annotation_fragments,
                survey_fragments,
                region_fragments,
            ),
            generation_enrichers=(
                CartographyGenerationEnricher(),
                RegionGenerationEnricher(),
            ),
        ),
    )


def bunnyland_plugins() -> list[Plugin]:
    return [plugin()]


__all__ = ["PLUGIN_ID", "bunnyland_plugins", "plugin"]
