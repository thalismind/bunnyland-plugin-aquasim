from __future__ import annotations

from bunnyland.core.world_actor import WorldActor
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_aquasim import (
    AquaWorldgenHook,
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


def test_plugin_loads_with_dotted_id():
    plugins = load_modules(["bunnyland_aquasim"])
    assert [p.id for p in plugins] == ["bunnyland.aquasim"]
    assert PLUGIN_ID == "bunnyland.aquasim"


def test_plugin_declares_its_components():
    plugin = load_modules(["bunnyland_aquasim"])[0]
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
    plugin = load_modules(["bunnyland_aquasim"])[0]
    assert PreysOn in plugin.ecs.edges
    assert DiscoveredBy in plugin.ecs.edges


def test_plugin_declares_content():
    plugin = load_modules(["bunnyland_aquasim"])[0]
    assert AquaWorldgenHook in plugin.content.worldgen_hooks
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
    plugin = load_modules(["bunnyland_aquasim"])[0]
    for event in (SiteDiscoveredEvent, MarineAttackEvent, HarvestedEvent):
        assert event in plugin.commands.typed_events


def test_plugin_version():
    plugin = load_modules(["bunnyland_aquasim"])[0]
    assert plugin.version == "0.2.0"


def test_plugin_recommends_optional_partners():
    plugin = load_modules(["bunnyland_aquasim"])[0]
    assert plugin.dependencies.recommends == (
        "bunnyland.fortunesim",
        "bunnyland.museumsim",
        "bunnyland.hearthsim",
    )
    # Standalone-first: no hard requirements on any partner pack.
    assert plugin.dependencies.requires == ()


def test_plugin_applies_and_registers_verbs():
    actor = WorldActor()
    applied = apply_plugins(load_modules(["bunnyland_aquasim"]), actor)
    assert applied[0].id == "bunnyland.aquasim"
    command_types = {definition.command_type for definition in actor.action_definitions()}
    assert {"dive", "surface", "survey", "harvest"} <= command_types
