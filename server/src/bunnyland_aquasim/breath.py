"""Breath meter and drowning (mechanic 2).

``BreathComponent`` reuses the shared :class:`~bunnyland.mechanics.meter.Meter` primitive,
exactly like the ``needs`` mechanics. Its ``value`` is *oxygen debt* — a rising need:

- underwater the debt **rises** each tick (the character's breath drains), scaled by room
  depth, slowed by a held rebreather and by swim skill;
- at the surface the debt **falls** (breath refills);
- once the debt maxes out (the ``crisis`` band) a still-submerged character starts drowning
  and loses :class:`~bunnyland.core.HealthComponent` each tick.

A per-tick :class:`BreathConsequence` drives all of this, excludes suspended/dead
characters (harmful world participation, spec 8.1), and emits band-crossing
:class:`BreathChangedEvent`s and :class:`DrowningEvent`s. It is fully deterministic.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import DeadComponent, HealthComponent, SuspendedComponent
from bunnyland.core.ecs import replace_component
from bunnyland.core.events import DomainEvent, EventVisibility, event_base
from bunnyland.mechanics.meter import Meter, band, changed
from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component, World

from .components import RebreatherComponent, held_rebreather
from .spatial import room_of
from .submersion import is_water_room, room_depth
from .swim import SwimSkillComponent, swim_drain_multiplier

# --------------------------------------------------------------------------------------
# Tuning
# --------------------------------------------------------------------------------------

#: Oxygen debt gained per tick per unit of room depth while submerged with no gear/skill.
DRAIN_PER_DEPTH = 12.0
#: Oxygen debt shed per tick at the surface.
REFILL_PER_TICK = 40.0
#: Health lost per tick while drowning (debt maxed and still underwater).
DROWN_DAMAGE = 8.0

# Escalating first-person lines, keyed by the debt band (``calm`` says nothing).
_BREATH_PROMPT_PHRASES = {
    "warning": "Your chest tightens; you need air soon.",
    "urgent": "Your lungs are burning.",
    "crisis": "You are drowning — everything narrows to the need for air.",
}


@dataclass(frozen=True)
class BreathComponent(Component):
    """A character's air supply. ``meter.value`` is oxygen debt (higher is worse)."""

    meter: Meter = Meter()

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        if not ctx.is_first_person:
            return ()
        phrase = _BREATH_PROMPT_PHRASES.get(band(self.meter))
        return (phrase,) if phrase else ()


def breath_band(component: BreathComponent) -> str:
    """Coarse breath band (``calm`` is a full breath, ``crisis`` is drowning)."""
    return band(component.meter)


class BreathChangedEvent(DomainEvent):
    """A character's breath crossed into a new band."""

    value: float
    band: str


class DrowningEvent(DomainEvent):
    """A character with no breath left took drowning damage."""

    damage: float


class BreathConsequence:
    """Drain/refill every active character's breath and drown the airless each tick."""

    def __init__(
        self,
        *,
        drain_per_depth: float = DRAIN_PER_DEPTH,
        refill_per_tick: float = REFILL_PER_TICK,
        drown_damage: float = DROWN_DAMAGE,
    ):
        self.drain_per_depth = drain_per_depth
        self.refill_per_tick = refill_per_tick
        self.drown_damage = drown_damage

    def process(self, world: World, epoch: int) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        for character in list(world.query().with_all([BreathComponent]).execute_entities()):
            if character.has_component(SuspendedComponent) or character.has_component(
                DeadComponent
            ):
                continue
            events.extend(self._update_character(world, epoch, character))
        return events

    def _update_character(self, world, epoch, character) -> list[DomainEvent]:
        room = room_of(world, character.id)
        submerged = is_water_room(room)
        component = character.get_component(BreathComponent)
        if submerged:
            delta = self.drain_per_depth * room_depth(room) * self._drain_multiplier(
                world, character
            )
        else:
            delta = -self.refill_per_tick
        if delta == 0.0:
            return []

        old_band = band(component.meter)
        updated_meter = changed(component.meter, delta)
        events: list[DomainEvent] = []
        if updated_meter.value != component.meter.value:
            replace_component(character, replace(component, meter=updated_meter))
            new_band = band(updated_meter)
            if new_band != old_band:
                events.append(
                    BreathChangedEvent(
                        **event_base(
                            epoch,
                            default_visibility=EventVisibility.PRIVATE,
                            actor_id=str(character.id),
                            value=updated_meter.value,
                            band=new_band,
                        )
                    )
                )

        if submerged and updated_meter.value >= updated_meter.crisis_at:
            drown = self._drown(character, epoch)
            if drown is not None:
                events.append(drown)
        return events

    def _drain_multiplier(self, world, character) -> float:
        multiplier = 1.0
        rebreather = held_rebreather(world, character)
        if rebreather is not None:
            efficiency = rebreather.get_component(RebreatherComponent).efficiency
            multiplier *= max(0.0, 1.0 - efficiency)
        skill = (
            character.get_component(SwimSkillComponent)
            if character.has_component(SwimSkillComponent)
            else None
        )
        return multiplier * swim_drain_multiplier(skill)

    def _drown(self, character, epoch) -> DomainEvent | None:
        if not character.has_component(HealthComponent):
            return None
        health = character.get_component(HealthComponent)
        if health.current <= 0.0:
            return None
        new_current = max(0.0, health.current - self.drown_damage)
        replace_component(character, replace(health, current=new_current))
        return DrowningEvent(
            **event_base(
                epoch,
                default_visibility=EventVisibility.PRIVATE,
                actor_id=str(character.id),
                damage=self.drown_damage,
            )
        )


def breath_fragments(world: World, character) -> list[str]:
    """First-person burning-lungs lines for a character running low on air."""
    if character is None or not character.has_component(BreathComponent):
        return []
    ctx = ComponentPromptContext.for_entity(world, character)
    return list(character.get_component(BreathComponent).prompt_fragments(ctx))


__all__ = [
    "DROWN_DAMAGE",
    "DRAIN_PER_DEPTH",
    "REFILL_PER_TICK",
    "BreathChangedEvent",
    "BreathComponent",
    "BreathConsequence",
    "DrowningEvent",
    "breath_band",
    "breath_fragments",
]
