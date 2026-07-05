"""Spawn factories for aquatic items and caches.

The loader does not consume ``ContentContribution.prefabs``, so these ``spawn_entity``
helpers create gear and caches from tests, admin tooling, or a worldgen hook. Pass
``room_id`` to drop the entity into a room, or leave it out to spawn it uncontained (e.g.
straight into an inventory).
"""

from __future__ import annotations

from bunnyland.core import (
    ContainmentMode,
    Contains,
    HoldableComponent,
    IdentityComponent,
    PortableComponent,
    spawn_entity,
)
from relics import Entity, World

from .components import RebreatherComponent, TreasureCacheComponent
from .gear import GEAR_TIERS, DiveGearComponent, gear_stats


def _link_into_room(world: World, item: Entity, room_id) -> None:
    if room_id is None or not world.has_entity(room_id):
        return
    world.get_entity(room_id).add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), item.id)


def spawn_rebreather(world: World, *, room_id=None, efficiency: float = 0.75) -> Entity:
    """Spawn a holdable rebreather item, optionally placed in ``room_id``."""
    item = spawn_entity(
        world,
        [
            IdentityComponent(name="rebreather", kind="item", tags=("aquasim",)),
            PortableComponent(),
            HoldableComponent(slot="hand"),
            RebreatherComponent(efficiency=efficiency),
        ],
    )
    _link_into_room(world, item, room_id)
    return item


def spawn_treasure_cache(
    world: World,
    *,
    room_id=None,
    biome: str = "reef",
    depth: float = 1.0,
    table: tuple[str, ...] = ("a barnacled coin",),
) -> Entity:
    """Spawn a sunk treasure cache, optionally placed in ``room_id``."""
    cache = spawn_entity(
        world,
        [
            IdentityComponent(name="treasure cache", kind="cache", tags=("aquasim",)),
            TreasureCacheComponent(biome=biome, depth=depth, table=table),
        ],
    )
    _link_into_room(world, cache, room_id)
    return cache


def spawn_dive_gear(world: World, *, tier: str = "scuba", room_id=None) -> Entity:
    """Spawn a tier of diving gear, optionally placed in ``room_id``.

    The item carries both a :class:`~bunnyland_aquasim.gear.DiveGearComponent` (for the v2
    depth-gating) and a matching :class:`~bunnyland_aquasim.components.RebreatherComponent`,
    so the untouched v1 breath-drain relief benefits from the tier's ``efficiency``.
    """
    efficiency, pressure = gear_stats(tier)
    label = GEAR_TIERS.get(tier, (0.0, 0.0, f"a {tier}"))[2]
    item = spawn_entity(
        world,
        [
            IdentityComponent(name=label, kind="item", tags=("aquasim", "gear", tier)),
            PortableComponent(),
            HoldableComponent(slot="back"),
            DiveGearComponent(tier=tier, efficiency=efficiency, pressure_rating=pressure),
            RebreatherComponent(efficiency=efficiency),
        ],
    )
    _link_into_room(world, item, room_id)
    return item


__all__ = ["spawn_dive_gear", "spawn_rebreather", "spawn_treasure_cache"]
