"""Typed relationship edges for the aquatic v2 expansion.

Repeatable, multi-instance relationships are modelled as :class:`relics.Edge` subclasses —
never as lists on a component — so each relationship gets its own index and queries stay
clear (project convention, spec 11.15 style):

- :class:`PreysOn` links a predator marine creature to the prey it hunts (the food chain).
  A predator busy feeding on prey present in its room ignores divers, so the edge carries
  real behaviour, not just narration.
- :class:`DiscoveredBy` credits the first character to chart a dive site (first-find credit
  a reputation/cartography reader can honour).
"""

from __future__ import annotations

from pydantic.dataclasses import dataclass
from relics import Edge, Entity, EntityId, World

from .spatial import room_of


@dataclass(frozen=True)
class PreysOn(Edge):
    """predator -> prey. The predator hunts this creature; ``strength`` scales the drive."""

    strength: float = 1.0


@dataclass(frozen=True)
class DiscoveredBy(Edge):
    """dive site -> discoverer. The first character to chart the site earns the credit."""

    epoch: int = 0


def prey_ids(predator: Entity) -> list[EntityId]:
    """Return the ids of the prey a predator hunts, in a stable order."""
    return sorted(
        (target_id for _edge, target_id in predator.get_relationships(PreysOn)),
        key=str,
    )


def discoverer_id_of(site: Entity) -> EntityId | None:
    """Return the id of the character who first charted ``site``, or ``None``."""
    for _edge, discoverer_id in site.get_relationships(DiscoveredBy):
        return discoverer_id
    return None


def credit_discovery(site: Entity, discoverer_id: EntityId, *, epoch: int = 0) -> bool:
    """Credit ``discoverer_id`` with the site's discovery; keep the first finder only."""
    if discoverer_id_of(site) is not None:
        return False
    site.add_relationship(DiscoveredBy(epoch=epoch), discoverer_id)
    return True


def prey_present(world: World, predator: Entity, room: Entity) -> bool:
    """True when a live prey the predator hunts shares ``room`` with it."""
    for prey_id in prey_ids(predator):
        if not world.has_entity(prey_id):
            continue
        prey_room = room_of(world, prey_id)
        if prey_room is not None and prey_room.id == room.id:
            return True
    return False


__all__ = [
    "DiscoveredBy",
    "PreysOn",
    "credit_discovery",
    "discoverer_id_of",
    "prey_ids",
    "prey_present",
]
