"""Declarative submersion and treasure-cache generation enrichment."""

from bunnyland.core.generation import GenerationDelta, GenerationRequest

from .components import SubmergedComponent, TreasureCacheComponent
from .submersion import AQUATIC_BIOMES

WATER_TERMS = (
    "water",
    "underwater",
    "submerged",
    "flooded",
    "sunken",
    "sunk",
    "ocean",
    "sea",
    "lake",
    "river",
    "reef",
    "lagoon",
    "abyss",
    "deep",
    "tide",
    "current",
)
TREASURE_TERMS = (
    "treasure",
    "chest",
    "hoard",
    "trove",
    "loot",
    "wreck",
    "shipwreck",
    "cache",
    "coffer",
    "bounty",
)
DEFAULT_TABLE = (
    "a barnacled coin",
    "a pearl the size of an eye",
    "a rusted cutlass",
    "a coral-crusted locket",
)


def _text(request):
    return " ".join(
        (request.source_key, request.entity_kind, request.description, *request.tags)
    ).casefold()


class AquaGenerationEnricher:
    capabilities: tuple[str, ...] = ()

    def enrich(self, request: GenerationRequest) -> GenerationDelta:
        existing = tuple(request.context.get("base_components", ()))
        text = _text(request)
        if request.entity_kind == "room":
            room = next(
                (item for item in existing if item.__class__.__name__ == "RoomComponent"), None
            )
            biome = str(getattr(room, "biome", ""))
            if not any(isinstance(item, SubmergedComponent) for item in existing) and (
                biome in AQUATIC_BIOMES or any(term in text for term in WATER_TERMS)
            ):
                return GenerationDelta(components=(SubmergedComponent(),))
        elif not any(isinstance(item, TreasureCacheComponent) for item in existing) and any(
            term in text for term in TREASURE_TERMS
        ):
            return GenerationDelta(components=(TreasureCacheComponent(table=DEFAULT_TABLE),))
        return GenerationDelta()


__all__ = ["AquaGenerationEnricher", "DEFAULT_TABLE", "TREASURE_TERMS", "WATER_TERMS"]
