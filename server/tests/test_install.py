from __future__ import annotations

from bunnyland.core import WorldActor

from bunnyland_cartographysim import connectors, install
from bunnyland_cartographysim.install import install_cartographysim


class _FakeEvent:
    pass


def _registered_types(actor):
    # WorldActor stores registered consequences; introspect by class name for robustness.
    consequences = getattr(actor, "_consequences", None) or getattr(actor, "consequences", ())
    return {type(c).__name__ for c in consequences}


def test_install_registers_all_consequences_standalone(caplog):
    actor = WorldActor()
    with caplog.at_level("WARNING"):
        install_cartographysim(actor)
    names = _registered_types(actor)
    assert {
        "MappingConsequence",
        "TravelConsequence",
        "ExpeditionConsequence",
        "UnchartedRegionIncidentConsequence",
    } <= names
    # With no partner packs installed, both synergies warn that they are disabled.
    messages = " ".join(r.message for r in caplog.records)
    assert "discovery charting disabled" in messages
    assert "mount-boosted expeditions disabled" in messages


def test_install_wires_synergies_when_partners_present(monkeypatch, caplog):
    # Simulate loaded partner packs so the active synergy branches run.
    monkeypatch.setattr(
        connectors, "resolve_discovery_event_types", lambda sources=None: (_FakeEvent,)
    )
    monkeypatch.setattr(install, "resolve_mount_component_types", lambda: (object,))

    actor = WorldActor()
    with caplog.at_level("WARNING"):
        install_cartographysim(actor)

    messages = " ".join(r.message for r in caplog.records)
    # Neither synergy warns when its partner is present.
    assert "discovery charting disabled" not in messages
    assert "mount-boosted expeditions disabled" not in messages
