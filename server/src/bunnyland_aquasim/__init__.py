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
from .edges import (
    DiscoveredBy,
    PreysOn,
    credit_discovery,
    discoverer_id_of,
    prey_ids,
    prey_present,
)
from .enrichment import AquaWorldgenHook
from .gear import (
    GEAR_TIERS,
    DiveGearComponent,
    gear_fragments,
    gear_pressure_rating,
    gear_stats,
    held_dive_gear,
)
from .harvest import (
    HARVEST_ACTION_DEFINITIONS,
    HARVEST_ACTION_HANDLERS,
    HarvestedEvent,
    HarvestHandler,
    HarvestNodeComponent,
    harvest_fragments,
    luck_biased_index,
    luck_biased_loot,
)
from .install import install_aquasim
from .marinelife import (
    MarineAttackEvent,
    MarineLifeComponent,
    MarineThreatConsequence,
    is_threat,
    marine_life_in_room,
    marinelife_fragments,
)
from .plugin import PLUGIN_ID, bunnyland_plugins, plugin
from .prefabs import spawn_dive_gear, spawn_rebreather, spawn_treasure_cache
from .spatial import active_characters_in_room, holder_of, room_of
from .structures import (
    SURVEY_ACTION_DEFINITIONS,
    SURVEY_ACTION_HANDLERS,
    SiteDiscoveredEvent,
    StructureComponent,
    SurveyHandler,
    structure_fragments,
    structure_of_room,
)
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
from .synergy import (
    fortune_available,
    hearth_available,
    museum_available,
    publish_collectible,
    publish_ingredient,
    read_luck,
)

__all__ = [
    "AQUATIC_BIOMES",
    "DIVE_ACTION_DEFINITIONS",
    "DIVE_ACTION_HANDLERS",
    "GEAR_TIERS",
    "HARVEST_ACTION_DEFINITIONS",
    "HARVEST_ACTION_HANDLERS",
    "PLUGIN_ID",
    "SURVEY_ACTION_DEFINITIONS",
    "SURVEY_ACTION_HANDLERS",
    "AquaWorldgenHook",
    "BreathChangedEvent",
    "BreathComponent",
    "BreathConsequence",
    "CurrentComponent",
    "CurrentConsequence",
    "DiscoveredBy",
    "DiveGearComponent",
    "DiveHandler",
    "DriftedEvent",
    "DrowningEvent",
    "HarvestHandler",
    "HarvestNodeComponent",
    "HarvestedEvent",
    "HazardComponent",
    "HazardConsequence",
    "HazardStruckEvent",
    "MarineAttackEvent",
    "MarineLifeComponent",
    "MarineThreatConsequence",
    "PreysOn",
    "RebreatherComponent",
    "SiteDiscoveredEvent",
    "StructureComponent",
    "SubmergedComponent",
    "SurfaceHandler",
    "SurfacedEvent",
    "SurveyHandler",
    "SwimSkillComponent",
    "SwimSkillImprovedEvent",
    "TreasureCacheComponent",
    "TreasureRecoveredEvent",
    "active_characters_in_room",
    "breath_band",
    "breath_fragments",
    "bunnyland_plugins",
    "credit_discovery",
    "deterministic_loot",
    "discoverer_id_of",
    "fortune_available",
    "gear_fragments",
    "gear_pressure_rating",
    "gear_stats",
    "harvest_fragments",
    "hearth_available",
    "held_dive_gear",
    "held_rebreather",
    "holder_of",
    "improve_swim",
    "install_aquasim",
    "is_threat",
    "is_water_room",
    "luck_biased_index",
    "luck_biased_loot",
    "marine_life_in_room",
    "marinelife_fragments",
    "museum_available",
    "plugin",
    "prey_ids",
    "prey_present",
    "publish_collectible",
    "publish_ingredient",
    "read_luck",
    "room_depth",
    "room_of",
    "spawn_dive_gear",
    "spawn_rebreather",
    "spawn_treasure_cache",
    "structure_fragments",
    "structure_of_room",
    "submersion_fragments",
    "swim_drain_multiplier",
    "swim_fragments",
    "swim_hazard_multiplier",
    "swim_resists_current",
    "water_room_of",
]
