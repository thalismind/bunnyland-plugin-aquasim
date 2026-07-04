"""Water rooms and submersion (mechanic 1).

A room is *underwater* when it either carries an explicit
:class:`~bunnyland_aquasim.components.SubmergedComponent` or its
:class:`~bunnyland.core.RoomComponent` ``biome`` is one of the aquatic biomes. The rest of
the pack (breath drain, dive/surface, currents) asks the two questions this module answers:

- ``is_water_room(room)`` — is this room underwater?
- ``water_room_of(world, entity)`` — the water room an entity is in, or ``None``.

``room_depth`` gives a single scalar the breath and loot logic scale against.
"""

from __future__ import annotations

from bunnyland.core import RoomComponent
from relics import Entity, World

from .components import SubmergedComponent
from .spatial import room_of

#: Room biomes that count as underwater even without an explicit ``SubmergedComponent``.
AQUATIC_BIOMES: frozenset[str] = frozenset(
    {
        "ocean",
        "sea",
        "lake",
        "river",
        "reef",
        "underwater",
        "abyss",
        "lagoon",
        "flooded",
    }
)

#: Depth assumed for an aquatic-biome room that lacks an explicit ``SubmergedComponent``.
DEFAULT_DEPTH = 1.0


def is_water_room(room: Entity | None) -> bool:
    """True when ``room`` is underwater (submerged tag or an aquatic biome)."""
    if room is None:
        return False
    if room.has_component(SubmergedComponent):
        return True
    if room.has_component(RoomComponent):
        return room.get_component(RoomComponent).biome in AQUATIC_BIOMES
    return False


def room_depth(room: Entity | None) -> float:
    """Depth scalar for a water room (``0.0`` for dry land)."""
    if room is None:
        return 0.0
    if room.has_component(SubmergedComponent):
        return room.get_component(SubmergedComponent).depth
    if is_water_room(room):
        return DEFAULT_DEPTH
    return 0.0


def water_room_of(world: World, entity_id) -> Entity | None:
    """Return the water room ``entity_id`` is in, or ``None`` if it is on dry land."""
    room = room_of(world, entity_id)
    return room if is_water_room(room) else None


def submersion_fragments(world: World, character: Entity) -> list[str]:
    """Tell a character standing in a water room that they are submerged."""
    if character is None:
        return []
    room = room_of(world, character.id)
    if not is_water_room(room):
        return []
    return ["You are underwater; the light dims and the pressure builds."]


__all__ = [
    "AQUATIC_BIOMES",
    "DEFAULT_DEPTH",
    "is_water_room",
    "room_depth",
    "submersion_fragments",
    "water_room_of",
]
