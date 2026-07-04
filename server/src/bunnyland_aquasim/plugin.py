"""Bunnyland plugin entrypoint for the out-of-tree aquasim (swimming/diving) extension."""

from __future__ import annotations

from bunnyland.plugins import (
    CommandContribution,
    ContentContribution,
    EcsContribution,
    Plugin,
    RuntimeContribution,
)

from .breath import BreathChangedEvent, BreathComponent, DrowningEvent, breath_fragments
from .components import RebreatherComponent, SubmergedComponent, TreasureCacheComponent
from .currents import (
    CurrentComponent,
    DriftedEvent,
    HazardComponent,
    HazardStruckEvent,
)
from .diving import (
    DIVE_ACTION_DEFINITIONS,
    DIVE_ACTION_HANDLERS,
    SurfacedEvent,
    TreasureRecoveredEvent,
)
from .enrichment import AquaWorldgenHook
from .install import install_aquasim
from .submersion import submersion_fragments
from .swim import SwimSkillComponent, SwimSkillImprovedEvent, swim_fragments

PLUGIN_ID = "bunnyland.aquasim"


def plugin() -> Plugin:
    return Plugin(
        id=PLUGIN_ID,
        name="Bunnyland Aquasim",
        version="0.1.0",
        default_enabled=True,
        ecs=EcsContribution(
            components=(
                SubmergedComponent,
                RebreatherComponent,
                TreasureCacheComponent,
                BreathComponent,
                SwimSkillComponent,
                CurrentComponent,
                HazardComponent,
            ),
        ),
        commands=CommandContribution(
            action_handlers=DIVE_ACTION_HANDLERS,
            action_definitions=DIVE_ACTION_DEFINITIONS,
            typed_events=(
                BreathChangedEvent,
                DrowningEvent,
                TreasureRecoveredEvent,
                SurfacedEvent,
                DriftedEvent,
                HazardStruckEvent,
                SwimSkillImprovedEvent,
            ),
        ),
        runtime=RuntimeContribution(
            service_factories=(install_aquasim,),
        ),
        content=ContentContribution(
            prompt_fragments=(submersion_fragments, breath_fragments, swim_fragments),
            worldgen_hooks=(AquaWorldgenHook,),
        ),
    )


def bunnyland_plugins() -> list[Plugin]:
    return [plugin()]


__all__ = ["PLUGIN_ID", "bunnyland_plugins", "plugin"]
