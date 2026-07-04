# Bunnyland Aquasim

Out-of-tree [Bunnyland](https://github.com/thalismind/bunnyland-server) plugin that adds
**swimming, diving, and the underwater** — an expansion-pack-sized themed bundle of aquatic
mechanics. Water rooms are their own little survival puzzle: dive deep, hold your breath,
and surface with treasure. It is a natural companion to river-fording and fishing worlds.

The pack bundles five mechanics, each in its own module with its own tests:

- **Water rooms / submersion** — a `SubmergedComponent` tags a room as deep water; any room
  with an aquatic `RoomComponent.biome` also counts. Being submerged gates movement and
  drives the breath timer.
- **Breath + drowning** — a `BreathComponent` meter (built on the shared needs `Meter`)
  drains while submerged and refills at the surface; running out damages `HealthComponent`.
  A held `RebreatherComponent` stretches every breath.
- **Diving for treasure** — a `dive` verb recovers loot from sunk caches with **deterministic**
  loot tables (a hash of the cache id and world epoch — no randomness); `surface` swims up an
  exit to dry land and catches your breath. Diving rejects if you cannot swim or have no air.
- **Currents & hazards** — a `CurrentComponent` drifts swimmers toward an exit each tick; a
  `HazardComponent` bites the ungeared. Strong swimmers resist both.
- **Swim skill** — a `SwimSkillComponent` that improves with use, reducing breath drain and
  hazard damage and letting a master hold their ground against currents.

This repo intentionally keeps all aquatic work outside the main `bunnyland-server` repo.

## Layout

- `server/` — Python Bunnyland plugin package with the components, the breath / current /
  hazard consequences, prompt fragments, a worldgen enrichment hook, the `dive`/`surface`
  verbs, spawn factories, and tests.

## Server Plugin

The plugin exposes `bunnyland_aquasim.bunnyland_plugins()` and contributes:

- `SubmergedComponent`, `RebreatherComponent`, `TreasureCacheComponent`, `BreathComponent`,
  `SwimSkillComponent`, `CurrentComponent`, `HazardComponent`.
- `BreathConsequence` — drains/refills breath and drowns the airless each tick.
- `CurrentConsequence` and `HazardConsequence` — drift swimmers and damage the ungeared.
- `submersion_fragments`, `breath_fragments`, `swim_fragments` — prompt fragments.
- `AquaWorldgenHook` — floods aquatic generated rooms and sinks treasure caches.
- `dive` and `surface` — verbs for the diver (human or AI).
- `spawn_rebreather`, `spawn_treasure_cache` — spawn factories.

## Running

This package builds no containers. It is loaded into the stock server via `--module`:

```bash
bunnyland serve --module bunnyland_aquasim
```

`default_enabled=True`, so no `--plugin` flag is required once the module is imported. The
`bunnyland_aquasim` package must be importable by the server (installed into the server's
environment, or on `PYTHONPATH`).

## Development

Run server tests against a sibling `bunnyland-server` checkout (no install required —
`server/tests/conftest.py` puts both packages on `sys.path`). From `server/`:

```bash
uv run --project ../../bunnyland-server -m pytest
uv run --project ../../bunnyland-server ruff check src tests
```

See [`server/README.md`](server/README.md) for more detail.

## Contributing & Conduct

This plugin follows the Bunnyland project's
[contribution guidelines](CONTRIBUTING.md) and [code of conduct](CODE_OF_CONDUCT.md),
which point back to the `bunnyland-server` repository.

## License

Licensed under the GNU Affero General Public License v3.0. See [LICENSE](LICENSE).
