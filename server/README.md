# bunnyland-aquasim (server plugin)

The out-of-tree Bunnyland plugin package `bunnyland_aquasim` (plugin id `bunnyland.aquasim`).

## Development

Tests run against a sibling `bunnyland-server` checkout without installing anything —
`tests/conftest.py` puts both this package's `src/` and `../bunnyland-server/src` on
`sys.path`. From this `server/` directory:

```bash
# uses the sibling bunnyland-server's virtualenv/deps
uv run --project ../../bunnyland-server -m pytest
# or, if bunnyland + relics are already importable:
python -m pytest
```

Lint:

```bash
uv run --project ../../bunnyland-server ruff check src tests
```

## Loading into the server

```bash
bunnyland serve --module bunnyland_aquasim
```

`default_enabled=True`, so no `--plugin` flag is required once the module is imported.

## What it contributes

Each mechanic lives in its own module with a matching `tests/test_*.py`:

- **Water rooms / submersion** (`submersion.py`) — `SubmergedComponent` marks a room as deep
  water; aquatic `RoomComponent.biome`s count too. `is_water_room`, `room_depth`, and
  `water_room_of` answer the questions the rest of the pack asks.
- **Breath + drowning** (`breath.py`) — `BreathComponent` reuses the shared needs `Meter`
  as *oxygen debt*: a per-tick `BreathConsequence` raises it underwater (scaled by depth,
  slowed by a held rebreather and by swim skill), lowers it at the surface, and applies
  `HealthComponent` damage once the debt maxes out. Emits `BreathChangedEvent` and
  `DrowningEvent`; `breath_fragments` render first-person burning-lungs lines.
- **Diving for treasure** (`diving.py`) — the `dive` and `surface` verbs. `deterministic_loot`
  picks a cache's reward from a hash of the cache id and world epoch, so there is no runtime
  randomness. Emits `TreasureRecoveredEvent` and `SurfacedEvent`.
- **Currents & hazards** (`currents.py`) — `CurrentComponent` drifts non-mastery swimmers
  toward an `ExitTo`; `HazardComponent` damages the ungeared. `CurrentConsequence` and
  `HazardConsequence` emit `DriftedEvent` and `HazardStruckEvent`.
- **Swim skill** (`swim.py`) — `SwimSkillComponent` improves via `improve_swim`, reducing
  breath drain and hazard damage and resisting currents at mastery. Emits
  `SwimSkillImprovedEvent`; `swim_fragments` render a first-person mastery line.

Shared surfaces: `components.py` (passive room/item/cache state), `spatial.py`
(`holder_of`/`room_of`), `enrichment.py` (`AquaWorldgenHook`), `prefabs.py`
(`spawn_rebreather`, `spawn_treasure_cache`), `install.py` (registers the consequences), and
`plugin.py` (the `Plugin` contribution).
