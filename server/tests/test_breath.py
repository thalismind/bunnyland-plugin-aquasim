from __future__ import annotations

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
    spawn_entity,
)
from bunnyland.mechanics.meter import Meter

from bunnyland_aquasim import (
    BreathChangedEvent,
    BreathComponent,
    BreathConsequence,
    DrowningEvent,
    SubmergedComponent,
    SwimSkillComponent,
    breath_band,
    breath_fragments,
    spawn_rebreather,
)

EPOCH = 100


def _water_room(world, *, depth=1.0):
    room = spawn_entity(world, [RoomComponent(title="Trench", biome="ocean")])
    room.add_component(SubmergedComponent(depth=depth))
    return room


def _dry_room(world):
    return spawn_entity(world, [RoomComponent(title="Beach", biome="meadow")])


def _diver(world, room, *, value=0.0, health=None, skill=None):
    components = [
        IdentityComponent(name="Vin", kind="character"),
        CharacterComponent(),
        BreathComponent(meter=Meter(value=value)),
    ]
    if health is not None:
        components.append(HealthComponent(current=health))
    if skill is not None:
        components.append(SwimSkillComponent(level=skill))
    character = spawn_entity(world, components)
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def _debt(character):
    return character.get_component(BreathComponent).meter.value


# -- bands ------------------------------------------------------------------------------


def test_breath_bands():
    assert breath_band(BreathComponent(meter=Meter(value=0.0))) == "calm"
    assert breath_band(BreathComponent(meter=Meter(value=50.0))) == "warning"
    assert breath_band(BreathComponent(meter=Meter(value=75.0))) == "urgent"
    assert breath_band(BreathComponent(meter=Meter(value=95.0))) == "crisis"


# -- drain / refill ---------------------------------------------------------------------


def test_submersion_drains_breath():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room, value=0.0)

    BreathConsequence().process(actor.world, EPOCH)

    assert _debt(diver) > 0.0


def test_deeper_water_drains_faster():
    actor = WorldActor()
    shallow = _water_room(actor.world, depth=1.0)
    deep = _water_room(actor.world, depth=3.0)
    shallow_diver = _diver(actor.world, shallow, value=0.0)
    deep_diver = _diver(actor.world, deep, value=0.0)

    BreathConsequence().process(actor.world, EPOCH)

    assert _debt(deep_diver) > _debt(shallow_diver)


def test_surface_refills_breath():
    actor = WorldActor()
    room = _dry_room(actor.world)
    diver = _diver(actor.world, room, value=50.0)

    BreathConsequence().process(actor.world, EPOCH)

    assert _debt(diver) < 50.0


def test_refill_clamps_at_zero():
    actor = WorldActor()
    room = _dry_room(actor.world)
    diver = _diver(actor.world, room, value=10.0)

    BreathConsequence().process(actor.world, EPOCH)

    assert _debt(diver) == 0.0


def test_rebreather_slows_the_drain():
    actor = WorldActor()
    bare_room = _water_room(actor.world)
    geared_room = _water_room(actor.world)
    bare = _diver(actor.world, bare_room, value=0.0)
    geared = _diver(actor.world, geared_room, value=0.0)
    rebreather = spawn_rebreather(actor.world, efficiency=0.75)
    geared.add_relationship(Contains(mode=ContainmentMode.INVENTORY), rebreather.id)

    BreathConsequence().process(actor.world, EPOCH)

    assert _debt(geared) < _debt(bare)


def test_swim_skill_slows_the_drain():
    actor = WorldActor()
    novice_room = _water_room(actor.world)
    expert_room = _water_room(actor.world)
    novice = _diver(actor.world, novice_room, value=0.0)
    expert = _diver(actor.world, expert_room, value=0.0, skill=5.0)

    BreathConsequence().process(actor.world, EPOCH)

    assert _debt(expert) < _debt(novice)


# -- drowning ---------------------------------------------------------------------------


def test_airless_diver_drowns_and_takes_damage():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room, value=95.0, health=100.0)

    events = BreathConsequence().process(actor.world, EPOCH)

    assert diver.get_component(HealthComponent).current < 100.0
    assert any(isinstance(event, DrowningEvent) for event in events)


def test_no_drowning_at_the_surface():
    actor = WorldActor()
    room = _dry_room(actor.world)
    diver = _diver(actor.world, room, value=95.0, health=100.0)

    events = BreathConsequence().process(actor.world, EPOCH)

    assert diver.get_component(HealthComponent).current == 100.0
    assert not any(isinstance(event, DrowningEvent) for event in events)


def test_drowning_clamps_health_at_zero():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room, value=95.0, health=1.0)

    BreathConsequence().process(actor.world, EPOCH)

    assert diver.get_component(HealthComponent).current == 0.0


def test_dead_diver_does_not_drown_again():
    actor = WorldActor()
    room = _water_room(actor.world)
    _diver(actor.world, room, value=95.0, health=0.0)

    events = BreathConsequence().process(actor.world, EPOCH)

    assert not any(isinstance(event, DrowningEvent) for event in events)


# -- excluded characters ----------------------------------------------------------------


def test_suspended_diver_is_skipped():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room, value=0.0)
    diver.add_component(SuspendedComponent())

    BreathConsequence().process(actor.world, EPOCH)

    assert _debt(diver) == 0.0


def test_dead_diver_is_skipped():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room, value=0.0)
    diver.add_component(DeadComponent(died_at_epoch=EPOCH, cause="drowned"))

    BreathConsequence().process(actor.world, EPOCH)

    assert _debt(diver) == 0.0


def test_diver_without_a_room_is_unchanged():
    actor = WorldActor()
    diver = spawn_entity(
        actor.world,
        [
            IdentityComponent(name="drifter", kind="character"),
            CharacterComponent(),
            BreathComponent(meter=Meter(value=20.0)),
        ],
    )

    BreathConsequence().process(actor.world, EPOCH)

    assert _debt(diver) < 20.0  # treated as surfaced (no water room) -> refills


# -- events -----------------------------------------------------------------------------


def test_band_crossing_emits_event():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room, value=32.0)  # +12 -> 44, crosses calm->warning

    events = BreathConsequence().process(actor.world, EPOCH)

    assert any(
        isinstance(event, BreathChangedEvent) and event.band == "warning" for event in events
    )
    assert _debt(diver) == 44.0


def test_no_event_when_band_unchanged():
    actor = WorldActor()
    room = _water_room(actor.world)
    _diver(actor.world, room, value=0.0)  # 0 -> 12, still calm

    events = BreathConsequence().process(actor.world, EPOCH)

    assert not any(isinstance(event, BreathChangedEvent) for event in events)


# -- fragments --------------------------------------------------------------------------


def test_calm_diver_has_no_breath_fragment():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room, value=0.0)

    assert breath_fragments(actor.world, diver) == []


def test_urgent_diver_reads_burning_lungs():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room, value=75.0)

    assert breath_fragments(actor.world, diver) == ["Your lungs are burning."]


def test_breath_fragment_is_first_person_only():
    actor = WorldActor()
    room = _water_room(actor.world)
    diver = _diver(actor.world, room, value=75.0)
    from bunnyland.prompts.context import ComponentPromptContext, PromptPerspective

    other = _diver(actor.world, room, value=0.0)
    ctx = ComponentPromptContext.for_entity(
        actor.world, diver, perspective=PromptPerspective(viewer=other), room=room
    )
    assert diver.get_component(BreathComponent).prompt_fragments(ctx) == ()


def test_breath_fragment_empty_for_character_without_breath():
    actor = WorldActor()
    room = _water_room(actor.world)
    character = spawn_entity(
        actor.world, [IdentityComponent(name="npc", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)

    assert breath_fragments(actor.world, character) == []
