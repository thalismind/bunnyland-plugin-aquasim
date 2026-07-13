"""Behaviour tests for the aquasim v2 bundle: structures, marine life, gear, harvest."""

from __future__ import annotations

from dataclasses import replace

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    DeadComponent,
    HealthComponent,
    IdentityComponent,
    RoomComponent,
    SuspendedComponent,
    WorldActor,
    contents,
    spawn_entity,
)
from bunnyland.core.commands import CommandCost, Lane, build_submitted_command
from bunnyland.core.ecs import replace_component
from bunnyland.core.handlers import HandlerContext
from bunnyland.foundation.consumables.components import FoodComponent
from bunnyland.foundation.meters.mechanics import Meter
from bunnyland.prompts.context import ComponentPromptContext, PromptPerspective
from conftest import execute_handler

from bunnyland_aquasim import (
    BreathComponent,
    DiscoveredBy,
    DiveGearComponent,
    HarvestedEvent,
    HarvestHandler,
    HarvestNodeComponent,
    MarineAttackEvent,
    MarineLifeComponent,
    MarineThreatConsequence,
    PreysOn,
    SiteDiscoveredEvent,
    StructureComponent,
    SubmergedComponent,
    SurveyHandler,
    SwimSkillComponent,
    active_characters_in_room,
    credit_discovery,
    discoverer_id_of,
    gear_fragments,
    gear_pressure_rating,
    gear_stats,
    harvest_fragments,
    held_dive_gear,
    holder_of,
    is_threat,
    luck_biased_index,
    luck_biased_loot,
    marine_life_in_room,
    marinelife_fragments,
    prey_ids,
    prey_present,
    read_luck,
    spawn_dive_gear,
    structure_fragments,
    structure_of_room,
)

EPOCH = 100


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------


def _water_room(world, *, biome="reef"):
    room = spawn_entity(world, [RoomComponent(title="Reef", biome=biome)])
    room.add_component(SubmergedComponent(depth=1.0))
    return room


def _dry_room(world):
    return spawn_entity(world, [RoomComponent(title="Deck", biome="meadow")])


def _place(world, room, entity, mode=ContainmentMode.ROOM_CONTENT):
    room.add_relationship(Contains(mode=mode), entity.id)


def _diver(world, room, *, skill=1.0, breath=None, health=None, name="Vin"):
    components = [IdentityComponent(name=name, kind="character"), CharacterComponent()]
    if skill is not None:
        components.append(SwimSkillComponent(level=skill))
    if breath is not None:
        components.append(BreathComponent(meter=Meter(value=breath)))
    if health is not None:
        components.append(HealthComponent(current=health, maximum=100.0))
    character = spawn_entity(world, components)
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


def _run(handler_cls, actor, character, command_type, payload=None, epoch=EPOCH):
    ctx = HandlerContext(world=actor.world, epoch=epoch)
    return execute_handler(handler_cls(), ctx, _cmd(character.id, command_type, payload))


def _structure_room(world, *, kind="wreck", depth_rating=1.0, renown=1.0):
    room = _water_room(world)
    room.add_component(StructureComponent(kind=kind, depth_rating=depth_rating, renown=renown))
    return room


def _marine(world, room, *, species="shark", role="predator", threat=5.0):
    creature = spawn_entity(
        world,
        [
            IdentityComponent(name=species, kind="character"),
            MarineLifeComponent(species=species, role=role, threat=threat),
        ],
    )
    _place(world, room, creature)
    return creature


def _harvest_node(world, room, **kwargs):
    node = spawn_entity(world, [IdentityComponent(name="node", kind="node")])
    node.add_component(HarvestNodeComponent(**kwargs))
    _place(world, room, node)
    return node


# --------------------------------------------------------------------------------------
# gear tiers
# --------------------------------------------------------------------------------------


def test_gear_stats_and_fallback():
    assert gear_stats("atmospheric_suit") == (0.95, 5.0)
    # Unknown tier falls back to the snorkel.
    assert gear_stats("floaties") == gear_stats("snorkel")


def test_spawn_dive_gear_carries_both_components():
    actor = WorldActor()
    gear = spawn_dive_gear(actor.world, tier="rebreather")
    dg = gear.get_component(DiveGearComponent)
    assert dg.tier == "rebreather"
    assert dg.pressure_rating == 2.5
    # It also carries the v1 RebreatherComponent so breath relief benefits from the tier.
    from bunnyland_aquasim import RebreatherComponent

    assert gear.has_component(RebreatherComponent)


def test_held_dive_gear_picks_the_deepest_rated():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room)
    snorkel = spawn_dive_gear(actor.world, tier="snorkel")
    suit = spawn_dive_gear(actor.world, tier="atmospheric_suit")
    diver.add_relationship(Contains(mode=ContainmentMode.INVENTORY), snorkel.id)
    diver.add_relationship(Contains(mode=ContainmentMode.INVENTORY), suit.id)
    best = held_dive_gear(actor.world, diver)
    assert best is not None and best.id == suit.id
    assert gear_pressure_rating(actor.world, diver) == 5.0


def test_gear_pressure_rating_zero_without_gear():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room)
    assert gear_pressure_rating(actor.world, diver) == 0.0


def test_gear_fragments_first_person_only():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room)
    gear = spawn_dive_gear(actor.world, tier="scuba")
    diver.add_relationship(Contains(mode=ContainmentMode.INVENTORY), gear.id)
    lines = gear_fragments(actor.world, diver)
    assert lines and "scuba" in lines[0]
    # Third-person context (a different viewer) yields nothing.
    third = ComponentPromptContext.for_entity(
        actor.world, gear, perspective=PromptPerspective(viewer=diver)
    )
    assert gear.get_component(DiveGearComponent).prompt_fragments(third) == ()
    # No character / no gear -> empty.
    assert gear_fragments(actor.world, None) == []
    assert gear_fragments(actor.world, _diver(actor.world, room, name="Bare")) == []


def test_gear_prompt_fragment_unknown_tier_label():
    actor = WorldActor()
    gear = spawn_entity(actor.world, [IdentityComponent(name="odd", kind="item")])
    gear.add_component(DiveGearComponent(tier="mystery"))
    ctx = ComponentPromptContext.for_entity(actor.world, gear)  # viewer is the gear -> first person
    frag = gear.get_component(DiveGearComponent).prompt_fragments(ctx)
    assert frag and "a mystery" in frag[0]


# --------------------------------------------------------------------------------------
# structures & survey
# --------------------------------------------------------------------------------------


def test_survey_charts_a_site_and_credits_the_discoverer():
    actor = WorldActor()
    room = _structure_room(actor.world, kind="wreck", depth_rating=1.0, renown=3.0)
    diver = _diver(actor.world, room, skill=0.0)
    gear = spawn_dive_gear(actor.world, tier="scuba")
    diver.add_relationship(Contains(mode=ContainmentMode.INVENTORY), gear.id)

    result = _run(SurveyHandler, actor, diver, "survey")

    assert result.ok
    event = next(e for e in result.events if isinstance(e, SiteDiscoveredEvent))
    assert event.kind == "wreck" and event.renown == 3.0
    assert room.get_component(StructureComponent).charted
    assert discoverer_id_of(room) == diver.id
    # Surveying trains the swim skill (level 0 -> gains xp).
    assert diver.get_component(SwimSkillComponent).experience > 0.0


def test_survey_rejects_without_deep_enough_gear():
    actor = WorldActor()
    room = _structure_room(actor.world, depth_rating=5.0)
    diver = _diver(actor.world, room)
    snorkel = spawn_dive_gear(actor.world, tier="snorkel")
    diver.add_relationship(Contains(mode=ContainmentMode.INVENTORY), snorkel.id)
    result = _run(SurveyHandler, actor, diver, "survey")
    assert not result.ok
    assert result.reason == "you need heavier diving gear to reach this depth"


def test_survey_rejects_on_dry_land():
    actor = WorldActor()
    room = _dry_room(actor.world)
    diver = _diver(actor.world, room)
    result = _run(SurveyHandler, actor, diver, "survey")
    assert result.reason == "you are not in the water"


def test_survey_rejects_when_nothing_to_chart():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room)
    result = _run(SurveyHandler, actor, diver, "survey")
    assert result.reason == "there is nothing here to survey"


def test_survey_rejects_already_charted():
    actor = WorldActor()
    room = _structure_room(actor.world)
    replace_component(room, replace(room.get_component(StructureComponent), charted=True))
    diver = _diver(actor.world, room)
    spawn_dive_gear(actor.world)  # loose gear, still enough
    gear = spawn_dive_gear(actor.world, tier="scuba")
    diver.add_relationship(Contains(mode=ContainmentMode.INVENTORY), gear.id)
    result = _run(SurveyHandler, actor, diver, "survey")
    assert result.reason == "this site has already been charted"


def test_survey_rejects_invalid_character():
    actor = WorldActor()
    result = execute_handler(
        SurveyHandler(), HandlerContext(world=actor.world, epoch=EPOCH), _cmd("???", "survey")
    )
    assert result.reason == "invalid character id"


def test_structure_helpers_and_fragments():
    actor = WorldActor()
    room = _structure_room(actor.world, kind="grotto")
    diver = _diver(actor.world, room)
    assert structure_of_room(room).kind == "grotto"
    assert structure_of_room(None) is None
    assert structure_of_room(_water_room(actor.world)) is None
    lines = structure_fragments(actor.world, diver)
    assert lines and "uncharted" in lines[0]
    # Charted variant, unknown-kind fallback text, and no-character path.
    replace_component(
        room, replace(room.get_component(StructureComponent), kind="atoll", charted=True)
    )
    charted = structure_fragments(actor.world, diver)
    assert "charted" in charted[0] and "atoll" in charted[0]
    assert structure_fragments(actor.world, None) == []
    assert structure_fragments(actor.world, _diver(actor.world, _water_room(actor.world))) == []


# --------------------------------------------------------------------------------------
# marine life & threat
# --------------------------------------------------------------------------------------


def test_is_threat_classifies_roles():
    assert is_threat(MarineLifeComponent(role="predator", threat=1.0))
    assert not is_threat(MarineLifeComponent(role="prey", threat=1.0))
    assert not is_threat(MarineLifeComponent(role="apex", threat=0.0))


def test_predator_bites_a_diver_sharing_its_room():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room, skill=0.0, health=100.0)
    _marine(actor.world, room, species="shark", role="predator", threat=8.0)

    events = MarineThreatConsequence().process(actor.world, EPOCH)

    assert any(isinstance(e, MarineAttackEvent) for e in events)
    assert diver.get_component(HealthComponent).current == 92.0


def test_mastery_blunts_the_bite():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room, skill=5.0, health=100.0)  # master swimmer
    _marine(actor.world, room, species="shark", role="predator", threat=8.0)
    MarineThreatConsequence().process(actor.world, EPOCH)
    assert diver.get_component(HealthComponent).current == 96.0  # halved damage


def test_a_feeding_predator_ignores_divers():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room, health=100.0)
    shark = _marine(actor.world, room, role="predator", threat=8.0)
    seal = _marine(actor.world, room, species="seal", role="prey", threat=0.0)
    shark.add_relationship(PreysOn(strength=1.0), seal.id)
    assert prey_present(actor.world, shark, room)

    events = MarineThreatConsequence().process(actor.world, EPOCH)
    assert events == []
    assert diver.get_component(HealthComponent).current == 100.0


def test_threat_skips_suspended_dead_and_non_threats():
    actor = WorldActor()
    room = _water_room(actor.world)
    _diver(actor.world, room, health=100.0)
    harmless = _marine(actor.world, room, species="clownfish", role="forage", threat=0.0)
    assert not is_threat(harmless.get_component(MarineLifeComponent))
    suspended = _marine(actor.world, room, role="predator", threat=5.0)
    suspended.add_component(SuspendedComponent())
    dead = _marine(actor.world, room, role="predator", threat=5.0)
    dead.add_component(DeadComponent(died_at_epoch=0, cause="test"))
    # Only harmless/suspended/dead predators present -> no bites.
    assert MarineThreatConsequence().process(actor.world, EPOCH) == []


def test_threat_needs_a_water_room_and_a_healthy_target():
    actor = WorldActor()
    dry = _dry_room(actor.world)
    _diver(actor.world, dry, health=100.0)
    _marine(actor.world, dry, role="predator", threat=5.0)
    assert MarineThreatConsequence().process(actor.world, EPOCH) == []

    # In water, but the only diver is already at zero health -> no further bite.
    water = _water_room(actor.world)
    downed = _diver(actor.world, water, health=0.0)
    _marine(actor.world, water, role="predator", threat=5.0)
    assert MarineThreatConsequence().process(actor.world, EPOCH) == []
    assert downed.get_component(HealthComponent).current == 0.0


def test_threat_skips_a_diver_without_health():
    actor = WorldActor()
    room = _water_room(actor.world)
    _diver(actor.world, room, health=None)  # no HealthComponent
    _marine(actor.world, room, role="predator", threat=5.0)
    assert MarineThreatConsequence().process(actor.world, EPOCH) == []


def test_predator_does_not_bite_itself_or_other_creatures():
    actor = WorldActor()
    room = _water_room(actor.world)
    # Two predators, no divers: neither bites the other (both carry MarineLifeComponent).
    _marine(actor.world, room, role="predator", threat=5.0)
    _marine(actor.world, room, species="eel", role="predator", threat=5.0)
    assert MarineThreatConsequence().process(actor.world, EPOCH) == []


def test_marine_life_helpers_and_fragments():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room)
    _marine(actor.world, room, species="ray", role="forage", threat=0.0)
    assert marine_life_in_room(actor.world, None) == []
    assert len(marine_life_in_room(actor.world, room)) == 1
    lines = marinelife_fragments(actor.world, diver)
    assert lines and "ray" in lines[0]
    assert marinelife_fragments(actor.world, None) == []
    stray = spawn_entity(actor.world, [IdentityComponent(name="lost", kind="character")])
    assert marinelife_fragments(actor.world, stray) == []


# --------------------------------------------------------------------------------------
# harvest & deterministic loot
# --------------------------------------------------------------------------------------


def test_luck_biased_loot_is_deterministic_and_shifts_with_luck():
    table = ("plain", "nice", "rare")
    first = luck_biased_loot("node_1", EPOCH, table, 0.0)
    assert first == luck_biased_loot("node_1", EPOCH, table, 0.0)
    assert first in table
    # 10 luck (2 steps of 5) pushes the pick toward the rare end (clamped in-range).
    base = luck_biased_index("node_1", EPOCH, len(table), 0.0)
    boosted = luck_biased_index("node_1", EPOCH, len(table), 10.0)
    assert boosted >= base
    assert boosted <= len(table) - 1


def test_harvest_pulls_a_yield_and_feeds_hunger():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room, skill=0.0)
    _harvest_node(
        actor.world,
        room,
        resource="fish",
        table=("a silvery fish",),
        remaining=2,
        edible=True,
        nutrition=4.0,
        satiety=3.0,
        food_tags=("fish",),
    )

    result = _run(HarvestHandler, actor, diver, "harvest")

    assert result.ok
    event = next(e for e in result.events if isinstance(e, HarvestedEvent))
    assert event.resource == "fish"
    items = [actor.world.get_entity(i) for i in contents(diver)]
    assert any(i.has_component(FoodComponent) for i in items)  # core hunger, no partner needed
    # swim skill trained
    assert diver.get_component(SwimSkillComponent).experience > 0.0


def test_harvest_decrements_remaining_and_exhausts():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room)
    node = _harvest_node(actor.world, room, resource="pearl", table=("a pearl",), remaining=1)
    _run(HarvestHandler, actor, diver, "harvest")
    assert node.get_component(HarvestNodeComponent).remaining == 0
    # Now exhausted; auto-pick finds nothing.
    again = _run(HarvestHandler, actor, diver, "harvest")
    assert again.reason == "there is nothing here to harvest"


def test_harvest_targets_a_named_node():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room)
    _harvest_node(actor.world, room, resource="coral", table=("coral",), remaining=1)
    chosen = _harvest_node(actor.world, room, resource="pearl", table=("a pearl",), remaining=1)
    result = _run(HarvestHandler, actor, diver, "harvest", {"node_id": str(chosen.id)})
    assert result.ok
    assert chosen.get_component(HarvestNodeComponent).remaining == 0


def test_harvest_rejections():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room)

    # dry land
    dry = _dry_room(actor.world)
    lander = _diver(actor.world, dry, name="Land")
    assert _run(HarvestHandler, actor, lander, "harvest").reason == "you are not in the water"

    # no breath
    gasping = _diver(actor.world, room, breath=100.0, name="Gasp")
    _harvest_node(actor.world, room, table=("x",), remaining=1)
    assert (
        _run(HarvestHandler, actor, gasping, "harvest").reason
        == "you have no breath left to harvest"
    )

    # invalid / missing / not-a-node / elsewhere / exhausted named node
    assert _run(HarvestHandler, actor, diver, "harvest", {"node_id": "??"}).reason == (
        "invalid node id"
    )
    assert _run(HarvestHandler, actor, diver, "harvest", {"node_id": "entity_9999"}).reason == (
        "that node does not exist"
    )
    rock = spawn_entity(actor.world, [IdentityComponent(name="rock", kind="item")])
    _place(actor.world, room, rock)
    assert _run(HarvestHandler, actor, diver, "harvest", {"node_id": str(rock.id)}).reason == (
        "that is not a harvest node"
    )
    other = _water_room(actor.world)
    far = _harvest_node(actor.world, other, table=("x",), remaining=1)
    assert _run(HarvestHandler, actor, diver, "harvest", {"node_id": str(far.id)}).reason == (
        "that node is not here"
    )
    spent = _harvest_node(actor.world, room, table=("x",), remaining=0)
    assert _run(HarvestHandler, actor, diver, "harvest", {"node_id": str(spent.id)}).reason == (
        "that node is exhausted"
    )


def test_harvest_fragments():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room)
    _harvest_node(actor.world, room, resource="pearl", table=("a pearl",), remaining=2)
    _harvest_node(actor.world, room, resource="spent", table=("x",), remaining=0)
    lines = harvest_fragments(actor.world, diver)
    assert any("pearl" in line for line in lines)
    assert not any("spent" in line for line in lines)  # exhausted node stays quiet
    assert harvest_fragments(actor.world, None) == []
    dry = _dry_room(actor.world)
    lander = _diver(actor.world, dry, name="L")
    assert harvest_fragments(actor.world, lander) == []


def test_harvest_node_prompt_fragment_hides_when_exhausted():
    actor = WorldActor()
    node = spawn_entity(actor.world, [IdentityComponent(name="n", kind="node")])
    ctx = ComponentPromptContext.for_entity(actor.world, node)
    assert HarvestNodeComponent(remaining=0).prompt_fragments(ctx) == ()
    assert HarvestNodeComponent(resource="coral", remaining=1).prompt_fragments(ctx)


# --------------------------------------------------------------------------------------
# edges
# --------------------------------------------------------------------------------------


def test_prey_edges_are_stable_and_credit_is_first_finder_only():
    actor = WorldActor()
    room = _water_room(actor.world)
    shark = _marine(actor.world, room, role="predator", threat=5.0)
    a = _marine(actor.world, room, species="a", role="prey", threat=0.0)
    b = _marine(actor.world, room, species="b", role="prey", threat=0.0)
    shark.add_relationship(PreysOn(), a.id)
    shark.add_relationship(PreysOn(), b.id)
    assert prey_ids(shark) == sorted([a.id, b.id], key=str)

    site = _structure_room(actor.world)
    diver = _diver(actor.world, site)
    assert credit_discovery(site, diver.id, epoch=EPOCH) is True
    # A second attempt keeps the original finder.
    other = _diver(actor.world, site, name="Late")
    assert credit_discovery(site, other.id, epoch=EPOCH + 1) is False
    assert discoverer_id_of(site) == diver.id
    assert [t for _e, t in site.get_relationships(DiscoveredBy)] == [diver.id]


def test_prey_present_ignores_prey_in_another_room_or_gone():
    actor = WorldActor()
    room = _water_room(actor.world)
    other = _water_room(actor.world)
    shark = _marine(actor.world, room, role="predator", threat=5.0)
    far = _marine(actor.world, other, species="far", role="prey", threat=0.0)
    shark.add_relationship(PreysOn(), far.id)
    assert prey_present(actor.world, shark, room) is False
    # A dangling prey id (its entity later removed) is skipped, not an error.
    gone = _marine(actor.world, room, species="gone", role="prey", threat=0.0)
    shark.add_relationship(PreysOn(), gone.id)
    actor.world.remove(gone)
    assert prey_present(actor.world, shark, room) is False


# --------------------------------------------------------------------------------------
# spatial & synergy standalone
# --------------------------------------------------------------------------------------


def test_active_characters_in_room_excludes_suspended_and_dead():
    actor = WorldActor()
    room = _water_room(actor.world)
    live = _diver(actor.world, room, name="Live")
    suspended = _diver(actor.world, room, name="Zzz")
    suspended.add_component(SuspendedComponent())
    dead = _diver(actor.world, room, name="Gone")
    dead.add_component(DeadComponent(died_at_epoch=0, cause="test"))
    spawn_entity(actor.world, [IdentityComponent(name="thing", kind="item")])
    ids = [c.id for c in active_characters_in_room(actor.world, room)]
    assert ids == [live.id]
    assert active_characters_in_room(actor.world, None) == []
    # holder_of is None for a room-contained character, but resolves a carried item's holder.
    assert holder_of(actor.world, live.id) is None
    gear = spawn_dive_gear(actor.world)
    live.add_relationship(Contains(mode=ContainmentMode.INVENTORY), gear.id)
    assert holder_of(actor.world, gear.id).id == live.id


def test_synergy_is_off_and_neutral_without_partner_packs():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room)
    from bunnyland_aquasim import (
        fortune_available,
        hearth_available,
        museum_available,
        publish_collectible,
        publish_ingredient,
    )

    assert (museum_available(), hearth_available(), fortune_available()) == (False, False, False)
    assert read_luck(diver) == 0.0
    item = spawn_entity(actor.world, [IdentityComponent(name="pearl", kind="item")])
    assert publish_collectible(item, category="art", rarity="rare") is False
    assert publish_ingredient(item, tags=("fish",)) is False
