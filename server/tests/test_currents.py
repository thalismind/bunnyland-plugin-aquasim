from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    DeadComponent,
    ExitTo,
    HealthComponent,
    IdentityComponent,
    RoomComponent,
    SuspendedComponent,
    WorldActor,
    spawn_entity,
)

from bunnyland_aquasim import (
    CurrentComponent,
    CurrentConsequence,
    DriftedEvent,
    HazardComponent,
    HazardConsequence,
    HazardStruckEvent,
    SwimSkillComponent,
    spawn_rebreather,
)
from bunnyland_aquasim.spatial import room_of

EPOCH = 100


def _room(world, title="Trench", biome="ocean"):
    return spawn_entity(world, [RoomComponent(title=title, biome=biome)])


def _character(world, room, *, skill=None, health=None):
    components = [IdentityComponent(name="Vin", kind="character"), CharacterComponent()]
    if skill is not None:
        components.append(SwimSkillComponent(level=skill))
    if health is not None:
        components.append(HealthComponent(current=health))
    character = spawn_entity(world, components)
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


# -- currents ---------------------------------------------------------------------------


def test_current_drifts_a_swimmer_to_the_exit():
    actor = WorldActor()
    here = _room(actor.world, title="Rip")
    there = _room(actor.world, title="Eddy")
    here.add_relationship(ExitTo(direction="east"), there.id)
    here.add_component(CurrentComponent(direction="east"))
    swimmer = _character(actor.world, here)

    events = CurrentConsequence().process(actor.world, EPOCH)

    assert room_of(actor.world, swimmer.id).id == there.id
    assert any(isinstance(event, DriftedEvent) for event in events)


def test_current_follows_its_named_direction():
    actor = WorldActor()
    here = _room(actor.world)
    north = _room(actor.world, title="North")
    south = _room(actor.world, title="South")
    here.add_relationship(ExitTo(direction="north"), north.id)
    here.add_relationship(ExitTo(direction="south"), south.id)
    here.add_component(CurrentComponent(direction="south"))
    swimmer = _character(actor.world, here)

    CurrentConsequence().process(actor.world, EPOCH)

    assert room_of(actor.world, swimmer.id).id == south.id


def test_current_falls_back_to_first_exit():
    actor = WorldActor()
    here = _room(actor.world)
    there = _room(actor.world, title="Anywhere")
    here.add_relationship(ExitTo(direction="west"), there.id)
    here.add_component(CurrentComponent(direction=""))
    swimmer = _character(actor.world, here)

    CurrentConsequence().process(actor.world, EPOCH)

    assert room_of(actor.world, swimmer.id).id == there.id


def test_master_swimmer_resists_the_current():
    actor = WorldActor()
    here = _room(actor.world)
    there = _room(actor.world, title="Eddy")
    here.add_relationship(ExitTo(direction="east"), there.id)
    here.add_component(CurrentComponent(direction="east"))
    swimmer = _character(actor.world, here, skill=5.0)

    CurrentConsequence().process(actor.world, EPOCH)

    assert room_of(actor.world, swimmer.id).id == here.id


def test_current_with_no_exit_does_nothing():
    actor = WorldActor()
    here = _room(actor.world)
    here.add_component(CurrentComponent(direction="east"))
    swimmer = _character(actor.world, here)

    assert CurrentConsequence().process(actor.world, EPOCH) == []
    assert room_of(actor.world, swimmer.id).id == here.id


def test_current_skips_suspended_swimmer():
    actor = WorldActor()
    here = _room(actor.world)
    there = _room(actor.world, title="Eddy")
    here.add_relationship(ExitTo(direction="east"), there.id)
    here.add_component(CurrentComponent(direction="east"))
    swimmer = _character(actor.world, here)
    swimmer.add_component(SuspendedComponent())

    CurrentConsequence().process(actor.world, EPOCH)

    assert room_of(actor.world, swimmer.id).id == here.id


# -- hazards ----------------------------------------------------------------------------


def test_hazard_damages_an_unprotected_character():
    actor = WorldActor()
    room = _room(actor.world)
    room.add_component(HazardComponent(damage=6.0, requires_gear=True))
    victim = _character(actor.world, room, health=100.0)

    events = HazardConsequence().process(actor.world, EPOCH)

    assert victim.get_component(HealthComponent).current < 100.0
    assert any(isinstance(event, HazardStruckEvent) for event in events)


def test_rebreather_wards_off_a_gear_hazard():
    actor = WorldActor()
    room = _room(actor.world)
    room.add_component(HazardComponent(damage=6.0, requires_gear=True))
    victim = _character(actor.world, room, health=100.0)
    rebreather = spawn_rebreather(actor.world)
    victim.add_relationship(Contains(mode=ContainmentMode.INVENTORY), rebreather.id)

    HazardConsequence().process(actor.world, EPOCH)

    assert victim.get_component(HealthComponent).current == 100.0


def test_gearless_hazard_ignores_gear():
    actor = WorldActor()
    room = _room(actor.world)
    room.add_component(HazardComponent(damage=6.0, requires_gear=False))
    victim = _character(actor.world, room, health=100.0)
    rebreather = spawn_rebreather(actor.world)
    victim.add_relationship(Contains(mode=ContainmentMode.INVENTORY), rebreather.id)

    HazardConsequence().process(actor.world, EPOCH)

    assert victim.get_component(HealthComponent).current < 100.0


def test_master_swimmer_takes_less_hazard_damage():
    actor = WorldActor()
    bare_room = _room(actor.world)
    expert_room = _room(actor.world)
    bare_room.add_component(HazardComponent(damage=6.0, requires_gear=False))
    expert_room.add_component(HazardComponent(damage=6.0, requires_gear=False))
    novice = _character(actor.world, bare_room, health=100.0)
    expert = _character(actor.world, expert_room, skill=5.0, health=100.0)

    HazardConsequence().process(actor.world, EPOCH)

    novice_loss = 100.0 - novice.get_component(HealthComponent).current
    expert_loss = 100.0 - expert.get_component(HealthComponent).current
    assert expert_loss < novice_loss


def test_hazard_clamps_health_at_zero():
    actor = WorldActor()
    room = _room(actor.world)
    room.add_component(HazardComponent(damage=6.0, requires_gear=False))
    victim = _character(actor.world, room, health=3.0)

    HazardConsequence().process(actor.world, EPOCH)

    assert victim.get_component(HealthComponent).current == 0.0


def test_hazard_skips_dead_character():
    actor = WorldActor()
    room = _room(actor.world)
    room.add_component(HazardComponent(damage=6.0, requires_gear=False))
    victim = _character(actor.world, room, health=100.0)
    victim.add_component(DeadComponent(died_at_epoch=EPOCH, cause="eel"))

    assert HazardConsequence().process(actor.world, EPOCH) == []
    assert victim.get_component(HealthComponent).current == 100.0
