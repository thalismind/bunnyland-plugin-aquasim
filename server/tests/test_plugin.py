from __future__ import annotations

from bunnyland.core.world_actor import WorldActor
from bunnyland.plugins import apply_plugins

from bunnyland_aquasim import (
    AquaGenerationEnricher,
    BreathComponent,
    CurrentComponent,
    DiscoveredBy,
    DiveGearComponent,
    HarvestedEvent,
    HarvestNodeComponent,
    HazardComponent,
    MarineAttackEvent,
    MarineLifeComponent,
    PreysOn,
    RebreatherComponent,
    SiteDiscoveredEvent,
    StructureComponent,
    SubmergedComponent,
    SwimSkillComponent,
    TreasureCacheComponent,
    breath_fragments,
    gear_fragments,
    harvest_fragments,
    marinelife_fragments,
    structure_fragments,
    submersion_fragments,
    swim_fragments,
)
from bunnyland_aquasim.plugin import PLUGIN_ID
from bunnyland_aquasim.plugin import bunnyland_plugins as _plugins


def test_plugin_loads_with_dotted_id():
    plugins = _plugins()
    assert [p.id for p in plugins] == ["bunnyland.aquasim"]
    assert PLUGIN_ID == "bunnyland.aquasim"


def test_plugin_declares_its_components():
    plugin = _plugins()[0]
    for component in (
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
    ):
        assert component in plugin.ecs.components


def test_plugin_declares_its_typed_edges():
    plugin = _plugins()[0]
    assert PreysOn in plugin.ecs.edges
    assert DiscoveredBy in plugin.ecs.edges


def test_plugin_declares_content():
    plugin = _plugins()[0]
    assert AquaGenerationEnricher in [type(item) for item in plugin.content.generation_enrichers]
    for provider in (
        submersion_fragments,
        breath_fragments,
        swim_fragments,
        structure_fragments,
        marinelife_fragments,
        gear_fragments,
        harvest_fragments,
    ):
        assert provider in plugin.content.prompt_fragments


def test_plugin_publishes_its_v2_events():
    plugin = _plugins()[0]
    for event in (SiteDiscoveredEvent, MarineAttackEvent, HarvestedEvent):
        assert event in plugin.commands.typed_events


def test_plugin_version():
    plugin = _plugins()[0]
    assert plugin.version == "0.2.0"


def test_plugin_recommends_optional_partners():
    plugin = _plugins()[0]
    assert plugin.dependencies.recommends == (
        "bunnyland.fortunesim",
        "bunnyland.museumsim",
        "bunnyland.hearthsim",
    )
    # Standalone-first: no hard requirements on any partner pack.
    assert plugin.dependencies.requires == ()


def test_plugin_applies_and_registers_verbs():
    actor = WorldActor()
    applied = apply_plugins(_plugins(), actor)
    assert applied[0].id == "bunnyland.aquasim"
    command_types = {definition.command_type for definition in actor.action_definitions()}
    assert {"dive", "surface", "survey", "harvest"} <= command_types
