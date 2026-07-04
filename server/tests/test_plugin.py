from __future__ import annotations

from bunnyland.core.world_actor import WorldActor
from bunnyland.plugins import apply_plugins, load_modules

from bunnyland_aquasim import (
    AquaWorldgenHook,
    BreathComponent,
    CurrentComponent,
    HazardComponent,
    RebreatherComponent,
    SubmergedComponent,
    SwimSkillComponent,
    TreasureCacheComponent,
    breath_fragments,
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
    ):
        assert component in plugin.ecs.components


def test_plugin_declares_content():
    plugin = load_modules(["bunnyland_aquasim"])[0]
    assert AquaWorldgenHook in plugin.content.worldgen_hooks
    for provider in (submersion_fragments, breath_fragments, swim_fragments):
        assert provider in plugin.content.prompt_fragments


def test_plugin_version():
    plugin = load_modules(["bunnyland_aquasim"])[0]
    assert plugin.version == "0.1.0"


def test_plugin_applies_and_registers_verbs():
    actor = WorldActor()
    applied = apply_plugins(load_modules(["bunnyland_aquasim"]), actor)
    assert applied[0].id == "bunnyland.aquasim"
    command_types = {definition.command_type for definition in actor.action_definitions()}
    assert {"dive", "surface"} <= command_types
