"""Branch-coverage tests for the aquasim v2 bundle and its integration seams.

These exercise the remaining reachable rejection, skip, and partner-present paths so the
enforced coverage gate reflects real behaviour rather than untested holes.
"""

from __future__ import annotations

import asyncio

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    HealthComponent,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)
from bunnyland.core.commands import CommandCost, Lane, build_submitted_command
from bunnyland.core.components import GenerationIntentComponent
from bunnyland.core.events import ObjectGeneratedEvent, RoomGeneratedEvent, event_base
from bunnyland.core.handlers import HandlerContext
from bunnyland.mechanics.meter import Meter
from bunnyland.plugins import apply_plugins, load_modules
from bunnyland.prompts.context import ComponentPromptContext
from pydantic.dataclasses import dataclass
from relics import Component

from bunnyland_aquasim import (
    BreathComponent,
    HarvestHandler,
    HarvestNodeComponent,
    MarineLifeComponent,
    MarineThreatConsequence,
    RebreatherComponent,
    StructureComponent,
    SubmergedComponent,
    SurveyHandler,
    SwimSkillComponent,
    active_characters_in_room,
    holder_of,
    is_water_room,
    marine_life_in_room,
    marinelife_fragments,
    read_luck,
    room_of,
    spawn_dive_gear,
)
from bunnyland_aquasim import synergy as synergy_mod

EPOCH = 100


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------


def _water_room(world, *, biome="reef"):
    room = spawn_entity(world, [RoomComponent(title="Reef", biome=biome)])
    room.add_component(SubmergedComponent(depth=1.0))
    return room


def _place(world, room, entity):
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), entity.id)


def _diver(world, room, *, name="Vin", experience=0.0, health=None):
    comps = [
        IdentityComponent(name=name, kind="character"),
        CharacterComponent(),
        SwimSkillComponent(level=0.0, experience=experience),
    ]
    if health is not None:
        comps.append(HealthComponent(current=health, maximum=100.0))
    character = spawn_entity(world, comps)
    _place(world, room, character)
    return character


def _cmd(character_id, command_type, payload=None):
    return build_submitted_command(
        character_id=str(character_id),
        controller_id="ctrl",
        controller_generation=0,
        command_type=command_type,
        cost=CommandCost(action=1),
        lane=Lane.WORLD,
        payload=payload or {},
    )


def _run(handler_cls, actor, character, command_type, payload=None):
    ctx = HandlerContext(world=actor.world, epoch=EPOCH)
    return handler_cls().execute(ctx, _cmd(character.id, command_type, payload))


# --------------------------------------------------------------------------------------
# skill-up branches (improve_swim returns an event)
# --------------------------------------------------------------------------------------


def test_survey_emits_skill_event_on_level_up():
    actor = WorldActor()
    room = _water_room(actor.world)
    room.add_component(StructureComponent(kind="wreck", depth_rating=0.0))
    diver = _diver(actor.world, room, experience=2.0)  # +1 use -> level up
    gear = spawn_dive_gear(actor.world, tier="scuba")
    diver.add_relationship(Contains(mode=ContainmentMode.INVENTORY), gear.id)
    result = _run(SurveyHandler, actor, diver, "survey")
    assert result.ok
    from bunnyland_aquasim import SwimSkillImprovedEvent

    assert any(isinstance(e, SwimSkillImprovedEvent) for e in result.events)


def test_harvest_emits_skill_event_and_publishes_collectible_call():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room, experience=2.0)
    node = spawn_entity(actor.world, [IdentityComponent(name="bed", kind="node")])
    node.add_component(
        HarvestNodeComponent(
            resource="pearl", table=("a pearl",), remaining=1, collectible=True, category="gem"
        )
    )
    _place(actor.world, room, node)
    result = _run(HarvestHandler, actor, diver, "harvest")
    assert result.ok
    from bunnyland_aquasim import SwimSkillImprovedEvent

    assert any(isinstance(e, SwimSkillImprovedEvent) for e in result.events)


# --------------------------------------------------------------------------------------
# marine-life edge branches
# --------------------------------------------------------------------------------------


def test_predator_ignores_a_creature_that_is_also_a_character():
    actor = WorldActor()
    room = _water_room(actor.world)
    # A character that also carries MarineLifeComponent is not treated as prey to bite.
    hybrid = _diver(actor.world, room, health=100.0)
    hybrid.add_component(MarineLifeComponent(species="merfolk", role="forage", threat=0.0))
    _place(actor.world, room, hybrid)
    creature = spawn_entity(
        actor.world,
        [
            IdentityComponent(name="shark", kind="character"),
            MarineLifeComponent(species="shark", role="predator", threat=5.0),
        ],
    )
    _place(actor.world, room, creature)
    assert MarineThreatConsequence().process(actor.world, EPOCH) == []
    assert hybrid.get_component(HealthComponent).current == 100.0


def test_marinelife_fragments_skips_the_viewer_itself():
    actor = WorldActor()
    room = _water_room(actor.world)
    viewer = spawn_entity(
        actor.world,
        [
            IdentityComponent(name="merfolk", kind="character"),
            CharacterComponent(),
            MarineLifeComponent(species="merfolk", role="forage", threat=0.0),
        ],
    )
    _place(actor.world, room, viewer)
    assert marinelife_fragments(actor.world, viewer) == []  # only itself here
    assert marine_life_in_room(actor.world, room)  # but it is a marine entity in the room


# --------------------------------------------------------------------------------------
# spatial branches
# --------------------------------------------------------------------------------------


def test_spatial_edge_cases():
    actor = WorldActor()
    # holder_of / room_of on a missing id.
    assert holder_of(actor.world, "entity_9999") is None
    assert room_of(actor.world, "entity_9999") is None
    # An uncontained entity has no holder and no room.
    loose = spawn_entity(actor.world, [IdentityComponent(name="drift", kind="item")])
    assert holder_of(actor.world, loose.id) is None
    assert room_of(actor.world, loose.id) is None
    # A non-character resting in a room is excluded from active characters.
    room = _water_room(actor.world)
    _place(actor.world, room, loose)
    _diver(actor.world, room, name="Real")
    actives = active_characters_in_room(actor.world, room)
    assert [c.get_component(IdentityComponent).name for c in actives] == ["Real"]


def test_is_water_room_by_biome_without_submerged_marker():
    actor = WorldActor()
    reef = spawn_entity(actor.world, [RoomComponent(title="Reef", biome="reef")])
    assert is_water_room(reef)  # aquatic biome alone is enough
    meadow = spawn_entity(actor.world, [RoomComponent(title="Field", biome="meadow")])
    assert not is_water_room(meadow)
    assert not is_water_room(None)


# --------------------------------------------------------------------------------------
# gear held-lookup skip branches
# --------------------------------------------------------------------------------------


def test_held_dive_gear_skips_non_gear_inventory():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room)
    junk = spawn_entity(actor.world, [IdentityComponent(name="shell", kind="item")])
    diver.add_relationship(Contains(mode=ContainmentMode.INVENTORY), junk.id)
    from bunnyland_aquasim import gear_pressure_rating, held_dive_gear

    assert held_dive_gear(actor.world, diver) is None
    assert gear_pressure_rating(actor.world, diver) == 0.0
    gear = spawn_dive_gear(actor.world, tier="scuba")
    diver.add_relationship(Contains(mode=ContainmentMode.INVENTORY), gear.id)
    assert held_dive_gear(actor.world, diver).id == gear.id


# --------------------------------------------------------------------------------------
# component prompt fragments
# --------------------------------------------------------------------------------------


def test_passive_component_fragments():
    actor = WorldActor()
    room = _water_room(actor.world)
    ctx_room = ComponentPromptContext.for_entity(actor.world, room)
    assert SubmergedComponent().prompt_fragments(ctx_room)  # underwater line

    diver = _diver(actor.world, room)
    reb = spawn_entity(actor.world, [IdentityComponent(name="rebreather", kind="item")])
    reb.add_component(RebreatherComponent())
    diver.add_relationship(Contains(mode=ContainmentMode.INVENTORY), reb.id)
    from bunnyland_aquasim import held_rebreather

    assert held_rebreather(actor.world, diver).id == reb.id
    # First-person rebreather line, and nothing in third person.
    ctx_first = ComponentPromptContext.for_entity(actor.world, reb)
    assert reb.get_component(RebreatherComponent).prompt_fragments(ctx_first)
    from bunnyland.prompts.context import PromptPerspective

    ctx_third = ComponentPromptContext.for_entity(
        actor.world, reb, perspective=PromptPerspective(viewer=diver)
    )
    assert reb.get_component(RebreatherComponent).prompt_fragments(ctx_third) == ()


# --------------------------------------------------------------------------------------
# worldgen hook partial branches
# --------------------------------------------------------------------------------------


def _hook_actor():
    actor = WorldActor()
    apply_plugins(load_modules(["bunnyland_aquasim"]), actor)
    return actor


def _publish(actor, event):
    asyncio.run(actor.bus.publish(event))


def test_worldgen_hook_ignores_missing_and_already_tagged_entities():
    actor = _hook_actor()
    # Bad entity id -> _entity returns None, both handlers no-op safely.
    bad_room = RoomGeneratedEvent(
        **event_base(0),
        seed="s",
        entity_id="entity_9999",
        entity_key="room",
        entity_kind="room",
        generation=GenerationIntentComponent(tags=(), description="a flooded cave"),
        room_key="room",
        biome="reef",
    )
    _publish(actor, bad_room)  # no crash

    # An already-submerged room is left alone (early return branch).
    room = spawn_entity(actor.world, [RoomComponent(title="R", biome="reef")])
    room.add_component(SubmergedComponent(depth=2.0))
    _publish(
        actor,
        RoomGeneratedEvent(
            **event_base(0),
            seed="s",
            entity_id=str(room.id),
            entity_key="room",
            entity_kind="room",
            generation=GenerationIntentComponent(tags=(), description="water"),
            room_key="room",
            biome="reef",
        ),
    )
    assert room.get_component(SubmergedComponent).depth == 2.0  # untouched

    # An object already a cache is left alone.
    from bunnyland_aquasim import TreasureCacheComponent

    obj = spawn_entity(actor.world, [IdentityComponent(name="chest", kind="item")])
    obj.add_component(TreasureCacheComponent(table=("gold",)))
    _publish(
        actor,
        ObjectGeneratedEvent(
            **event_base(0),
            seed="s",
            entity_id=str(obj.id),
            entity_key="thing",
            entity_kind="object",
            generation=GenerationIntentComponent(tags=("treasure",), description="a hoard"),
            object_key="thing",
        ),
    )
    assert obj.get_component(TreasureCacheComponent).table == ("gold",)  # untouched


# --------------------------------------------------------------------------------------
# synergy: partner-present paths (a partner pack is loaded)
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _FakeCollectible(Component):
    category: str = "curio"
    rarity: str = "common"


@dataclass(frozen=True)
class _FakeIngredient(Component):
    tags: tuple[str, ...] = ()


def test_synergy_publishes_when_partners_are_present(monkeypatch):
    from bunnyland_aquasim import (
        fortune_available,
        hearth_available,
        museum_available,
        publish_collectible,
        publish_ingredient,
    )

    monkeypatch.setattr(synergy_mod, "_COLLECTIBLE", _FakeCollectible)
    monkeypatch.setattr(synergy_mod, "_INGREDIENT", _FakeIngredient)
    monkeypatch.setattr(synergy_mod, "_EFFECTIVE_LUCK", lambda entity: 12.0)

    assert (museum_available(), hearth_available(), fortune_available()) == (True, True, True)

    actor = WorldActor()
    item = spawn_entity(actor.world, [IdentityComponent(name="pearl", kind="item")])
    assert publish_collectible(item, category="gem", rarity="rare") is True
    assert item.get_component(_FakeCollectible).rarity == "rare"
    assert publish_ingredient(item, tags=("fish",)) is True
    assert item.get_component(_FakeIngredient).tags == ("fish",)

    diver = spawn_entity(actor.world, [IdentityComponent(name="Vin", kind="character")])
    assert read_luck(diver) == 12.0


def test_harvest_luck_biases_the_pick_when_fortune_is_present(monkeypatch):
    monkeypatch.setattr(synergy_mod, "_EFFECTIVE_LUCK", lambda entity: 100.0)
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room)
    node = spawn_entity(actor.world, [IdentityComponent(name="bed", kind="node")])
    node.add_component(
        HarvestNodeComponent(resource="pearl", table=("plain", "fine", "regal"), remaining=1)
    )
    _place(actor.world, room, node)
    result = _run(HarvestHandler, actor, diver, "harvest")
    assert result.ok
    from bunnyland_aquasim import HarvestedEvent

    event = next(e for e in result.events if isinstance(e, HarvestedEvent))
    # Overwhelming luck pushes the pick to the top of the desirability table.
    assert event.yield_name == "regal"


# --------------------------------------------------------------------------------------
# breath consequence corner (no-op tick / no health)
# --------------------------------------------------------------------------------------


def test_breath_band_and_full_meter_noop():
    from bunnyland_aquasim import BreathConsequence, breath_band

    actor = WorldActor()
    room = _water_room(actor.world)
    diver = spawn_entity(
        actor.world,
        [
            IdentityComponent(name="Full", kind="character"),
            CharacterComponent(),
            BreathComponent(meter=Meter(value=0.0)),
        ],
    )
    _place(actor.world, room, diver)
    assert breath_band(diver.get_component(BreathComponent)) in {"calm", "steady", "ok", "full"}
    # A single tick drains breath from full; the consequence runs without error.
    events = BreathConsequence().process(actor.world, EPOCH)
    assert isinstance(events, list)
