"""Out-of-tree Bunnyland plugin: swimming, diving, and the underwater.

An expansion-pack-sized themed bundle of aquatic mechanics: water rooms and submersion, a
breath meter with drowning, diving for deterministic treasure, currents and hazards, and a
swim skill that makes the deep safer with use.
"""

from .breath import (
    BreathChangedEvent,
    BreathComponent,
    BreathConsequence,
    DrowningEvent,
    breath_band,
    breath_fragments,
)
from .components import (
    RebreatherComponent,
    SubmergedComponent,
    TreasureCacheComponent,
    held_rebreather,
)
from .currents import (
    CurrentComponent,
    CurrentConsequence,
    DriftedEvent,
    HazardComponent,
    HazardConsequence,
    HazardStruckEvent,
)
from .diving import (
    DIVE_ACTION_DEFINITIONS,
    DIVE_ACTION_HANDLERS,
    DiveHandler,
    SurfacedEvent,
    SurfaceHandler,
    TreasureRecoveredEvent,
    deterministic_loot,
)
from .enrichment import AquaWorldgenHook
from .install import install_aquasim
from .plugin import PLUGIN_ID, bunnyland_plugins, plugin
from .prefabs import spawn_rebreather, spawn_treasure_cache
from .spatial import holder_of, room_of
from .submersion import (
    AQUATIC_BIOMES,
    is_water_room,
    room_depth,
    submersion_fragments,
    water_room_of,
)
from .swim import (
    SwimSkillComponent,
    SwimSkillImprovedEvent,
    improve_swim,
    swim_drain_multiplier,
    swim_fragments,
    swim_hazard_multiplier,
    swim_resists_current,
)

__all__ = [
    "AQUATIC_BIOMES",
    "DIVE_ACTION_DEFINITIONS",
    "DIVE_ACTION_HANDLERS",
    "PLUGIN_ID",
    "AquaWorldgenHook",
    "BreathChangedEvent",
    "BreathComponent",
    "BreathConsequence",
    "CurrentComponent",
    "CurrentConsequence",
    "DiveHandler",
    "DriftedEvent",
    "DrowningEvent",
    "HazardComponent",
    "HazardConsequence",
    "HazardStruckEvent",
    "RebreatherComponent",
    "SubmergedComponent",
    "SurfaceHandler",
    "SurfacedEvent",
    "SwimSkillComponent",
    "SwimSkillImprovedEvent",
    "TreasureCacheComponent",
    "TreasureRecoveredEvent",
    "breath_band",
    "breath_fragments",
    "bunnyland_plugins",
    "deterministic_loot",
    "held_rebreather",
    "holder_of",
    "improve_swim",
    "install_aquasim",
    "is_water_room",
    "plugin",
    "room_depth",
    "room_of",
    "spawn_rebreather",
    "spawn_treasure_cache",
    "submersion_fragments",
    "swim_drain_multiplier",
    "swim_fragments",
    "swim_hazard_multiplier",
    "swim_resists_current",
    "water_room_of",
]
