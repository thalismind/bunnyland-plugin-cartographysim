"""Runtime wiring: register the per-tick consequences on a world actor."""

from __future__ import annotations

from bunnyland.core.world_actor import WorldActor

from .mapping import MappingConsequence
from .travel import TravelConsequence


def install_cartographysim(actor: WorldActor) -> None:
    """Register the mapping and fast-travel consequences (a ``service_factories`` entry)."""
    actor.register_consequence(MappingConsequence())
    actor.register_consequence(TravelConsequence())


__all__ = ["install_cartographysim"]
