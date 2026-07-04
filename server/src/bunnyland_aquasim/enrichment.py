"""World-generation enrichment: flood aquatic rooms and sink treasure caches.

Generated rooms carry a ``biome`` and semantic ``tags``/``description``; generated objects
carry the same text. This hook tags a generated room underwater (a
:class:`~bunnyland_aquasim.components.SubmergedComponent`) when its biome is aquatic or its
text reads wet, and turns a generated object into a
:class:`~bunnyland_aquasim.components.TreasureCacheComponent` when its text reads like sunk
treasure — all without the core generator knowing this plugin exists.
"""

from __future__ import annotations

from bunnyland.core.ecs import parse_entity_id, replace_component
from bunnyland.core.events import (
    GeneratedEntityEvent,
    ObjectGeneratedEvent,
    RoomGeneratedEvent,
)
from bunnyland.core.world_actor import WorldActor

from .components import SubmergedComponent, TreasureCacheComponent
from .submersion import AQUATIC_BIOMES

#: Words that flood a generated room even if its biome is not explicitly aquatic.
WATER_TERMS = (
    "water",
    "underwater",
    "submerged",
    "flooded",
    "sunken",
    "sunk",
    "ocean",
    "sea",
    "lake",
    "river",
    "reef",
    "lagoon",
    "abyss",
    "deep",
    "tide",
    "current",
)

#: Words that mark a generated object as sunk treasure.
TREASURE_TERMS = (
    "treasure",
    "chest",
    "hoard",
    "trove",
    "loot",
    "wreck",
    "shipwreck",
    "cache",
    "coffer",
    "bounty",
)

#: Loot pool given to a sunk cache the generator did not itself specify.
DEFAULT_TABLE = (
    "a barnacled coin",
    "a pearl the size of an eye",
    "a rusted cutlass",
    "a coral-crusted locket",
)


def _text(event: GeneratedEntityEvent) -> str:
    generation = event.generation
    return " ".join(
        (
            event.entity_kind,
            generation.description,
            *generation.tags,
            *generation.wants,
            *generation.needs,
        )
    ).casefold()


def _mentions(event: GeneratedEntityEvent, terms: tuple[str, ...]) -> bool:
    text = _text(event)
    return any(term in text for term in terms)


class AquaWorldgenHook:
    """Flood aquatic generated rooms and sink treasure caches into generated objects."""

    def subscribe(self, actor: WorldActor) -> None:
        self._actor = actor
        actor.bus.subscribe(RoomGeneratedEvent, self._on_room)
        actor.bus.subscribe(ObjectGeneratedEvent, self._on_object)

    def _entity(self, entity_id: str):
        parsed = parse_entity_id(entity_id)
        if parsed is None or not self._actor.world.has_entity(parsed):
            return None
        return self._actor.world.get_entity(parsed)

    def _on_room(self, event: RoomGeneratedEvent) -> None:
        entity = self._entity(event.entity_id)
        if entity is None or entity.has_component(SubmergedComponent):
            return
        if event.biome in AQUATIC_BIOMES or _mentions(event, WATER_TERMS):
            replace_component(entity, SubmergedComponent())

    def _on_object(self, event: ObjectGeneratedEvent) -> None:
        entity = self._entity(event.entity_id)
        if entity is None or entity.has_component(TreasureCacheComponent):
            return
        if _mentions(event, TREASURE_TERMS):
            replace_component(entity, TreasureCacheComponent(table=DEFAULT_TABLE))


__all__ = ["DEFAULT_TABLE", "TREASURE_TERMS", "WATER_TERMS", "AquaWorldgenHook"]
