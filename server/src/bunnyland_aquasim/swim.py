"""Swim skill (mechanic 5).

A :class:`SwimSkillComponent` improves with use and makes the underwater safer:

- higher skill reduces breath drain (:func:`swim_drain_multiplier`), and
- past a threshold the swimmer resists being swept by currents and shrugs off some hazard
  damage (:func:`swim_resists_current`, :func:`swim_hazard_multiplier`).

Improvement is deterministic: :func:`improve_swim` adds a fixed amount of experience per
use and promotes a level every :data:`XP_PER_LEVEL` — no randomness, no wall-clock time.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core.ecs import replace_component
from bunnyland.core.events import DomainEvent, EventVisibility, event_base
from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World

#: Experience needed to gain one swim level.
XP_PER_LEVEL = 3.0
#: Experience granted for a single use (a dive, a surface, a resisted current).
XP_PER_USE = 1.0
#: Skill at or above this level resists currents and blunts hazards.
MASTERY_LEVEL = 3.0
#: Largest fraction of breath drain that skill can remove.
MAX_DRAIN_RELIEF = 0.5
#: Drain relief contributed per swim level.
DRAIN_RELIEF_PER_LEVEL = 0.1


@dataclass(frozen=True)
class SwimSkillComponent(Component):
    """A character's swimming proficiency. ``level`` rises as ``experience`` accrues."""

    level: float = 0.0
    experience: float = 0.0

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        if not ctx.is_first_person or self.level < MASTERY_LEVEL:
            return ()
        return ("You move through the water like you were born to it.",)


class SwimSkillImprovedEvent(DomainEvent):
    """A character's swim skill advanced a level."""

    level: float


def swim_drain_multiplier(skill: SwimSkillComponent | None) -> float:
    """Fraction of breath drain that still applies after skill relief (``1.0`` = none)."""
    if skill is None:
        return 1.0
    relief = min(MAX_DRAIN_RELIEF, skill.level * DRAIN_RELIEF_PER_LEVEL)
    return 1.0 - relief


def swim_resists_current(skill: SwimSkillComponent | None) -> bool:
    """True when a swimmer is strong enough to hold their ground against a current."""
    return skill is not None and skill.level >= MASTERY_LEVEL


def swim_hazard_multiplier(skill: SwimSkillComponent | None) -> float:
    """Fraction of hazard damage a swimmer still takes (mastery halves it)."""
    return 0.5 if swim_resists_current(skill) else 1.0


def improve_swim(character: Entity, *, epoch: int) -> DomainEvent | None:
    """Grant experience for a use; emit an event only when a level is gained."""
    if not character.has_component(SwimSkillComponent):
        return None
    skill = character.get_component(SwimSkillComponent)
    experience = skill.experience + XP_PER_USE
    levels_gained = int(experience // XP_PER_LEVEL)
    new_level = skill.level + levels_gained
    new_experience = experience - levels_gained * XP_PER_LEVEL
    replace_component(character, replace(skill, level=new_level, experience=new_experience))
    if levels_gained <= 0:
        return None
    return SwimSkillImprovedEvent(
        **event_base(
            epoch,
            default_visibility=EventVisibility.PRIVATE,
            actor_id=str(character.id),
            level=new_level,
        )
    )


def swim_fragments(world: World, character: Entity) -> list[str]:
    """First-person mastery line for a strong swimmer."""
    if character is None or not character.has_component(SwimSkillComponent):
        return []
    ctx = ComponentPromptContext.for_entity(world, character)
    return list(character.get_component(SwimSkillComponent).prompt_fragments(ctx))


__all__ = [
    "DRAIN_RELIEF_PER_LEVEL",
    "MASTERY_LEVEL",
    "MAX_DRAIN_RELIEF",
    "XP_PER_LEVEL",
    "XP_PER_USE",
    "SwimSkillComponent",
    "SwimSkillImprovedEvent",
    "improve_swim",
    "swim_drain_multiplier",
    "swim_fragments",
    "swim_hazard_multiplier",
    "swim_resists_current",
]
