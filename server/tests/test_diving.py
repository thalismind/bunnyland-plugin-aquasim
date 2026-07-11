from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    ExitTo,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    contents,
    spawn_entity,
)
from bunnyland.core.commands import CommandCost, Lane, build_submitted_command
from bunnyland.core.handlers import HandlerContext
from bunnyland.foundation.meters.mechanics import Meter

from bunnyland_aquasim import (
    BreathComponent,
    SubmergedComponent,
    SurfacedEvent,
    SurfaceHandler,
    SwimSkillComponent,
    TreasureCacheComponent,
    TreasureRecoveredEvent,
    deterministic_loot,
    spawn_treasure_cache,
)
from bunnyland_aquasim.diving import DiveHandler

EPOCH = 100


def _water_room(world, *, biome="reef"):
    room = spawn_entity(world, [RoomComponent(title="Reef", biome=biome)])
    room.add_component(SubmergedComponent(depth=1.0))
    return room


def _dry_room(world):
    return spawn_entity(world, [RoomComponent(title="Deck", biome="meadow")])


def _diver(world, room, *, skill=1.0, breath=None):
    components = [
        IdentityComponent(name="Vin", kind="character"),
        CharacterComponent(),
    ]
    if skill is not None:
        components.append(SwimSkillComponent(level=skill))
    if breath is not None:
        components.append(BreathComponent(meter=Meter(value=breath)))
    character = spawn_entity(world, components)
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def _cmd(character_id, command_type, payload):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type=command_type,
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload,
    )


def _ctx(actor):
    return HandlerContext(world=actor.world, epoch=EPOCH)


# -- deterministic loot -----------------------------------------------------------------


def test_deterministic_loot_is_stable():
    table = ("a pearl", "a coin", "a cutlass")
    first = deterministic_loot("cache_1", EPOCH, table)
    second = deterministic_loot("cache_1", EPOCH, table)
    assert first == second
    assert first in table


def test_deterministic_loot_ignores_table_order():
    a = deterministic_loot("cache_1", EPOCH, ("a pearl", "a coin", "a cutlass"))
    b = deterministic_loot("cache_1", EPOCH, ("a cutlass", "a pearl", "a coin"))
    assert a == b


# -- dive: happy path -------------------------------------------------------------------


def test_dive_recovers_treasure_into_inventory():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room)
    cache = spawn_treasure_cache(actor.world, room_id=room.id, table=("a barnacled coin",))

    result = DiveHandler().execute(_ctx(actor), _cmd(diver.id, "dive", {}))

    assert result.ok
    recovered = [event for event in result.events if isinstance(event, TreasureRecoveredEvent)]
    assert recovered and recovered[0].loot_name == "a barnacled coin"
    assert cache.get_component(TreasureCacheComponent).looted
    loot_names = [
        actor.world.get_entity(item_id).get_component(IdentityComponent).name
        for item_id in contents(diver)
    ]
    assert "a barnacled coin" in loot_names


def test_dive_targets_a_named_cache():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room)
    spawn_treasure_cache(actor.world, room_id=room.id, table=("a coin",))
    chosen = spawn_treasure_cache(actor.world, room_id=room.id, table=("a pearl",))

    result = DiveHandler().execute(
        _ctx(actor), _cmd(diver.id, "dive", {"cache_id": str(chosen.id)})
    )

    assert result.ok
    assert chosen.get_component(TreasureCacheComponent).looted


def test_dive_trains_swim_skill():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room, skill=0.0)
    spawn_treasure_cache(actor.world, room_id=room.id)

    DiveHandler().execute(_ctx(actor), _cmd(diver.id, "dive", {}))

    assert diver.get_component(SwimSkillComponent).experience > 0.0


# -- dive: rejections -------------------------------------------------------------------


def test_dive_rejects_invalid_character():
    actor = WorldActor()
    result = DiveHandler().execute(_ctx(actor), _cmd("???", "dive", {}))
    assert not result.ok
    assert result.reason == "invalid character id"


def test_dive_rejects_on_dry_land():
    actor = WorldActor()
    room = _dry_room(actor.world)
    diver = _diver(actor.world, room)
    result = DiveHandler().execute(_ctx(actor), _cmd(diver.id, "dive", {}))
    assert not result.ok
    assert result.reason == "you are not in the water"


def test_dive_rejects_non_swimmer():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room, skill=None)
    spawn_treasure_cache(actor.world, room_id=room.id)
    result = DiveHandler().execute(_ctx(actor), _cmd(diver.id, "dive", {}))
    assert not result.ok
    assert result.reason == "you cannot swim"


def test_dive_rejects_airless_diver():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room, breath=95.0)
    spawn_treasure_cache(actor.world, room_id=room.id)
    result = DiveHandler().execute(_ctx(actor), _cmd(diver.id, "dive", {}))
    assert not result.ok
    assert result.reason == "you have no breath left to dive"


def test_dive_rejects_when_nothing_to_find():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room)
    result = DiveHandler().execute(_ctx(actor), _cmd(diver.id, "dive", {}))
    assert not result.ok
    assert result.reason == "there is nothing to dive for here"


def test_dive_rejects_looted_cache():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room)
    cache = spawn_treasure_cache(actor.world, room_id=room.id)
    from dataclasses import replace

    from bunnyland.core.ecs import replace_component

    replace_component(cache, replace(cache.get_component(TreasureCacheComponent), looted=True))
    result = DiveHandler().execute(_ctx(actor), _cmd(diver.id, "dive", {"cache_id": str(cache.id)}))
    assert not result.ok
    assert result.reason == "that cache has already been looted"


def test_dive_rejects_cache_in_another_room():
    actor = WorldActor()
    room = _water_room(actor.world)
    other = _water_room(actor.world)
    diver = _diver(actor.world, room)
    elsewhere = spawn_treasure_cache(actor.world, room_id=other.id)
    result = DiveHandler().execute(
        _ctx(actor), _cmd(diver.id, "dive", {"cache_id": str(elsewhere.id)})
    )
    assert not result.ok
    assert result.reason == "that cache is not here"


def test_dive_rejects_non_cache_target():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room)
    rock = spawn_entity(actor.world, [IdentityComponent(name="rock", kind="item")])
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), rock.id)
    result = DiveHandler().execute(_ctx(actor), _cmd(diver.id, "dive", {"cache_id": str(rock.id)}))
    assert not result.ok
    assert result.reason == "that is not a treasure cache"


def test_dive_rejects_missing_cache():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room)
    result = DiveHandler().execute(_ctx(actor), _cmd(diver.id, "dive", {"cache_id": "entity_9999"}))
    assert not result.ok
    assert result.reason == "cache does not exist"


# -- surface ----------------------------------------------------------------------------


def test_surface_moves_diver_to_dry_room_and_refills():
    actor = WorldActor()
    deep = _water_room(actor.world)
    shore = _dry_room(actor.world)
    deep.add_relationship(ExitTo(direction="up"), shore.id)
    diver = _diver(actor.world, deep, breath=80.0)

    result = SurfaceHandler().execute(_ctx(actor), _cmd(diver.id, "surface", {}))

    assert result.ok
    assert isinstance(result.events[0], SurfacedEvent)
    assert str(shore.id) == result.events[0].to_room_id
    assert diver.id in [target for _edge, target in shore.get_relationships(Contains)]
    assert diver.get_component(BreathComponent).meter.value == 0.0


def test_surface_rejects_on_dry_land():
    actor = WorldActor()
    room = _dry_room(actor.world)
    diver = _diver(actor.world, room)
    result = SurfaceHandler().execute(_ctx(actor), _cmd(diver.id, "surface", {}))
    assert not result.ok
    assert result.reason == "you are not in the water"


def test_surface_rejects_without_a_way_up():
    actor = WorldActor()
    deep = _water_room(actor.world)
    deeper = _water_room(actor.world)
    deep.add_relationship(ExitTo(direction="down"), deeper.id)
    diver = _diver(actor.world, deep)
    result = SurfaceHandler().execute(_ctx(actor), _cmd(diver.id, "surface", {}))
    assert not result.ok
    assert result.reason == "there is no way up from here"


def test_surface_rejects_invalid_character():
    actor = WorldActor()
    result = SurfaceHandler().execute(_ctx(actor), _cmd("???", "surface", {}))
    assert not result.ok
    assert result.reason == "invalid character id"
