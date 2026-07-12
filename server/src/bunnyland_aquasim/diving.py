"""Diving for treasure, and surfacing for air (mechanic 3).

Two verbs:

- ``dive`` recovers a single item from a :class:`~bunnyland_aquasim.components.
  TreasureCacheComponent` sunk in the character's water room. The item is chosen
  **deterministically** from the cache's loot table by hashing the cache id and the world
  epoch, so a given cache yields the same thing on a given tick — no runtime randomness.
  Diving trains swim skill. It rejects if you are not in the water, cannot swim, have no
  breath left, or there is nothing to dive for.
- ``surface`` swims up an :class:`~bunnyland.core.ExitTo` link to the first dry room,
  refilling breath. It rejects if you are not in the water or there is no way up.

Validation order matches the project convention: invalid id -> missing entity -> wrong
state -> wrong kind -> apply.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace

from bunnyland.core import (
    ContainmentMode,
    Contains,
    ExitTo,
    HoldableComponent,
    IdentityComponent,
    PortableComponent,
    spawn_entity,
)
from bunnyland.core.actions import ActionArgument, ActionDefinition, ActionEffort, effort_cost
from bunnyland.core.commands import Lane, SubmittedCommand
from bunnyland.core.ecs import contents, remove_from_container, replace_component
from bunnyland.core.events import DomainEvent, EventVisibility
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    ok,
    rejected,
    require_character,
    require_entity,
)
from relics import Entity, World

from .breath import BreathComponent, breath_band
from .components import TreasureCacheComponent
from .spatial import room_of
from .submersion import is_water_room
from .swim import SwimSkillComponent, improve_swim


class TreasureRecoveredEvent(DomainEvent):
    """A diver pulled an item from a sunk cache."""

    cache_id: str
    loot_id: str
    loot_name: str


class SurfacedEvent(DomainEvent):
    """A character swam up out of the water."""

    from_room_id: str
    to_room_id: str


def deterministic_loot(cache_id: str, epoch: int, table: tuple[str, ...]) -> str:
    """Pick one loot name from ``table`` deterministically from the cache id and epoch."""
    items = sorted(table)
    digest = hashlib.sha256(f"{cache_id}:{epoch}".encode()).hexdigest()
    return items[int(digest, 16) % len(items)]


def _first_cache_in_room(world: World, room: Entity) -> Entity | None:
    caches: list[Entity] = []
    for entity_id in contents(room):
        if not world.has_entity(entity_id):
            continue
        entity = world.get_entity(entity_id)
        if (
            entity.has_component(TreasureCacheComponent)
            and not entity.get_component(TreasureCacheComponent).looted
        ):
            caches.append(entity)
    caches.sort(key=lambda entity: str(entity.id))
    return caches[0] if caches else None


def _surface_exit(world: World, room: Entity) -> Entity | None:
    """First room reachable via an ``ExitTo`` that is dry land."""
    for _edge, target_id in room.get_relationships(ExitTo):
        if not world.has_entity(target_id):
            continue
        target = world.get_entity(target_id)
        if not is_water_room(target):
            return target
    return None


class DiveHandler:
    """Recover treasure from a sunk cache in the character's water room."""

    command_type = "dive"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        room = room_of(ctx.world, character_id)
        if not is_water_room(room):
            return rejected("you are not in the water")
        if not character.has_component(SwimSkillComponent):
            return rejected("you cannot swim")
        if (
            character.has_component(BreathComponent)
            and breath_band(character.get_component(BreathComponent)) == "crisis"
        ):
            return rejected("you have no breath left to dive")

        cache, rejection = self._resolve_cache(ctx, room, command)
        if rejection is not None:
            return rejection

        loot = self._recover(ctx, character, cache)
        events: list[DomainEvent] = [loot]
        skill_event = improve_swim(character, epoch=ctx.epoch)
        if skill_event is not None:
            events.append(skill_event)
        return ok(*events)

    def _resolve_cache(self, ctx: HandlerContext, room: Entity, command: SubmittedCommand):
        raw_cache = command.payload.get("cache_id")
        if raw_cache is not None:
            cache_id, cache, rejection = require_entity(
                ctx,
                raw_cache,
                invalid_reason="invalid cache id",
                missing_reason="cache does not exist",
            )
            if rejection is not None:
                return None, rejection
            cache_room = room_of(ctx.world, cache_id)
            if cache_room is None or cache_room.id != room.id:
                return None, rejected("that cache is not here")
            if not cache.has_component(TreasureCacheComponent):
                return None, rejected("that is not a treasure cache")
            if cache.get_component(TreasureCacheComponent).looted:
                return None, rejected("that cache has already been looted")
            return cache, None
        cache = _first_cache_in_room(ctx.world, room)
        if cache is None:
            return None, rejected("there is nothing to dive for here")
        return cache, None

    def _recover(self, ctx: HandlerContext, character: Entity, cache: Entity) -> DomainEvent:
        component = cache.get_component(TreasureCacheComponent)
        loot_name = deterministic_loot(str(cache.id), ctx.epoch, component.table)
        loot = spawn_entity(
            ctx.world,
            [
                IdentityComponent(name=loot_name, kind="item", tags=("aquasim", "treasure")),
                PortableComponent(),
                HoldableComponent(slot="hand"),
            ],
        )
        character.add_relationship(Contains(mode=ContainmentMode.INVENTORY), loot.id)
        replace_component(cache, replace(component, looted=True))
        room = room_of(ctx.world, character.id)
        return TreasureRecoveredEvent(
            **ctx.event_base(
                visibility=EventVisibility.ROOM,
                actor_id=str(character.id),
                room_id=str(room.id) if room is not None else None,
                target_ids=(str(cache.id),),
                cache_id=str(cache.id),
                loot_id=str(loot.id),
                loot_name=loot_name,
            )
        )


class SurfaceHandler:
    """Swim up out of the water to the first dry room, catching your breath."""

    command_type = "surface"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        room = room_of(ctx.world, character_id)
        if not is_water_room(room):
            return rejected("you are not in the water")
        surface = _surface_exit(ctx.world, room)
        if surface is None:
            return rejected("there is no way up from here")

        remove_from_container(ctx.world, character_id)
        surface.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character_id)
        if character.has_component(BreathComponent):
            breath = character.get_component(BreathComponent)
            replace_component(character, replace(breath, meter=replace(breath.meter, value=0.0)))
        events: list[DomainEvent] = [
            SurfacedEvent(
                **ctx.event_base(
                    visibility=EventVisibility.ROOM,
                    actor_id=str(character.id),
                    room_id=str(surface.id),
                    target_ids=(str(surface.id),),
                    from_room_id=str(room.id),
                    to_room_id=str(surface.id),
                )
            )
        ]
        skill_event = improve_swim(character, epoch=ctx.epoch)
        if skill_event is not None:
            events.append(skill_event)
        return ok(*events)


DIVE_DEF = ActionDefinition(
    command_type="dive",
    title="Dive",
    description="Dive for treasure in the water room you are in.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.ROUTINE),
    arguments={
        "cache_id": ActionArgument(
            title="Cache",
            description="The sunk cache to dive for; omit to take the first one here.",
            kind="entity",
        ),
    },
)

SURFACE_DEF = ActionDefinition(
    command_type="surface",
    title="Surface",
    description="Swim up out of the water to catch your breath.",
    lane=Lane.WORLD,
    cost=effort_cost(action=ActionEffort.ROUTINE),
    arguments={},
)

DIVE_ACTION_DEFINITIONS = (DIVE_DEF, SURFACE_DEF)
DIVE_ACTION_HANDLERS = (DiveHandler, SurfaceHandler)


__all__ = [
    "DIVE_ACTION_DEFINITIONS",
    "DIVE_ACTION_HANDLERS",
    "DIVE_DEF",
    "SURFACE_DEF",
    "DiveHandler",
    "SurfaceHandler",
    "SurfacedEvent",
    "TreasureRecoveredEvent",
    "deterministic_loot",
]
