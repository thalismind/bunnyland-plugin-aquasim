"""Optional cross-pack connectors — detected once, and safe when a partner is absent.

aquasim is **standalone-first**: it is complete with no other pack loaded. Where a synergy
partner *is* present it interlocks, but always through a safe conditional import and never a
hard dependency (the plugin lists these packs under ``recommends``, not ``requires``):

- **museum** — treasure and pearls carry a :class:`CollectibleComponent` so the museum can
  exhibit them.
- **hearth** — edible harvest carries an :class:`IngredientComponent` so it can be cooked.
- **fortune** — dive/harvest loot is biased by the harvester's :class:`Luck` ``value``.

Each partner is probed **once at import**; if it is missing the feature simply switches off
and a warning is logged (per the disable-and-warn convention). Core hunger is *not* a
connector: harvested food carries the core :class:`FoodComponent`, so it always feeds
lifesim hunger with no partner required.

The Discovery connector (cartography) needs no import at all — aquasim just publishes its
own :class:`~bunnyland_aquasim.structures.SiteDiscoveredEvent` on the bus for a charting
pack to subscribe to.
"""

from __future__ import annotations

import logging

from relics import Entity

logger = logging.getLogger(__name__)


def _detect_collectible():
    try:
        from bunnyland_museumsim import CollectibleComponent
    except ImportError:
        logger.warning(
            "bunnyland_museumsim not loaded; aquasim treasure and pearls will not be "
            "published as museum collectibles"
        )
        return None
    return CollectibleComponent


def _detect_ingredient():
    try:
        from bunnyland_hearthsim import IngredientComponent
    except ImportError:
        logger.warning(
            "bunnyland_hearthsim not loaded; aquasim edible harvest will not be tagged as "
            "cooking ingredients"
        )
        return None
    return IngredientComponent


def _detect_luck():
    try:
        from bunnyland_fortunesim import effective_luck
    except ImportError:
        logger.warning(
            "bunnyland_fortunesim not loaded; aquasim dive and harvest loot will not be "
            "biased by luck"
        )
        return None
    return effective_luck


#: Probed once at import. ``None`` means the partner is absent and the feature is off.
_COLLECTIBLE = _detect_collectible()
_INGREDIENT = _detect_ingredient()
_EFFECTIVE_LUCK = _detect_luck()


def museum_available() -> bool:
    """True when a museum pack is loaded and collectibles can be published."""
    return _COLLECTIBLE is not None


def hearth_available() -> bool:
    """True when a hearth pack is loaded and ingredients can be tagged."""
    return _INGREDIENT is not None


def fortune_available() -> bool:
    """True when a fortune pack is loaded and loot can be luck-biased."""
    return _EFFECTIVE_LUCK is not None


def publish_collectible(item: Entity, *, category: str, rarity: str) -> bool:
    """Tag ``item`` as a museum collectible when a museum pack is loaded."""
    if _COLLECTIBLE is None:
        return False
    item.add_component(_COLLECTIBLE(category=category, rarity=rarity))
    return True


def publish_ingredient(item: Entity, *, tags: tuple[str, ...]) -> bool:
    """Tag ``item`` as a cooking ingredient when a hearth pack is loaded."""
    if _INGREDIENT is None:
        return False
    item.add_component(_INGREDIENT(tags=tags))
    return True


def read_luck(character: Entity) -> float:
    """Return the character's materialised luck, or ``0.0`` when no fortune pack is loaded."""
    if _EFFECTIVE_LUCK is None:
        return 0.0
    return _EFFECTIVE_LUCK(character)


__all__ = [
    "fortune_available",
    "hearth_available",
    "museum_available",
    "publish_collectible",
    "publish_ingredient",
    "read_luck",
]
