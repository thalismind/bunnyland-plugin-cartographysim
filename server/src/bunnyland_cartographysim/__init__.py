"""Out-of-tree Bunnyland plugin: chart, name, and navigate the world graph.

Bundles five mechanics — a **field map** that records every room its holder visits, a
**compass** that names the current room's exits by direction, **landmarks** a character can
pin to a room, **fast-travel** that routes to any charted room over known exits, and
**fog of war** that renders unmapped ground as uncharted.
"""

from .annotations import (
    ANNOTATE_MAP_DEF,
    AnnotateMapHandler,
    MapAnnotatedEvent,
    MapAnnotationsComponent,
    MapNote,
    annotation_fragments,
)
from .commands import CARTOGRAPHY_ACTION_DEFINITIONS, CARTOGRAPHY_ACTION_HANDLERS
from .compass import compass_fragments, compass_lines
from .components import (
    ChartedExit,
    ChartedRoom,
    CompassComponent,
    LandmarkComponent,
    MapComponent,
)
from .connectors import (
    DISCOVERY_EVENT_SOURCES,
    MOUNT_COMPONENT_SOURCES,
    ExpeditionDiscoveryReactor,
    expedition_pace,
    is_mounted,
    resolve_discovery_event_types,
    resolve_mount_component_types,
)
from .enrichment import CartographyGenerationEnricher, classify_landmark
from .events import (
    LandmarkNamedEvent,
    TravelArrivedEvent,
    TravelStartedEvent,
    TravelStepEvent,
)
from .expeditions import (
    EXPEDITION_ACTION_DEFINITIONS,
    EXPEDITION_ACTION_HANDLERS,
    LAUNCH_EXPEDITION_DEF,
    ExpeditionArrivedEvent,
    ExpeditionConsequence,
    ExpeditionLegEvent,
    ExpeditionPlanComponent,
    ExpeditionStartedEvent,
    LaunchExpeditionHandler,
)
from .fog import fog_fragments, frontier_lines, held_map
from .holding import held_map_entity
from .incidents import (
    INCIDENT_KIND,
    UnchartedRegionIncidentConsequence,
    stage_uncharted_region_incident,
    uncharted_frontier_rooms,
)
from .install import install_cartographysim
from .landmarks import (
    LANDMARK_ACTION_DEFINITIONS,
    LANDMARK_ACTION_HANDLERS,
    NameLandmarkHandler,
    landmark_fragments,
)
from .mapping import MappingConsequence, charted_exits, map_fragments, record_for_room
from .plugin import PLUGIN_ID, bunnyland_plugins, plugin
from .prefabs import spawn_compass, spawn_field_map
from .regions import (
    LocatedInRegion,
    RegionGenerationEnricher,
    region_fragments,
    region_name_for,
)
from .sharing import (
    SHARE_ACTION_DEFINITIONS,
    SHARE_ACTION_HANDLERS,
    SHARE_MAP_DEF,
    MapSharedEvent,
    SharedWith,
    ShareMapHandler,
    is_shared_with,
    maps_shared_with,
    share_fragments,
)
from .spatial import holder_of, room_of
from .surveys import (
    SURVEY_ACTION_DEFINITIONS,
    SURVEY_ACTION_HANDLERS,
    SURVEY_REGION_DEF,
    LastSurveyComponent,
    RegionSurvey,
    RegionSurveyedEvent,
    SurveyMemoryReactor,
    SurveyRegionHandler,
    survey_fragments,
    survey_region,
    survey_summary,
)
from .travel import (
    TRAVEL_ACTION_DEFINITIONS,
    TRAVEL_ACTION_HANDLERS,
    TravelConsequence,
    TravelPlanComponent,
    TravelToHandler,
    plan_route,
)

__all__ = [
    "ANNOTATE_MAP_DEF",
    "CARTOGRAPHY_ACTION_DEFINITIONS",
    "CARTOGRAPHY_ACTION_HANDLERS",
    "DISCOVERY_EVENT_SOURCES",
    "EXPEDITION_ACTION_DEFINITIONS",
    "EXPEDITION_ACTION_HANDLERS",
    "INCIDENT_KIND",
    "LANDMARK_ACTION_DEFINITIONS",
    "LANDMARK_ACTION_HANDLERS",
    "LAUNCH_EXPEDITION_DEF",
    "MOUNT_COMPONENT_SOURCES",
    "PLUGIN_ID",
    "SHARE_ACTION_DEFINITIONS",
    "SHARE_ACTION_HANDLERS",
    "SHARE_MAP_DEF",
    "SURVEY_ACTION_DEFINITIONS",
    "SURVEY_ACTION_HANDLERS",
    "SURVEY_REGION_DEF",
    "TRAVEL_ACTION_DEFINITIONS",
    "TRAVEL_ACTION_HANDLERS",
    "AnnotateMapHandler",
    "CartographyGenerationEnricher",
    "ChartedExit",
    "ChartedRoom",
    "CompassComponent",
    "ExpeditionArrivedEvent",
    "ExpeditionConsequence",
    "ExpeditionDiscoveryReactor",
    "ExpeditionLegEvent",
    "ExpeditionPlanComponent",
    "ExpeditionStartedEvent",
    "LandmarkComponent",
    "LandmarkNamedEvent",
    "LastSurveyComponent",
    "LaunchExpeditionHandler",
    "MapAnnotatedEvent",
    "MapAnnotationsComponent",
    "MapComponent",
    "MapNote",
    "MapSharedEvent",
    "MappingConsequence",
    "NameLandmarkHandler",
    "LocatedInRegion",
    "RegionSurvey",
    "RegionSurveyedEvent",
    "RegionGenerationEnricher",
    "ShareMapHandler",
    "SharedWith",
    "SurveyMemoryReactor",
    "SurveyRegionHandler",
    "TravelArrivedEvent",
    "TravelConsequence",
    "TravelPlanComponent",
    "TravelStartedEvent",
    "TravelStepEvent",
    "TravelToHandler",
    "UnchartedRegionIncidentConsequence",
    "annotation_fragments",
    "bunnyland_plugins",
    "charted_exits",
    "classify_landmark",
    "compass_fragments",
    "compass_lines",
    "expedition_pace",
    "fog_fragments",
    "frontier_lines",
    "held_map",
    "held_map_entity",
    "holder_of",
    "install_cartographysim",
    "is_mounted",
    "is_shared_with",
    "landmark_fragments",
    "map_fragments",
    "maps_shared_with",
    "plan_route",
    "plugin",
    "record_for_room",
    "region_fragments",
    "region_name_for",
    "resolve_discovery_event_types",
    "resolve_mount_component_types",
    "room_of",
    "share_fragments",
    "spawn_compass",
    "spawn_field_map",
    "stage_uncharted_region_incident",
    "survey_fragments",
    "survey_region",
    "survey_summary",
    "uncharted_frontier_rooms",
]
