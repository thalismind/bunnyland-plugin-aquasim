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
        ParticleSystem3D,
        RoomDecorationRule,
        RoomParticleRule,
        RoomSkyboxRule,
        Skybox3D,
        register_models,
        register_particle_rules,
        register_particle_systems,
        register_room_decorations,
        register_skybox_rules,
        register_skyboxes,
    )

    owner = "bunnyland.aquasim"
    register_skyboxes(
        actor,
        owner,
        (
            Skybox3D(
                f"{owner}/underwater",
                zenith_color="#123f52",
                sky_color="#1b6572",
                horizon_color="#2f7f83",
                horizon_mix=0.72,
                sun_color="#9ddbd5",
                sun_x=0.5,
                sun_y=0.08,
                sun_size=0.08,
                sun_opacity=0.32,
                cloud_count=0,
            ),
        ),
    )
    register_particle_systems(
        actor,
        owner,
        (
            ParticleSystem3D(
                f"{owner}/suspended-silt",
                vertical_motion="drift",
                vertical_scale=0.05,
                lateral_wobble=0.12,
            ),
        ),
    )
    register_skybox_rules(
        actor,
        owner,
        (
            RoomSkyboxRule(
                f"{owner}/underwater-sky",
                f"{owner}/underwater",
                lambda _world, room: water_room(room),
                priority=100,
            ),
        ),
    )
    register_particle_rules(
        actor,
        owner,
        (
            RoomParticleRule(
                f"{owner}/suspended-silt-field",
                f"{owner}/suspended-silt",
                lambda _world, room: water_room(room),
                priority=100,
                count=80,
                height=4.0,
                margin=1.0,
                color="#a7d9cf",
                size=0.045,
                speed=0.08,
                opacity=0.35,
            ),
        ),
    )

    register_models(
        actor,
        owner,
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
        owner,
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
