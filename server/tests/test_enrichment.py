import asyncio

from bunnyland.core import WorldActor
from bunnyland.plugins import apply_plugins
from bunnyland.worldgen import ObjectSpec, RoomSpec, WorldProposal, instantiate

from bunnyland_aquasim import SubmergedComponent, TreasureCacheComponent
from bunnyland_aquasim.plugin import bunnyland_plugins as _plugins


def _world(*, room=None, object_=None):
    actor = WorldActor()
    apply_plugins(_plugins(), actor)
    result = asyncio.run(
        instantiate(
            actor,
            WorldProposal(
                seed="seed",
                rooms=[room or RoomSpec(key="room", title="Room")],
                objects=[object_] if object_ else [],
            ),
        )
    )
    return actor, result


def test_aquatic_and_flooded_rooms_are_submerged():
    actor, result = _world(room=RoomSpec(key="reef", title="Reef", biome="reef"))
    assert actor.world.get_entity(result.rooms["reef"]).has_component(SubmergedComponent)
    actor, result = _world(
        room=RoomSpec(key="grotto", title="Grotto", description="a flooded sunken grotto")
    )
    assert actor.world.get_entity(result.rooms["grotto"]).has_component(SubmergedComponent)


def test_dry_room_is_ignored():
    actor, result = _world(room=RoomSpec(key="field", title="Field", biome="meadow"))
    assert not actor.world.get_entity(result.rooms["field"]).has_component(SubmergedComponent)


def test_treasure_objects_become_caches_and_plain_objects_do_not():
    actor, result = _world(object_=ObjectSpec(key="chest", name="Treasure Chest", room_key="room"))
    assert (
        actor.world.get_entity(result.objects["chest"]).get_component(TreasureCacheComponent).table
    )
    actor, result = _world(object_=ObjectSpec(key="rock", name="Rock", room_key="room"))
    assert not actor.world.get_entity(result.objects["rock"]).has_component(TreasureCacheComponent)
