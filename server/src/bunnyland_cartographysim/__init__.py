"""Out-of-tree Bunnyland plugin: chart, name, and navigate the world graph.

Bundles five mechanics — a **field map** that records every room its holder visits, a
**compass** that names the current room's exits by direction, **landmarks** a character can
pin to a room, **fast-travel** that routes to any charted room over known exits, and
**fog of war** that renders unmapped ground as uncharted.
"""

from .commands import CARTOGRAPHY_ACTION_DEFINITIONS, CARTOGRAPHY_ACTION_HANDLERS
from .compass import compass_fragments, compass_lines
from .components import (
    ChartedExit,
    ChartedRoom,
    CompassComponent,
    LandmarkComponent,
    MapComponent,
)
from .enrichment import CartographyWorldgenHook, classify_landmark
from .events import (
    LandmarkNamedEvent,
    TravelArrivedEvent,
    TravelStartedEvent,
    TravelStepEvent,
)
from .fog import fog_fragments, frontier_lines, held_map
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
from .spatial import holder_of, room_of
from .travel import (
    TRAVEL_ACTION_DEFINITIONS,
    TRAVEL_ACTION_HANDLERS,
    TravelConsequence,
    TravelPlanComponent,
    TravelToHandler,
    plan_route,
)

__all__ = [
    "CARTOGRAPHY_ACTION_DEFINITIONS",
    "CARTOGRAPHY_ACTION_HANDLERS",
    "LANDMARK_ACTION_DEFINITIONS",
    "LANDMARK_ACTION_HANDLERS",
    "PLUGIN_ID",
    "TRAVEL_ACTION_DEFINITIONS",
    "TRAVEL_ACTION_HANDLERS",
    "CartographyWorldgenHook",
    "ChartedExit",
    "ChartedRoom",
    "CompassComponent",
    "LandmarkComponent",
    "LandmarkNamedEvent",
    "MapComponent",
    "MappingConsequence",
    "NameLandmarkHandler",
    "TravelArrivedEvent",
    "TravelConsequence",
    "TravelPlanComponent",
    "TravelStartedEvent",
    "TravelStepEvent",
    "TravelToHandler",
    "bunnyland_plugins",
    "charted_exits",
    "classify_landmark",
    "compass_fragments",
    "compass_lines",
    "fog_fragments",
    "frontier_lines",
    "held_map",
    "holder_of",
    "install_cartographysim",
    "landmark_fragments",
    "map_fragments",
    "plan_route",
    "plugin",
    "record_for_room",
    "room_of",
    "spawn_compass",
    "spawn_field_map",
]
