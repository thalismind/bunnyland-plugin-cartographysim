import asyncio

from bunnyland.core import WorldActor
from bunnyland.plugins import apply_plugins
from bunnyland.worldgen import RoomSpec, WorldProposal, instantiate

from bunnyland_cartographysim import LandmarkComponent
from bunnyland_cartographysim.plugin import bunnyland_plugins as _plugins


def _room(*, biome="unknown", title="Somewhere", description=""):
    actor = WorldActor()
    apply_plugins(_plugins(), actor)
    proposal = WorldProposal(
        seed="seed",
        rooms=[
            RoomSpec(
                key="room",
                title=title,
                biome=biome,
                description=description,
            )
        ],
    )
    result = asyncio.run(instantiate(actor, proposal))
    return actor.world.get_entity(result.rooms["room"])


def test_crossroads_room_gets_a_landmark():
    room = _room(title="Crossroads")
    assert room.get_component(LandmarkComponent).name == "the Crossroads"


def test_peak_seeded_from_biome():
    assert _room(biome="mountain").get_component(LandmarkComponent).kind == "peak"


def test_ruin_seeded_from_description():
    room = _room(description="a derelict tower long abandoned")
    assert room.get_component(LandmarkComponent).kind == "ruin"


def test_plain_room_gets_no_landmark():
    assert not _room(biome="meadow", description="a quiet field").has_component(LandmarkComponent)


def test_first_matching_rule_wins():
    room = _room(title="Cave Crossroads")
    assert room.get_component(LandmarkComponent).name == "the Crossroads"
