"""Bunnyland plugin entrypoint for the out-of-tree aquasim (swimming/diving) extension."""

from __future__ import annotations

from bunnyland.plugins import (
    CommandContribution,
    ContentContribution,
    DependencyContribution,
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
from .edges import DiscoveredBy, PreysOn
from .enrichment import AquaWorldgenHook
from .gear import DiveGearComponent, gear_fragments
from .harvest import (
    HARVEST_ACTION_DEFINITIONS,
    HARVEST_ACTION_HANDLERS,
    HarvestedEvent,
    HarvestNodeComponent,
    harvest_fragments,
)
from .install import install_aquasim
from .marinelife import (
    MarineAttackEvent,
    MarineLifeComponent,
    marinelife_fragments,
)
from .structures import (
    SURVEY_ACTION_DEFINITIONS,
    SURVEY_ACTION_HANDLERS,
    SiteDiscoveredEvent,
    StructureComponent,
    structure_fragments,
)
from .submersion import submersion_fragments
from .swim import SwimSkillComponent, SwimSkillImprovedEvent, swim_fragments

PLUGIN_ID = "bunnyland.aquasim"


def plugin() -> Plugin:
    return Plugin(
        id=PLUGIN_ID,
        name="Bunnyland Aquasim",
        version="0.2.0",
        default_enabled=True,
        # Optional synergy, conditionally imported and disabled when absent: fortunesim's Luck
        # biases loot, museumsim exhibits pearls/treasure, hearthsim cooks edible harvest.
        dependencies=DependencyContribution(
            recommends=(
                "bunnyland.fortunesim",
                "bunnyland.museumsim",
                "bunnyland.hearthsim",
            ),
        ),
        ecs=EcsContribution(
            components=(
                SubmergedComponent,
                RebreatherComponent,
                TreasureCacheComponent,
                BreathComponent,
                SwimSkillComponent,
                CurrentComponent,
                HazardComponent,
                StructureComponent,
                MarineLifeComponent,
                DiveGearComponent,
                HarvestNodeComponent,
            ),
            edges=(PreysOn, DiscoveredBy),
        ),
        commands=CommandContribution(
            action_handlers=(
                *DIVE_ACTION_HANDLERS,
                *SURVEY_ACTION_HANDLERS,
                *HARVEST_ACTION_HANDLERS,
            ),
            action_definitions=(
                *DIVE_ACTION_DEFINITIONS,
                *SURVEY_ACTION_DEFINITIONS,
                *HARVEST_ACTION_DEFINITIONS,
            ),
            typed_events=(
                BreathChangedEvent,
                DrowningEvent,
                TreasureRecoveredEvent,
                SurfacedEvent,
                DriftedEvent,
                HazardStruckEvent,
                SwimSkillImprovedEvent,
                SiteDiscoveredEvent,
                MarineAttackEvent,
                HarvestedEvent,
            ),
        ),
        runtime=RuntimeContribution(
            service_factories=(install_aquasim,),
        ),
        content=ContentContribution(
            prompt_fragments=(
                submersion_fragments,
                breath_fragments,
                swim_fragments,
                structure_fragments,
                marinelife_fragments,
                gear_fragments,
                harvest_fragments,
            ),
            worldgen_hooks=(AquaWorldgenHook,),
        ),
    )


def bunnyland_plugins() -> list[Plugin]:
    return [plugin()]


__all__ = ["PLUGIN_ID", "bunnyland_plugins", "plugin"]
