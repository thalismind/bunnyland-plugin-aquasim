"""Optional, lazily imported Bunnyland 3D presentation integration."""

from __future__ import annotations

from pathlib import Path

from bunnyland.core import GenerationIntentComponent, RoomComponent

from .submersion import is_water_room

ASSET_ROOT = Path(__file__).with_name("assets")
REEF_TERMS = ("reef", "lagoon", "coral")


def water_room(room) -> bool:
    return is_water_room(room)


def reef_room(room) -> bool:
    if not is_water_room(room) or not room.has_component(RoomComponent):
        return False
    component = room.get_component(RoomComponent)
    intent = (
        room.get_component(GenerationIntentComponent)
        if room.has_component(GenerationIntentComponent)
        else None
    )
    text = " ".join(
        (
            component.title,
            component.biome,
            intent.description if intent else "",
            intent.source_key if intent else "",
            *(intent.tags if intent else ()),
        )
    ).casefold()
    return any(term in text for term in REEF_TERMS)


def install_aquasim_3d(actor, context) -> None:
    if context.plugins is None or not context.plugins.enabled("bunnyland.3d"):
        return
    from bunnyland_3d import (
        AssetSource,
        ModelAsset,
        RoomDecorationRule,
        register_models,
        register_room_decorations,
    )

    register_models(
        actor,
        "bunnyland.aquasim",
        (
            ModelAsset(
                key="bunnyland.aquasim/aquatic-plants",
                source=AssetSource(ASSET_ROOT, "aquatic-plants.obj"),
                instanced=True,
                license="AGPL-3.0-or-later",
                attribution="Bunnyland Aquasim contributors",
            ),
            ModelAsset(
                key="bunnyland.aquasim/coral-cluster",
                source=AssetSource(ASSET_ROOT, "coral-cluster.obj"),
                instanced=True,
                license="AGPL-3.0-or-later",
                attribution="Bunnyland Aquasim contributors",
            ),
        ),
    )
    register_room_decorations(
        actor,
        "bunnyland.aquasim",
        (
            RoomDecorationRule(
                key="bunnyland.aquasim/aquatic-plants",
                model_key="bunnyland.aquasim/aquatic-plants",
                room_predicate=water_room,
                count=18,
                min_scale=0.65,
                max_scale=1.3,
                margin=1.8,
                tint="#367f68",
            ),
            RoomDecorationRule(
                key="bunnyland.aquasim/coral-clusters",
                model_key="bunnyland.aquasim/coral-cluster",
                room_predicate=reef_room,
                count=8,
                min_scale=0.7,
                max_scale=1.18,
                margin=2.4,
                tint="#d47772",
            ),
        ),
    )


__all__ = ["REEF_TERMS", "install_aquasim_3d", "reef_room", "water_room"]
