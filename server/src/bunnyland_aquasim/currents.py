"""Currents and hazards (mechanic 4).

Two room components add danger to the water:

- :class:`CurrentComponent` drifts every non-mastery swimmer toward an
  :class:`~bunnyland.core.ExitTo` each tick — following the current's ``direction`` when a
  matching exit exists, otherwise the first exit. Strong swimmers
  (:func:`~bunnyland_aquasim.swim.swim_resists_current`) hold their ground.
- :class:`HazardComponent` bites any character in the room each tick, damaging
  :class:`~bunnyland.core.HealthComponent`. When ``requires_gear`` is set, a held rebreather
  wards it off entirely; otherwise swim skill only blunts it.

Both consequences are per-tick, deterministic, and exclude suspended/dead characters.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    DeadComponent,
    ExitTo,
    HealthComponent,
    SuspendedComponent,
    contents,
)
from bunnyland.core.ecs import remove_from_container, replace_component
from bunnyland.core.events import DomainEvent, EventVisibility, event_base
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World

from .components import held_rebreather
from .swim import SwimSkillComponent, swim_hazard_multiplier, swim_resists_current


@dataclass(frozen=True)
class CurrentComponent(Component):
    """A room current that sweeps swimmers toward an exit. ``direction`` picks the exit."""

    direction: str = ""
    strength: float = 1.0


@dataclass(frozen=True)
class HazardComponent(Component):
    """A submerged hazard that damages characters. ``requires_gear`` lets gear negate it."""

    damage: float = 6.0
    requires_gear: bool = True


def _active_characters_in_room(world: World, room: Entity) -> list[Entity]:
    characters: list[Entity] = []
    for entity_id in contents(room):
        if not world.has_entity(entity_id):
            continue
        entity = world.get_entity(entity_id)
        if not entity.has_component(CharacterComponent):
            continue
        if entity.has_component(SuspendedComponent) or entity.has_component(DeadComponent):
            continue
        characters.append(entity)
    characters.sort(key=lambda entity: str(entity.id))
    return characters


def _current_exit(room: Entity, direction: str) -> object | None:
    exits = room.get_relationships(ExitTo)
    if not exits:
        return None
    if direction:
        for edge, target_id in exits:
            if getattr(edge, "direction", "") == direction:
                return target_id
    return exits[0][1]


class DriftedEvent(DomainEvent):
    """A current swept a character from one room into another."""

    from_room_id: str
    to_room_id: str


class HazardStruckEvent(DomainEvent):
    """A submerged hazard damaged a character."""

    damage: float


class CurrentConsequence:
    """Drift every non-mastery swimmer toward a room current's exit each tick."""

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        for room in list(world.query().with_all([CurrentComponent]).execute_entities()):
            current = room.get_component(CurrentComponent)
            target_id = _current_exit(room, current.direction)
            if target_id is None or not world.has_entity(target_id):
                continue
            target = world.get_entity(target_id)
            for character in _active_characters_in_room(world, room):
                if character.has_component(SwimSkillComponent) and swim_resists_current(
                    character.get_component(SwimSkillComponent)
                ):
                    continue
                remove_from_container(world, character.id)
                target.add_relationship(
                    Contains(mode=ContainmentMode.ROOM_CONTENT), character.id
                )
                events.append(
                    DriftedEvent(
                        **event_base(
                            epoch,
                            default_visibility=EventVisibility.ROOM,
                            actor_id=str(character.id),
                            room_id=str(target.id),
                            from_room_id=str(room.id),
                            to_room_id=str(target.id),
                        )
                    )
                )
        return events


class HazardConsequence:
    """Damage characters caught in a hazardous room, unless warded by gear each tick."""

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        for room in list(world.query().with_all([HazardComponent]).execute_entities()):
            hazard = room.get_component(HazardComponent)
            for character in _active_characters_in_room(world, room):
                event = self._strike(world, epoch, character, hazard)
                if event is not None:
                    events.append(event)
        return events

    def _strike(self, world, epoch, character, hazard) -> DomainEvent | None:
        if hazard.requires_gear and held_rebreather(world, character) is not None:
            return None
        if not character.has_component(HealthComponent):
            return None
        skill = (
            character.get_component(SwimSkillComponent)
            if character.has_component(SwimSkillComponent)
            else None
        )
        damage = hazard.damage * swim_hazard_multiplier(skill)
        if damage <= 0.0:
            return None
        health = character.get_component(HealthComponent)
        if health.current <= 0.0:
            return None
        new_current = max(0.0, health.current - damage)
        replace_component(character, replace(health, current=new_current))
        return HazardStruckEvent(
            **event_base(
                epoch,
                default_visibility=EventVisibility.PRIVATE,
                actor_id=str(character.id),
                damage=damage,
            )
        )


__all__ = [
    "CurrentComponent",
    "CurrentConsequence",
    "DriftedEvent",
    "HazardComponent",
    "HazardConsequence",
    "HazardStruckEvent",
]
