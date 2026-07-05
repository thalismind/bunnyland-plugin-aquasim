"""Diving-gear tiers (v2 support mechanic).

v1 shipped a single :class:`~bunnyland_aquasim.components.RebreatherComponent`. v2 layers a
tiered progression on top: a :class:`DiveGearComponent` names a gear tier and carries two
numbers other mechanics read —

- ``efficiency`` (0..1) feeds the existing v1 breath/hazard relief. Gear items spawned by
  :func:`~bunnyland_aquasim.prefabs.spawn_dive_gear` also carry a matching
  ``RebreatherComponent`` so the v1 drain logic benefits from a tier without any change to
  it; and
- ``pressure_rating`` gates how deep a structure a diver can safely reach — a snorkel is
  fine for a shallow reef, but an abyssal wreck needs an atmospheric suit.

The tier table is deterministic and closed; no randomness, no brand names.
"""

from __future__ import annotations

from bunnyland.core import contents
from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World

#: Ordered gear tiers, shallow to deep: ``tier -> (efficiency, pressure_rating, label)``.
GEAR_TIERS: dict[str, tuple[float, float, str]] = {
    "snorkel": (0.2, 0.5, "a snorkel"),
    "scuba": (0.55, 1.5, "a scuba rig"),
    "rebreather": (0.75, 2.5, "a rebreather"),
    "atmospheric_suit": (0.95, 5.0, "an atmospheric diving suit"),
}


@dataclass(frozen=True)
class DiveGearComponent(Component):
    """Held diving gear of a named ``tier``; deeper tiers slow breath and resist pressure."""

    tier: str = "snorkel"
    efficiency: float = 0.2
    pressure_rating: float = 0.5

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        if not ctx.is_first_person:
            return ()
        label = GEAR_TIERS.get(self.tier, (0.0, 0.0, f"a {self.tier}"))[2]
        return (f"You are geared for the deep in {label}.",)


def gear_stats(tier: str) -> tuple[float, float]:
    """Return ``(efficiency, pressure_rating)`` for a tier (falls back to the snorkel)."""
    efficiency, pressure, _label = GEAR_TIERS.get(tier, GEAR_TIERS["snorkel"])
    return efficiency, pressure


def held_dive_gear(world: World, character: Entity) -> Entity | None:
    """Return the best (highest ``pressure_rating``) dive gear the character carries."""
    best: Entity | None = None
    best_pressure = -1.0
    for item_id in contents(character):
        if not world.has_entity(item_id):
            continue
        item = world.get_entity(item_id)
        if not item.has_component(DiveGearComponent):
            continue
        pressure = item.get_component(DiveGearComponent).pressure_rating
        if pressure > best_pressure:
            best = item
            best_pressure = pressure
    return best


def gear_pressure_rating(world: World, character: Entity) -> float:
    """Return the pressure rating of the character's best gear (``0.0`` if unequipped)."""
    gear = held_dive_gear(world, character)
    if gear is None:
        return 0.0
    return gear.get_component(DiveGearComponent).pressure_rating


def gear_fragments(world: World, character: Entity) -> list[str]:
    """First-person line naming the diving gear a character is wearing."""
    if character is None:
        return []
    gear = held_dive_gear(world, character)
    if gear is None:
        return []
    ctx = ComponentPromptContext.for_entity(world, character)
    return list(gear.get_component(DiveGearComponent).prompt_fragments(ctx))


__all__ = [
    "GEAR_TIERS",
    "DiveGearComponent",
    "gear_fragments",
    "gear_pressure_rating",
    "gear_stats",
    "held_dive_gear",
]
