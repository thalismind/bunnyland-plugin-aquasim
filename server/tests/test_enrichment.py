from __future__ import annotations

import asyncio

from bunnyland.core import (
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.components import GenerationIntentComponent
from bunnyland.core.events import ObjectGeneratedEvent, RoomGeneratedEvent, event_base
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_aquasim import SubmergedComponent, TreasureCacheComponent


def _actor():
    actor = WorldActor()
    apply_plugins(load_modules(["bunnyland_aquasim"]), actor)
    return actor


def _publish(actor, event):
    asyncio.run(actor.bus.publish(event))


def _room(actor, *, biome="unknown", tags=(), description=""):
    entity = spawn_entity(actor.world, [RoomComponent(title="Room", biome=biome)])
    event = RoomGeneratedEvent(
        **event_base(0),
        seed="seed",
        entity_id=str(entity.id),
        entity_key="room",
        entity_kind="room",
        generation=GenerationIntentComponent(tags=tuple(tags), description=description),
        room_key="room",
        biome=biome,
    )
    _publish(actor, event)
    return entity


def _object(actor, *, tags=(), description=""):
    entity = spawn_entity(actor.world, [IdentityComponent(name="thing", kind="item")])
    event = ObjectGeneratedEvent(
        **event_base(0),
        seed="seed",
        entity_id=str(entity.id),
        entity_key="thing",
        entity_kind="object",
        generation=GenerationIntentComponent(tags=tuple(tags), description=description),
        object_key="thing",
    )
    _publish(actor, event)
    return entity


def test_aquatic_biome_room_is_flooded():
    actor = _actor()
    room = _room(actor, biome="reef")
    assert room.has_component(SubmergedComponent)


def test_wet_description_floods_a_room():
    actor = _actor()
    room = _room(actor, biome="cavern", description="a flooded sunken grotto")
    assert room.has_component(SubmergedComponent)


def test_dry_room_is_not_flooded():
    actor = _actor()
    room = _room(actor, biome="meadow", tags=("grassy",), description="a sunny hill")
    assert not room.has_component(SubmergedComponent)


def test_treasure_object_becomes_a_cache():
    actor = _actor()
    obj = _object(actor, tags=("treasure", "chest"))
    assert obj.has_component(TreasureCacheComponent)
    assert obj.get_component(TreasureCacheComponent).table


def test_treasure_detected_from_description():
    actor = _actor()
    obj = _object(actor, description="a sunken shipwreck full of gold")
    assert obj.has_component(TreasureCacheComponent)


def test_plain_object_is_not_a_cache():
    actor = _actor()
    obj = _object(actor, tags=("wooden", "crate"))
    assert not obj.has_component(TreasureCacheComponent)
