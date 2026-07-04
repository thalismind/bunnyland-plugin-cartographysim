from __future__ import annotations

import asyncio

from bunnyland.core import (
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.components import GenerationIntentComponent
from bunnyland.core.events import RoomGeneratedEvent, event_base
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_cartographysim import LandmarkComponent


def _actor():
    actor = WorldActor()
    apply_plugins(load_modules(["bunnyland_cartographysim"]), actor)
    return actor


def _publish(actor, event):
    asyncio.run(actor.bus.publish(event))


def _generate_room(actor, *, title="Somewhere", biome="unknown", tags=(), description=""):
    room = spawn_entity(actor.world, [RoomComponent(title=title, biome=biome)])
    event = RoomGeneratedEvent(
        **event_base(0),
        seed="seed",
        entity_id=str(room.id),
        entity_key="room",
        entity_kind="room",
        generation=GenerationIntentComponent(tags=tuple(tags), description=description),
        room_key="room",
        biome=biome,
    )
    _publish(actor, event)
    return room


def test_crossroads_room_gets_a_landmark():
    actor = _actor()
    room = _generate_room(actor, tags=("crossroads",))
    assert room.has_component(LandmarkComponent)
    assert room.get_component(LandmarkComponent).name == "the Crossroads"


def test_peak_seeded_from_biome():
    actor = _actor()
    room = _generate_room(actor, biome="mountain")
    assert room.get_component(LandmarkComponent).kind == "peak"


def test_ruin_seeded_from_description():
    actor = _actor()
    room = _generate_room(actor, description="a derelict tower long abandoned")
    assert room.get_component(LandmarkComponent).kind == "ruin"


def test_plain_room_gets_no_landmark():
    actor = _actor()
    room = _generate_room(actor, biome="meadow", tags=("grassy",), description="a quiet field")
    assert not room.has_component(LandmarkComponent)


def test_first_matching_rule_wins():
    actor = _actor()
    # Both "crossroads" and "cave" cue; the ordered rules put crossroads first.
    room = _generate_room(actor, tags=("cave", "crossroads"))
    assert room.get_component(LandmarkComponent).name == "the Crossroads"


def test_existing_landmark_is_not_overwritten():
    actor = _actor()
    room = spawn_entity(actor.world, [RoomComponent(title="Named"), LandmarkComponent(name="Home")])
    event = RoomGeneratedEvent(
        **event_base(0),
        seed="seed",
        entity_id=str(room.id),
        entity_key="room",
        entity_kind="room",
        generation=GenerationIntentComponent(tags=("ruin",)),
        room_key="room",
        biome="ruin",
    )
    _publish(actor, event)
    assert room.get_component(LandmarkComponent).name == "Home"
