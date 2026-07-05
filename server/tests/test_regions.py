from __future__ import annotations

import asyncio

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.components import GenerationIntentComponent
from bunnyland.core.events import RoomGeneratedEvent, event_base
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_cartographysim import (
    RegionComponent,
    RegionWorldgenHook,
    region_fragments,
    region_name_for,
)


def _actor():
    actor = WorldActor()
    apply_plugins(load_modules(["bunnyland_cartographysim"]), actor)
    return actor


def _room(world, *, title="Somewhere", biome="forest"):
    return spawn_entity(world, [RoomComponent(title=title, biome=biome)])


def _character(world, room):
    character = spawn_entity(
        world, [IdentityComponent(name="Vin", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def _generate(actor, room, *, biome="forest"):
    event = RoomGeneratedEvent(
        **event_base(0),
        seed="seed",
        entity_id=str(room.id),
        entity_key="room",
        entity_kind="room",
        generation=GenerationIntentComponent(),
        room_key="room",
        biome=biome,
    )
    asyncio.run(actor.bus.publish(event))


# -- naming -----------------------------------------------------------------------------


def test_region_name_for_known_biomes():
    assert region_name_for("forest") == "the Whispering Wilds"
    assert region_name_for("Desert") == "the Sunscoured Waste"


def test_region_name_for_unknown_biome_titles_it():
    assert region_name_for("glacier") == "the Glacier Reaches"


def test_region_name_for_blank_biome():
    assert region_name_for("   ") == "the Unknown Reaches"


# -- worldgen hook ----------------------------------------------------------------------


def test_hook_paints_a_region_onto_a_generated_room():
    actor = _actor()
    room = _room(actor.world, biome="mountain")
    _generate(actor, room, biome="mountain")
    region = room.get_component(RegionComponent)
    assert region.name == "the Cloudpiercer Range"
    assert region.biome == "mountain"


def test_hook_is_idempotent():
    actor = _actor()
    room = _room(actor.world, biome="forest")
    _generate(actor, room, biome="forest")
    first = room.get_component(RegionComponent)
    _generate(actor, room, biome="forest")
    assert room.get_component(RegionComponent) is first  # not repainted


def test_hook_ignores_missing_entities():
    actor = _actor()
    hook = RegionWorldgenHook()
    hook.subscribe(actor)
    event = RoomGeneratedEvent(
        **event_base(0),
        seed="seed",
        entity_id="entity_9999",
        entity_key="room",
        entity_kind="room",
        generation=GenerationIntentComponent(),
        room_key="room",
        biome="forest",
    )
    asyncio.run(actor.bus.publish(event))  # must not raise


def test_hook_ignores_non_room_entities():
    actor = _actor()
    item = spawn_entity(actor.world, [IdentityComponent(name="rock", kind="item")])
    _generate(actor, item, biome="forest")
    assert not item.has_component(RegionComponent)


# -- fragments --------------------------------------------------------------------------


def test_region_fragment_names_the_region():
    actor = _actor()
    room = _room(actor.world)
    room.add_component(RegionComponent(name="the Whispering Wilds", biome="forest"))
    visitor = _character(actor.world, room)
    assert region_fragments(actor.world, visitor) == ["This lies within the Whispering Wilds."]


def test_region_fragment_empty_without_a_region_or_character():
    actor = _actor()
    room = _room(actor.world)
    visitor = _character(actor.world, room)
    assert region_fragments(actor.world, None) == []
    assert region_fragments(actor.world, visitor) == []
