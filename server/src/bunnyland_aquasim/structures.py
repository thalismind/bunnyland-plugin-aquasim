"""Underwater structures and the ``survey`` verb (v2 headline mechanic, part 1).

A water room may carry a :class:`StructureComponent` — a wreck, a drowned ruin, a grotto, a
kelp forest, an abyssal trench. Surveying it charts the site: the first surveyor is credited
(a :class:`~bunnyland_aquasim.edges.DiscoveredBy` edge) and a :class:`SiteDiscoveredEvent`
is **published** on the bus. That event is this pack's Discovery connector surface — a
cartography pack can chart the site by subscribing, with no dependency in either direction.

Reaching a deep structure needs gear: a site's ``depth_rating`` gates the ``survey`` verb
against the diver's best :class:`~bunnyland_aquasim.gear.DiveGearComponent` pressure rating,
so diving-gear tiers matter. Everything here is deterministic.
"""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core.actions import ActionArgument, ActionDefinition
from bunnyland.core.commands import CommandCost, Lane, SubmittedCommand
from bunnyland.core.ecs import replace_component
from bunnyland.core.events import DomainEvent, EventVisibility
from bunnyland.core.handlers import (
    HandlerContext,
    HandlerResult,
    ok,
    rejected,
    require_character,
)
from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component, Entity, World

from .edges import credit_discovery
from .gear import gear_pressure_rating
from .spatial import room_of
from .submersion import is_water_room
from .swim import improve_swim

#: Human-readable descriptions per structure kind, shown to anyone in the room.
STRUCTURE_DESCRIPTIONS: dict[str, str] = {
    "wreck": "The barnacled hull of a sunken wreck looms in the murk.",
    "ruin": "Drowned columns of a sunken ruin rise from the silt.",
    "grotto": "A hollow grotto opens in the reef wall.",
    "kelp_forest": "A towering kelp forest sways in the current.",
    "trench": "The seabed falls away into a lightless trench.",
}


@dataclass(frozen=True)
class StructureComponent(Component):
    """Marks a water room as a dive site. ``depth_rating`` gates the gear needed to survey."""

    kind: str = "wreck"
    charted: bool = False
    depth_rating: float = 1.0
    renown: float = 1.0

    def prompt_fragments(self, ctx: ComponentPromptContext) -> tuple[str, ...]:
        description = STRUCTURE_DESCRIPTIONS.get(
            self.kind, f"A sunken {self.kind.replace('_', ' ')} lies here."
        )
        if self.charted:
            return (f"{description} It has been charted.",)
        return (f"{description} It is uncharted.",)


class SiteDiscoveredEvent(DomainEvent):
    """A diver charted an underwater structure (the Discovery connector surface)."""

    site_id: str
    kind: str
    depth_rating: float
    renown: float


def structure_of_room(room: Entity | None) -> StructureComponent | None:
    """Return the structure a water room hosts, or ``None`` if it is open water."""
    if room is None or not room.has_component(StructureComponent):
        return None
    return room.get_component(StructureComponent)


class SurveyHandler:
    """Chart the underwater structure in the diver's water room."""

    command_type = "survey"

    def execute(self, ctx: HandlerContext, command: SubmittedCommand) -> HandlerResult:
        character_id, character, rejection = require_character(ctx, command.character_id)
        if rejection is not None:
            return rejection
        room = room_of(ctx.world, character_id)
        if not is_water_room(room):
            return rejected("you are not in the water")
        structure = structure_of_room(room)
        if structure is None:
            return rejected("there is nothing here to survey")
        if structure.charted:
            return rejected("this site has already been charted")
        if gear_pressure_rating(ctx.world, character) < structure.depth_rating:
            return rejected("you need heavier diving gear to reach this depth")

        replace_component(room, replace(structure, charted=True))
        credit_discovery(room, character_id, epoch=ctx.epoch)
        event = SiteDiscoveredEvent(
            **ctx.event_base(
                visibility=EventVisibility.ROOM,
                actor_id=str(character_id),
                room_id=str(room.id),
                target_ids=(str(room.id),),
                site_id=str(room.id),
                kind=structure.kind,
                depth_rating=structure.depth_rating,
                renown=structure.renown,
            )
        )
        events: list[DomainEvent] = [event]
        skill_event = improve_swim(character, epoch=ctx.epoch)
        if skill_event is not None:
            events.append(skill_event)
        return ok(*events)


def structure_fragments(world: World, character: Entity) -> list[str]:
    """Describe the dive site in the character's current water room, if any."""
    if character is None:
        return []
    room = room_of(world, character.id)
    structure = structure_of_room(room)
    if structure is None:
        return []
    ctx = ComponentPromptContext.for_entity(world, room)
    return list(structure.prompt_fragments(ctx))


SURVEY_DEF = ActionDefinition(
    command_type="survey",
    title="Survey",
    description="Chart the underwater structure in the water room you are in.",
    lane=Lane.WORLD,
    cost=CommandCost(action=1),
    arguments={
        "note": ActionArgument(
            title="Note",
            description="An optional survey note (unused by the mechanic).",
            kind="text",
        ),
    },
)

SURVEY_ACTION_DEFINITIONS = (SURVEY_DEF,)
SURVEY_ACTION_HANDLERS = (SurveyHandler,)


__all__ = [
    "STRUCTURE_DESCRIPTIONS",
    "SURVEY_ACTION_DEFINITIONS",
    "SURVEY_ACTION_HANDLERS",
    "SURVEY_DEF",
    "SiteDiscoveredEvent",
    "StructureComponent",
    "SurveyHandler",
    "structure_fragments",
    "structure_of_room",
]
