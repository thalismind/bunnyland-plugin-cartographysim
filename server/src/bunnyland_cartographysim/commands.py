"""Aggregated player/AI verb surface for the cartography pack.

The individual verbs live with their mechanics (``name-landmark`` in :mod:`landmarks`,
``travel-to`` in :mod:`travel`); this module gathers their action definitions and handlers
into the single tuples the plugin registers.
"""

from __future__ import annotations

from .landmarks import LANDMARK_ACTION_DEFINITIONS, LANDMARK_ACTION_HANDLERS
from .travel import TRAVEL_ACTION_DEFINITIONS, TRAVEL_ACTION_HANDLERS

CARTOGRAPHY_ACTION_DEFINITIONS = LANDMARK_ACTION_DEFINITIONS + TRAVEL_ACTION_DEFINITIONS
CARTOGRAPHY_ACTION_HANDLERS = LANDMARK_ACTION_HANDLERS + TRAVEL_ACTION_HANDLERS


__all__ = ["CARTOGRAPHY_ACTION_DEFINITIONS", "CARTOGRAPHY_ACTION_HANDLERS"]
