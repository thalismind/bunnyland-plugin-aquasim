from __future__ import annotations

from bunnyland.core import (
    CharacterComponent,
    ContainmentMode,
    Contains,
    IdentityComponent,
    RoomComponent,
    WorldActor,
    spawn_entity,
)

from bunnyland_aquasim import (
    SubmergedComponent,
    is_water_room,
    room_depth,
    submersion_fragments,
    water_room_of,
)


def _room(world, *, biome="cavern", submerged=None):
    components = [RoomComponent(title="Room", biome=biome)]
    room = spawn_entity(world, components)
    if submerged is not None:
        room.add_component(SubmergedComponent(depth=submerged))
    return room


def _character(world, room):
    character = spawn_entity(
        world, [IdentityComponent(name="Vin", kind="character"), CharacterComponent()]
    )
    room.add_relationship(Contains(mode=ContainmentMode.ROOM_CONTENT), character.id)
    return character


def test_submerged_component_makes_a_water_room():
    actor = WorldActor()
    room = _room(actor.world, biome="cavern", submerged=2.0)
    assert is_water_room(room)
    assert room_depth(room) == 2.0


def test_aquatic_biome_is_a_water_room_without_tag():
    actor = WorldActor()
    room = _room(actor.world, biome="reef")
    assert is_water_room(room)
    assert room_depth(room) == 1.0


def test_dry_room_is_not_water():
    actor = WorldActor()
    room = _room(actor.world, biome="cavern")
    assert not is_water_room(room)
    assert room_depth(room) == 0.0


def test_none_room_is_not_water():
    assert not is_water_room(None)
    assert room_depth(None) == 0.0


def test_water_room_of_resolves_character_room():
    actor = WorldActor()
    room = _room(actor.world, biome="ocean")
    character = _character(actor.world, room)
    assert water_room_of(actor.world, character.id).id == room.id


def test_water_room_of_none_on_dry_land():
    actor = WorldActor()
    room = _room(actor.world, biome="meadow")
    character = _character(actor.world, room)
    assert water_room_of(actor.world, character.id) is None


def test_submersion_fragment_underwater():
    actor = WorldActor()
    room = _room(actor.world, biome="lagoon")
    character = _character(actor.world, room)
    lines = submersion_fragments(actor.world, character)
    assert lines == ["You are underwater; the light dims and the pressure builds."]


def test_no_submersion_fragment_on_dry_land():
    actor = WorldActor()
    room = _room(actor.world, biome="meadow")
    character = _character(actor.world, room)
    assert submersion_fragments(actor.world, character) == []


def test_submersion_fragment_empty_for_none_character():
    actor = WorldActor()
    assert submersion_fragments(actor.world, None) == []
