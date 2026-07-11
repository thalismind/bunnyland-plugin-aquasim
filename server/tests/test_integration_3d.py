from __future__ import annotations

import asyncio
import io
import sys

import pytest
from bunnyland.core import RoomComponent, WorldActor, spawn_entity
from bunnyland.foundation.media.plugin import plugin as media_plugin
from bunnyland.plugins import apply_plugins
from bunnyland.worldgen import RoomSpec, WorldProposal, instantiate

from bunnyland_aquasim.components import SubmergedComponent
from bunnyland_aquasim.integration_3d import reef_room, water_room
from bunnyland_aquasim.plugin import plugin as aqua_plugin


def _plugins_3d():
    from bunnyland_3d.plugin import plugin as plugin_3d

    return [media_plugin(), plugin_3d(), aqua_plugin()]


def _room(actor, spec):
    result = asyncio.run(instantiate(actor, WorldProposal(seed="seed", rooms=[spec])))
    return actor.world.get_entity(result.rooms[spec.key])


def test_plugin_stays_independent_when_3d_is_disabled():
    sys.modules.pop("bunnyland_3d", None)
    actor = WorldActor()

    apply_plugins([aqua_plugin()], actor)

    assert "bunnyland_3d" not in sys.modules
    assert aqua_plugin().dependencies.integrates_with == ("bunnyland.3d",)


@pytest.mark.parametrize("biome", ["ocean", "lake", "river", "abyss"])
def test_water_predicate_accepts_aquatic_rooms_without_implying_a_reef(biome):
    actor = WorldActor()
    apply_plugins([aqua_plugin()], actor)
    room = _room(actor, RoomSpec(key=biome, title=biome.title(), biome=biome))

    assert water_room(room)
    assert not reef_room(room)


def test_reef_predicate_reads_biome_and_generation_text_and_dry_rooms_are_rejected():
    actor = WorldActor()
    apply_plugins([aqua_plugin()], actor)
    reef = _room(actor, RoomSpec(key="reef", title="Reef", biome="reef"))
    grotto = _room(
        actor,
        RoomSpec(key="grotto", title="Grotto", description="a flooded coral grotto"),
    )
    dry = _room(actor, RoomSpec(key="meadow", title="Coral Gallery", biome="meadow"))
    explicit = spawn_entity(
        actor.world,
        [RoomComponent(title="Flooded Cave", biome="cavern"), SubmergedComponent()],
    )

    assert reef_room(reef)
    assert reef_room(grotto)
    assert not water_room(dry)
    assert not reef_room(dry)
    assert water_room(explicit)
    assert not reef_room(explicit)


def test_models_convert_and_grouped_water_room_projection_is_stable(tmp_path, monkeypatch):
    trimesh = pytest.importorskip("trimesh")
    monkeypatch.setenv("BUNNYLAND_MEDIA_DIR", str(tmp_path / "media"))
    actor = WorldActor()
    apply_plugins(_plugins_3d(), actor)
    room = _room(actor, RoomSpec(key="reef", title="Sunken Reef", biome="reef"))

    from bunnyland_3d import HasDecoration3D, PropGroup3DComponent, require_model_registry
    from bunnyland_3d.api import room_scene_view

    registry = require_model_registry(actor)
    for key in ("bunnyland.aquasim/aquatic-plants", "bunnyland.aquasim/coral-cluster"):
        model = registry.models[key]
        data = registry.media.read("models3d", model.url.rsplit("/", 1)[1])
        assert len(trimesh.load_scene(io.BytesIO(data), file_type="glb").geometry) >= 2
        assert model.asset.source.resolve().is_relative_to(model.asset.source.root)

    groups = {
        edge.role: actor.world.get_entity(target).get_component(PropGroup3DComponent)
        for edge, target in room.get_relationships(HasDecoration3D)
        if edge.role.startswith("bunnyland.aquasim/")
    }
    first = room_scene_view(actor, str(room.id))
    second = room_scene_view(actor, str(room.id))
    plants = next(
        item
        for item in first["decorations"]
        if item.get("decoration_source3d", {}).get("role")
        == "bunnyland.aquasim/aquatic-plants"
    )["prop_group3d"]["instances"]

    assert groups["bunnyland.aquasim/aquatic-plants"].count == 18
    assert groups["bunnyland.aquasim/coral-clusters"].count == 8
    assert first == second
    assert all(
        min(
            instance["position"]["x"],
            instance["position"]["z"],
            16 - instance["position"]["x"],
            16 - instance["position"]["z"],
        )
        == pytest.approx(1.8)
        for instance in plants
    )
