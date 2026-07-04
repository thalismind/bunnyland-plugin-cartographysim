# bunnyland-cartographysim (server plugin)

The out-of-tree Bunnyland plugin package `bunnyland_cartographysim`.

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
bunnyland serve --module bunnyland_cartographysim
```

`default_enabled=True`, so no `--plugin` flag is required once the module is imported.

## What it contributes

- **Components** — `MapComponent` (a field map recording charted rooms), `CompassComponent`
  (orients by exit direction), `LandmarkComponent` (a named place on a room), and the
  internal `TravelPlanComponent` (a queued fast-travel route).
- **A mapping consequence** (`MappingConsequence`) that stamps each field map's current room
  into the map every tick — title, biome, and known `ExitTo` edges — idempotently.
- **A fast-travel consequence** (`TravelConsequence`) that walks a planned route one hop per
  tick and stops cleanly if a charted edge disappears.
- **Prompt fragments** — `map_fragments` (charted-room tally), `compass_fragments` (exit
  headings), `landmark_fragments` (the current room's name), and `fog_fragments`
  (charted/uncharted status plus uncharted frontier exits).
- **A worldgen hook** (`CartographyWorldgenHook`) seeding natural landmarks onto generated
  rooms by biome/tags.
- **Two verbs** — `name-landmark` (pin a name to your room) and `travel-to` (route to a
  charted room over known exits) — usable by the holder (human or AI). Emit
  `LandmarkNamedEvent`, `TravelStartedEvent`, `TravelStepEvent`, and `TravelArrivedEvent`.
- **Spawn factories** — `spawn_field_map`, `spawn_compass`.

## Reuses

The core room graph (`ExitTo` / `RoomComponent`), `reachable_ids`/containment helpers, and
per-character/per-item component state for map persistence. No new core surface is required.
