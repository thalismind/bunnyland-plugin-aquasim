"""Passive world/item/cache state for the aquatic pack.

These are the immutable data components other modules read and swap with
``replace_component(entity, replace(component, ...))``:

- :class:`SubmergedComponent` tags a **room** as deep water — the water-room mechanic in
  :mod:`bunnyland_aquasim.submersion` treats such a room (or any aquatic ``RoomComponent``
  biome) as underwater, gating movement and driving the breath timer.
- :class:`RebreatherComponent` is a held **item** (diving gear) that slows breath drain.
- :class:`TreasureCacheComponent` is a sunk **cache** the ``dive`` verb recovers loot from.

Behavioural, meter-bearing components live with their mechanic (``BreathComponent`` in
:mod:`bunnyland_aquasim.breath`, ``SwimSkillComponent`` in :mod:`bunnyland_aquasim.swim`,
``CurrentComponent``/``HazardComponent`` in :mod:`bunnyland_aquasim.currents`).
"""

from __future__ import annotations

from bunnyland.core import contents
from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World


@dataclass(frozen=True)
class SubmergedComponent(Component):
    """Marks a room as deep water. ``depth`` scales breath drain and loot richness."""

    depth: float = 1.0

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        return ("You are underwater; the light dims and the pressure builds.",)


@dataclass(frozen=True)
class RebreatherComponent(Component):
    """Diving gear. ``efficiency`` (0..1) is the fraction of breath drain it removes."""

    efficiency: float = 0.75

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        if not ctx.is_first_person:
            return ()
        return ("You carry a rebreather; it stretches every breath underwater.",)


@dataclass(frozen=True)
class TreasureCacheComponent(Component):
    """A sunk cache the ``dive`` verb recovers a single item from.

    ``table`` is the pool of possible loot names; the recovered item is chosen
    deterministically from a hash of the cache id and the world epoch (no randomness).
    """

    biome: str = "reef"
    depth: float = 1.0
    table: tuple[str, ...] = ("a barnacled coin",)
    looted: bool = False


def held_rebreather(world: World, character: Entity) -> Entity | None:
    """Return a rebreather item the character is carrying, or ``None``."""
    for item_id in contents(character):
        if not world.has_entity(item_id):
            continue
        item = world.get_entity(item_id)
        if item.has_component(RebreatherComponent):
            return item
    return None


__all__ = [
    "RebreatherComponent",
    "SubmergedComponent",
    "TreasureCacheComponent",
    "held_rebreather",
]
