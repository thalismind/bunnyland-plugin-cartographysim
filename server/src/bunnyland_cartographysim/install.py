"""Runtime wiring: register the per-tick consequences and reactors on a world actor."""

from __future__ import annotations

import logging

from bunnyland.core.world_actor import WorldActor

from .connectors import (
    ExpeditionDiscoveryReactor,
    resolve_mount_component_types,
)
from .expeditions import ExpeditionConsequence
from .incidents import UnchartedRegionIncidentConsequence
from .mapping import MappingConsequence
from .surveys import SurveyMemoryReactor
from .travel import TravelConsequence

LOG = logging.getLogger(__name__)


def install_cartographysim(actor: WorldActor) -> None:
    """Register cartography consequences and optional synergy reactors (a service factory)."""
    actor.register_consequence(MappingConsequence())
    actor.register_consequence(TravelConsequence())
    actor.register_consequence(ExpeditionConsequence())
    actor.register_consequence(UnchartedRegionIncidentConsequence())

    # Persist surveys to the core memory store, resolved lazily so plugin order never matters.
    SurveyMemoryReactor(lambda: getattr(actor, "memory_store", None)).subscribe(actor.bus)

    # Optional synergy: chart partner-pack discoveries. Dormant (with a warning) if no partner.
    discovery = ExpeditionDiscoveryReactor(actor.world)
    if discovery.active:
        discovery.subscribe(actor.bus)
    else:
        LOG.warning(
            "cartographysim: no expedition partner pack loaded; discovery charting disabled"
        )

    # Optional synergy: petsim mounts speed expeditions. Warn if the partner pack is absent.
    if not resolve_mount_component_types():
        LOG.warning("cartographysim: petsim not loaded; mount-boosted expeditions disabled")


__all__ = ["install_cartographysim"]
