# Bunnyland Cartographysim

> **Explore. Chart. Never get lost again.**

Out-of-tree [Bunnyland](https://github.com/thalismind/bunnyland-server) plugin that turns the
world graph into something you can **map, name, and navigate**. It is the quality-of-life
pack every other expansion quietly benefits from — anglers chart fishing holes, bards
remember venues, ghost hunters map the haunted wing.

Five mechanics ship together:

- **Field map** — a carried `MapComponent` item that records every room its holder visits
  (title, biome, and the exits leading out). Unvisited rooms stay blank.
- **Compass** — a carried `CompassComponent` that names the current room's exits by
  direction, reusing each `ExitTo` edge's `direction`/`label`, so players and AI can orient
  without guessing.
- **Landmarks** — a `name-landmark` verb pins a memorable name (`LandmarkComponent`) to the
  room you stand in; anyone there reads it, and the worldgen hook seeds natural landmarks.
- **Fast travel** — a `travel-to` verb routes the character to any already-charted room along
  a shortest path of **known** exits (queued one hop per tick), rejecting unknown or
  unreachable destinations with exact reasons.
- **Fog of war** — unmapped rooms render as "uncharted", and the map shows which exits lead
  off its edge into the frontier.

This repo intentionally keeps all cartography work outside the main `bunnyland-server` repo.

## Layout

- `server/` - Python Bunnyland plugin package with the components, the mapping and
  fast-travel consequences, prompt fragments, a worldgen enrichment hook, the two player/AI
  verbs, spawn factories, and tests.

## Server Plugin

The plugin exposes `bunnyland_cartographysim.bunnyland_plugins()` and contributes:

- `MapComponent`, `CompassComponent`, `LandmarkComponent`, and the internal
  `TravelPlanComponent`.
- `MappingConsequence` - stamps each field map's current room into the map every tick,
  recording title, biome, and known exits.
- `TravelConsequence` - advances every fast-travelling character one hop per tick.
- `map_fragments`, `compass_fragments`, `landmark_fragments`, `fog_fragments` - render the
  map tally, compass headings, landmark names, and charted/uncharted status into prompts.
- `CartographyWorldgenHook` - seeds natural landmarks (peaks, ruins, crossroads, caverns,
  shrines) onto generated rooms by biome/tags.
- `name-landmark` and `travel-to` - verbs for the holder (human or AI).
- `spawn_field_map`, `spawn_compass` - spawn factories.

## Running

This package builds no containers. It is loaded into the stock server via `--module`:

```bash
bunnyland serve --module bunnyland_cartographysim
```

`default_enabled=True`, so no `--plugin` flag is required once the module is imported. The
`bunnyland_cartographysim` package must be importable by the server (installed into the
server's environment, or on `PYTHONPATH`).

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
