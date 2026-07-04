from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    IdentityComponent,
    WorldActor,
    spawn_entity,
)

from bunnyland_aquasim import (
    SwimSkillComponent,
    SwimSkillImprovedEvent,
    improve_swim,
    swim_drain_multiplier,
    swim_fragments,
    swim_hazard_multiplier,
    swim_resists_current,
)

EPOCH = 100


def _swimmer(world, *, level=0.0, experience=0.0):
    return spawn_entity(
        world,
        [
            IdentityComponent(name="Vin", kind="character"),
            CharacterComponent(),
            SwimSkillComponent(level=level, experience=experience),
        ],
    )


# -- multipliers ------------------------------------------------------------------------


def test_no_skill_gives_full_drain():
    assert swim_drain_multiplier(None) == 1.0
    assert swim_drain_multiplier(SwimSkillComponent(level=0.0)) == 1.0


def test_higher_skill_reduces_drain():
    weak = swim_drain_multiplier(SwimSkillComponent(level=1.0))
    strong = swim_drain_multiplier(SwimSkillComponent(level=4.0))
    assert strong < weak < 1.0


def test_drain_relief_is_capped():
    assert swim_drain_multiplier(SwimSkillComponent(level=100.0)) == 0.5


def test_mastery_resists_currents():
    assert not swim_resists_current(None)
    assert not swim_resists_current(SwimSkillComponent(level=1.0))
    assert swim_resists_current(SwimSkillComponent(level=3.0))


def test_mastery_halves_hazard_damage():
    assert swim_hazard_multiplier(None) == 1.0
    assert swim_hazard_multiplier(SwimSkillComponent(level=3.0)) == 0.5


# -- improvement ------------------------------------------------------------------------


def test_use_grants_experience_without_a_level():
    actor = WorldActor()
    swimmer = _swimmer(actor.world, level=0.0, experience=0.0)

    event = improve_swim(swimmer, epoch=EPOCH)

    assert event is None
    assert swimmer.get_component(SwimSkillComponent).experience == 1.0
    assert swimmer.get_component(SwimSkillComponent).level == 0.0


def test_enough_use_levels_up_and_emits_event():
    actor = WorldActor()
    swimmer = _swimmer(actor.world, level=0.0, experience=2.0)  # +1 -> 3 xp == one level

    event = improve_swim(swimmer, epoch=EPOCH)

    assert isinstance(event, SwimSkillImprovedEvent)
    assert event.level == 1.0
    assert swimmer.get_component(SwimSkillComponent).level == 1.0
    assert swimmer.get_component(SwimSkillComponent).experience == 0.0


def test_improve_swim_noop_without_component():
    actor = WorldActor()
    plain = spawn_entity(
        actor.world, [IdentityComponent(name="npc", kind="character"), CharacterComponent()]
    )
    assert improve_swim(plain, epoch=EPOCH) is None


# -- fragments --------------------------------------------------------------------------


def test_master_swimmer_reads_a_fragment():
    actor = WorldActor()
    swimmer = _swimmer(actor.world, level=5.0)
    assert swim_fragments(actor.world, swimmer) == [
        "You move through the water like you were born to it."
    ]


def test_novice_swimmer_has_no_fragment():
    actor = WorldActor()
    swimmer = _swimmer(actor.world, level=1.0)
    assert swim_fragments(actor.world, swimmer) == []


def test_swim_fragment_empty_for_character_without_skill():
    actor = WorldActor()
    plain = spawn_entity(
        actor.world, [IdentityComponent(name="npc", kind="character"), CharacterComponent()]
    )
    assert swim_fragments(actor.world, plain) == []
