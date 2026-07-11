"""Declarative natural-landmark generation enrichment."""

from __future__ import annotations

from bunnyland.core.generation import GenerationDelta, GenerationRequest

from .components import LandmarkComponent

NATURAL_LANDMARKS: tuple[tuple[tuple[str, ...], str, str], ...] = (
    (("crossroads", "junction", "crossing"), "crossroads", "the Crossroads"),
    (("peak", "summit", "mountain", "ridge", "cliff"), "peak", "the High Peak"),
    (("ruin", "ruins", "ancient", "derelict", "forgotten"), "ruin", "the Old Ruins"),
    (("shrine", "temple", "altar", "sanctuary"), "shrine", "the Forgotten Shrine"),
    (("cave", "cavern", "grotto", "hollow"), "cave", "the Deep Cavern"),
)


def classify_landmark(request: GenerationRequest) -> tuple[str, str] | None:
    """Return the natural landmark cued by a generation request, if any."""
    text = " ".join(
        (
            request.entity_kind,
            str(request.context.get("biome", "")),
            request.description,
            *request.tags,
        )
    ).casefold()
    for terms, kind, name in NATURAL_LANDMARKS:
        if any(term in text for term in terms):
            return kind, name
    return None


class CartographyGenerationEnricher:
    """Attach a landmark component to memorable generated rooms."""

    capabilities: tuple[str, ...] = ()

    def applies(self, request: GenerationRequest) -> bool:
        if request.entity_kind != "room":
            return False
        return not any(
            isinstance(component, LandmarkComponent)
            for component in request.context.get("base_components", ())
        )

    def enrich(self, request: GenerationRequest) -> GenerationDelta:
        classified = classify_landmark(request)
        if classified is None:
            return GenerationDelta()
        kind, name = classified
        return GenerationDelta(components=(LandmarkComponent(name=name, kind=kind, shared=True),))


__all__ = [
    "NATURAL_LANDMARKS",
    "CartographyGenerationEnricher",
    "classify_landmark",
]
