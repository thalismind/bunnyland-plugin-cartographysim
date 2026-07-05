"""Aggregated player/AI verb surface for the cartography pack.

The individual verbs live with their mechanics (``name-landmark`` in :mod:`landmarks`,
``travel-to`` in :mod:`travel`, and the v2 verbs ``share-map``, ``annotate-map``,
``survey-region`` and ``launch-expedition`` in their own modules); this module gathers their
action definitions and handlers into the single tuples the plugin registers.
"""

from __future__ import annotations

from .annotations import ANNOTATION_ACTION_DEFINITIONS, ANNOTATION_ACTION_HANDLERS
from .expeditions import EXPEDITION_ACTION_DEFINITIONS, EXPEDITION_ACTION_HANDLERS
from .landmarks import LANDMARK_ACTION_DEFINITIONS, LANDMARK_ACTION_HANDLERS
from .sharing import SHARE_ACTION_DEFINITIONS, SHARE_ACTION_HANDLERS
from .surveys import SURVEY_ACTION_DEFINITIONS, SURVEY_ACTION_HANDLERS
from .travel import TRAVEL_ACTION_DEFINITIONS, TRAVEL_ACTION_HANDLERS

CARTOGRAPHY_ACTION_DEFINITIONS = (
    LANDMARK_ACTION_DEFINITIONS
    + TRAVEL_ACTION_DEFINITIONS
    + SHARE_ACTION_DEFINITIONS
    + ANNOTATION_ACTION_DEFINITIONS
    + SURVEY_ACTION_DEFINITIONS
    + EXPEDITION_ACTION_DEFINITIONS
)
CARTOGRAPHY_ACTION_HANDLERS = (
    LANDMARK_ACTION_HANDLERS
    + TRAVEL_ACTION_HANDLERS
    + SHARE_ACTION_HANDLERS
    + ANNOTATION_ACTION_HANDLERS
    + SURVEY_ACTION_HANDLERS
    + EXPEDITION_ACTION_HANDLERS
)


__all__ = ["CARTOGRAPHY_ACTION_DEFINITIONS", "CARTOGRAPHY_ACTION_HANDLERS"]
