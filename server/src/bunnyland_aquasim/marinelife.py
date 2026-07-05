"""Marine life and the underwater food chain (v2 headline mechanic, part 2).

A :class:`MarineLifeComponent` sits on a creature entity and gives it a ``species`` and a
``role`` in the food chain — ``forage`` (harmless), ``prey`` (harvestable, hunted), or
``predator``/``apex`` (a threat). Predators wire to their quarry with the typed
:class:`~bunnyland_aquasim.edges.PreysOn` edge.

:class:`MarineThreatConsequence` reuses the core
:class:`~bunnyland.core.HealthComponent` to bite divers who share a water room with a
predator each tick — the "marine-life threat" the roadmap asks health to cover. Swim mastery
blunts the bite (reusing the v1 swim relief). The food chain is load-bearing, not flavour: a
predator busy feeding on prey present in its room ignores the divers entirely. Deterministic;
suspended and dead entities never participate (spec 8.1).
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import (
    DeadComponent,
    HealthComponent,
    SuspendedComponent,
    contents,
)
from bunnyland.core.ecs import replace_component
from bunnyland.core.events import DomainEvent, EventVisibility, event_base
from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World

from .edges import prey_present
from .spatial import active_characters_in_room, room_of
from .submersion import is_water_room
from .swim import SwimSkillComponent, swim_hazard_multiplier

#: Roles whose creatures menace divers.
THREAT_ROLES: frozenset[str] = frozenset({"predator", "apex"})

#: Short scene lines per role, shown to anyone sharing the room.
_ROLE_SCENE = {
    "forage": "drifts harmlessly by",
    "prey": "darts through the water",
    "predator": "circles, hunting",
    "apex": "looms, vast and hungry",
}


@dataclass(frozen=True)
class MarineLifeComponent(Component):
    """A creature's place in the food chain. Predators with ``threat`` bite unlucky divers."""

    species: str = "fish"
    role: str = "prey"
    threat: float = 0.0

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        scene = _ROLE_SCENE.get(self.role, "moves through the water")
        return (f"A {self.species} {scene}.",)


class MarineAttackEvent(DomainEvent):
    """A predatory marine creature bit a diver."""

    damage: float
    species: str


def is_threat(marine: MarineLifeComponent) -> bool:
    """True when a creature's role and threat make it dangerous to divers."""
    return marine.role in THREAT_ROLES and marine.threat > 0.0


class MarineThreatConsequence:
    """Predatory marine life bites divers sharing its water room, unless it is feeding."""

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        for creature in list(world.query().with_all([MarineLifeComponent]).execute_entities()):
            marine = creature.get_component(MarineLifeComponent)
            if not is_threat(marine):
                continue
            if creature.has_component(SuspendedComponent) or creature.has_component(DeadComponent):
                continue
            room = room_of(world, creature.id)
            if not is_water_room(room):
                continue
            if prey_present(world, creature, room):
                # Distracted feeding on its natural prey — the food chain in action.
                continue
            events.extend(self._hunt(world, epoch, creature, room, marine))
        return events

    def _hunt(self, world, epoch, creature, room, marine) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        for character in active_characters_in_room(world, room):
            if character.id == creature.id or character.has_component(MarineLifeComponent):
                continue
            event = self._bite(world, epoch, character, marine)
            if event is not None:
                events.append(event)
        return events

    def _bite(self, world, epoch, character, marine) -> DomainEvent | None:
        if not character.has_component(HealthComponent):
            return None
        skill = (
            character.get_component(SwimSkillComponent)
            if character.has_component(SwimSkillComponent)
            else None
        )
        damage = marine.threat * swim_hazard_multiplier(skill)
        if damage <= 0.0:
            return None
        health = character.get_component(HealthComponent)
        if health.current <= 0.0:
            return None
        replace_component(character, replace(health, current=max(0.0, health.current - damage)))
        return MarineAttackEvent(
            **event_base(
                epoch,
                default_visibility=EventVisibility.PRIVATE,
                actor_id=str(character.id),
                damage=damage,
                species=marine.species,
            )
        )


def marine_life_in_room(world: World, room: Entity | None) -> list[Entity]:
    """Return the marine creatures resting directly in ``room``, id-sorted."""
    if room is None:
        return []
    creatures: list[Entity] = []
    for member_id in contents(room):
        if not world.has_entity(member_id):
            continue
        member = world.get_entity(member_id)
        if member.has_component(MarineLifeComponent):
            creatures.append(member)
    creatures.sort(key=lambda entity: str(entity.id))
    return creatures


def marinelife_fragments(world: World, character: Entity) -> list[str]:
    """Describe the marine creatures sharing the character's water room."""
    if character is None:
        return []
    room = room_of(world, character.id)
    if room is None:
        return []
    lines: list[str] = []
    ctx = ComponentPromptContext.for_entity(world, character)
    for creature in marine_life_in_room(world, room):
        if creature.id == character.id:
            continue
        lines.extend(creature.get_component(MarineLifeComponent).prompt_fragments(ctx))
    return sorted(lines)


__all__ = [
    "THREAT_ROLES",
    "MarineAttackEvent",
    "MarineLifeComponent",
    "MarineThreatConsequence",
    "is_threat",
    "marine_life_in_room",
    "marinelife_fragments",
]
