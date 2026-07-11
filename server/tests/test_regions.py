from __future__ import annotations

import asyncio

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RegionComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.plugins import apply_plugins
from bunnyland.worldgen import RoomSpec, WorldProposal, instantiate

from bunnyland_cartographysim import LocatedInRegion, region_fragments, region_name_for
from bunnyland_cartographysim.plugin import bunnyland_plugins as _plugins


def _world(*rooms: RoomSpec):
    actor = WorldActor()
    apply_plugins(_plugins(), actor)
    result = asyncio.run(instantiate(actor, WorldProposal(seed="seed", rooms=list(rooms))))
    return actor, result


def test_region_name_for_known_and_unknown_biomes():
    assert region_name_for("forest") == "the Whispering Wilds"
    assert region_name_for("Desert") == "the Sunscoured Waste"
    assert region_name_for("glacier") == "the Glacier Reaches"
    assert region_name_for("   ") == "the Unknown Reaches"


def test_generation_links_room_to_region_entity():
    actor, result = _world(RoomSpec(key="peak", title="Peak", biome="mountain"))
    room = actor.world.get_entity(result.rooms["peak"])
    relationships = room.get_relationships(LocatedInRegion)
    assert len(relationships) == 1
    region = actor.world.get_entity(relationships[0][1])
    assert region.get_component(RegionComponent).name == "the Cloudpiercer Range"
    assert region.get_component(RegionComponent).climate == "mountain"


def test_rooms_in_same_biome_share_region_entity():
    actor, result = _world(
        RoomSpec(key="one", title="One", biome="forest"),
        RoomSpec(key="two", title="Two", biome="forest"),
    )
    one = actor.world.get_entity(result.rooms["one"])
    two = actor.world.get_entity(result.rooms["two"])
    assert (
        one.get_relationships(LocatedInRegion)[0][1] == two.get_relationships(LocatedInRegion)[0][1]
    )


def test_region_fragment_names_linked_region():
    actor, result = _world(RoomSpec(key="room", title="Room", biome="forest"))
    room = actor.world.get_entity(result.rooms["room"])
    visitor = spawn_entity(
        actor.world,
        [IdentityComponent(name="Vin", kind="character"), CharacterComponent()],
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), visitor.id)
    assert region_fragments(actor.world, visitor) == ["This lies within the Whispering Wilds."]


def test_region_fragment_empty_without_character_or_relationship():
    actor, result = _world(RoomSpec(key="room", title="Room", biome="forest"))
    room = actor.world.get_entity(result.rooms["room"])
    visitor = spawn_entity(
        actor.world,
        [IdentityComponent(name="Vin", kind="character"), CharacterComponent()],
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), visitor.id)
    for _edge, target_id in room.get_relationships(LocatedInRegion):
        room.remove_relationship(LocatedInRegion, target_id)
    assert region_fragments(actor.world, None) == []
    assert region_fragments(actor.world, visitor) == []
