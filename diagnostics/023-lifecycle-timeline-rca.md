## Root Cause Analysis: Lifecycle Timeline Bugs

### Summary

Two compounding issues cause the lifecycle timeline anomalies: (1) the unit
extraction pipeline does not handle SC2 engine tag recycling, causing a single
entity's columns to absorb data from multiple physical units and producing
dozens of spurious "destroyed" events per entity; and (2) units almost never
exhibit a "started" lifecycle event in the parquet data because SC2 units appear
in the observation already complete (`build_progress >= 1.0`), so the expected
"started -> completed -> destroyed" sequence is inherently incomplete for units.

---

### Symptom 1: Missing Lifecycle Events

**Observation:** Entities show "completed -> destroyed" but never "started".
Buildings show "building_started -> completed -> destroyed" correctly, but
units never show `unit_started`.

**Root cause:** Two independent issues combine.

**Issue 1a -- `unit_started` is unreachable for most unit types (extraction pipeline)**

The `_determine_lifecycle()` method in `unit_extractor.py` (line 502) returns
`"unit_started"` only when a unit first appears with `build_progress == 0.0`.
In practice, the SC2 engine does not expose units to the observation until they
finish training and pop out of the production building. At that point,
`build_progress` is already `>= 1.0`, so `_determine_lifecycle()` returns
`"completed"` instead of `"unit_started"`. The `"unit_started"` state is
effectively dead code for standard-production units (marines, SCVs, zealots,
etc.).

Game-start units (the initial 12 SCVs/probes/drones) also appear at
`game_loop=1` with `build_progress >= 1.0`, so they too get `"completed"` on
their first frame, never `"unit_started"`.

Evidence:
- In `match_4184936`, all 41 SCV entities have `completed` at their first
  non-null game_loop. None ever show `unit_started`. The first 12 SCVs all show
  `completed` at `game_loop=1`.
- Marine entities also show `completed` on their first appearance (e.g.,
  `marine_001` at `game_loop=2660`).
- The only lifecycle strings that appear in the parquet data are:
  `building_started`, `completed`, `destroyed`. The strings `unit_started`,
  `building`, `existing`, `under_construction`, `started`, and `cancelled` are
  absent across all 5 test matches.

**Issue 1b -- `existing` and `under_construction` never appear as strings (by design)**

The `wide_table_builder.py` only writes lifecycle override strings for states
listed in `UNIT_LIFECYCLE_OVERRIDE_STATES` and `BUILDING_LIFECYCLE_OVERRIDE_STATES`.
The states `"existing"` and `"under_construction"` are NOT in these override
sets, so real numeric data is written instead of the state string. This is
correct behavior -- these are continuous states, not point-in-time events.
However, the notebook's `ALL_LIFECYCLE_STRINGS` includes both `"existing"` and
`"under_construction"`, which can never match any data in the parquet.

The notebook also includes the phantom string `"started"` (without any prefix),
which is never produced by either extractor. The extractors produce
`"unit_started"` and `"building_started"`, never bare `"started"`.

**Affected code:**

- `SC2-gamestate-extractor/src_new/extractors/unit_extractor.py`:
  `UnitExtractor._determine_lifecycle()` (line 502) -- the `unit_started`
  return path is unreachable for units that appear already complete.
- `SC2-gamestate-extractor/EDA/data_verification.ipynb`: cell 2 --
  `ALL_LIFECYCLE_STRINGS` contains strings that can never appear in the data
  (`started`, `existing`, `under_construction`).

**Recommended fix:**

1. **Notebook fix (cosmetic):** Remove `"started"`, `"existing"`, and
   `"under_construction"` from `ALL_LIFECYCLE_STRINGS` since they never appear
   in the parquet data. Add a comment explaining that `existing` and
   `under_construction` write real data rather than string markers.

2. **Extraction pipeline fix (if "started" events are desired):** Modify
   `unit_extractor._determine_lifecycle()` so that when a new unit appears with
   `build_progress >= 1.0`, it returns `"unit_started"` on that frame and
   `"completed"` on the next frame (requires a one-frame tracking buffer).
   Alternatively, accept that unit production is effectively instantaneous from
   the observer's perspective and document this in the notebook.

---

### Symptom 2: SCV Anomaly (many dots, empty-looking rows)

**Observation:** One SCV row has ~40+ dots (described as "completed" dots but
actually "destroyed" events rendered in red), with a lifespan bar spanning the
entire game. Adjacent SCV rows with only a single "completed" event have no
lifespan bar and appear nearly empty.

**Root cause:** SC2 engine tag recycling combined with the unit extractor's
failure to detect tag reuse.

**Detailed mechanism:**

1. The SC2 engine recycles unit tags. When an SCV dies and a new SCV is later
   produced, the new SCV can receive the same tag as the dead one.

2. In `unit_extractor.extract()` (line 277), when a unit tag appears in the
   observation, the extractor checks `tag not in self.tag_to_readable_id`. If
   the tag was previously seen (even if that unit died), the mapping already
   exists, so the extractor reuses the OLD readable_id (e.g., `scv_001`).

3. The recycled tag's unit data is then written to the same columns as the
   original entity. When the recycled-tag unit dies, another `"destroyed"`
   string is written to `scv_001`'s columns. This cycle repeats every time the
   tag is recycled.

4. Additionally, `_determine_lifecycle()` checks `tag in self.completed_tags`
   first. Since the original unit already completed, the recycled-tag unit
   immediately returns `"existing"` (real data written), skipping the
   `"completed"` event entirely. Then when it dies, `"destroyed"` is written
   again.

**Evidence from `match_4184936`:**

- `p1_veterran_another_scv_001` has 1 `completed` event at `game_loop=1` and
  74 `destroyed` events scattered from `game_loop=1580` to `game_loop=8847`.
- The state transitions show a repeating cycle every ~100 game_loops:
  `real -> destroyed -> null -> real -> destroyed -> null -> ...`
  This matches the pattern of: tag reuse (new SCV with same tag appears with
  real data), then dies (`destroyed`), then tag not in observation (`null`),
  then another reuse.
- Similar patterns exist for `scv_003` (76 destroyed), `scv_009` (77 destroyed),
  `scv_011` (75 destroyed), `scv_014` (76 destroyed), `scv_016` (73 destroyed).
- The 41 distinct SCV entities each have exactly 1 `completed` event, confirming
  the extractor assigns new readable_ids when a truly new tag appears, but reuses
  the old ID when a recycled tag appears.

**The "empty row" below:** SCVs that have only 1 lifecycle event (`completed`
at `game_loop=1`) are rendered with a single blue dot and no lifespan bar
(the bar requires `len(entity_events) >= 2`). Next to a heavily-dotted row
like `scv_001` (75 events total), a single-dot row appears visually empty by
comparison.

**Affected code:**

- `SC2-gamestate-extractor/src_new/extractors/unit_extractor.py`:
  `UnitExtractor.extract()` (line 277) -- does not detect tag recycling. Once a
  tag is in `tag_to_readable_id`, it is always reused, even after the unit dies.
- `SC2-gamestate-extractor/src_new/extractors/building_extractor.py`:
  `BuildingExtractor.extract()` (line 229) -- has the same tag-reuse
  vulnerability, though buildings are recycled less frequently in practice.

**Recommended fix:**

In `unit_extractor.extract()`, after detecting a dead unit (adding to
`dead_tags`), also remove the tag from `tag_to_readable_id` and
`completed_tags`. This way, when the SC2 engine recycles the tag for a new
unit, the extractor will treat it as a brand-new unit and assign a fresh
readable_id. Apply the same fix to `building_extractor.extract()`.

Specifically, add after the dead-unit detection block (around line 393):

```python
# Clean up dead tag mappings so recycled tags get fresh IDs
for dead_tag in disappeared_tags:
    if dead_tag in self.tag_to_readable_id:
        # ... existing destroyed handling ...
        # NEW: Remove tag mapping so recycled tags are treated as new units
        del self.tag_to_readable_id[dead_tag]
        self.completed_tags.discard(dead_tag)
        self.previous_build_progress.pop(dead_tag, None)
```

The same cleanup should be applied in the `dead_units` event check loop.

**Caution:** This fix changes the schema (more unique entities will be
discovered in Pass 1), which increases the number of columns in the parquet
output. Verify that the schema_manager and wide_table_builder handle the
increased entity count correctly.

---

### Additional Findings

1. **`ALL_LIFECYCLE_STRINGS` in the notebook contains phantom entries:**
   The string `"started"` (without prefix) is never produced by any extractor.
   The strings `"existing"` and `"under_construction"` are valid lifecycle
   states but are never written as string markers in the parquet (real data is
   written instead). These phantom entries don't cause bugs but are misleading
   when reading the code.

2. **`event_colors` dict has entries that are never rendered:**
   The `plot_entity_timeline()` function's `event_colors` dict includes mappings
   for `"building"`, `"started"`, and `"under_construction"`, none of which
   appear in the data. These are harmless but add dead code.

3. **Tag reuse affects data integrity beyond the timeline chart:**
   When tag recycling merges multiple physical units into one readable_id, the
   entity's attribute columns contain interleaved data from different physical
   units. This corrupts any analysis that relies on per-entity time series
   (e.g., health over time, position tracking).

4. **Destroyed event is repeated even without full tag recycling:**
   The `raw_data.event.dead_units` check in the extractor (lines 397-405)
   fires independently of the disappeared-tags check. If a tag appears in both
   `dead_units` AND `disappeared_tags`, it could be double-counted in the same
   frame. In practice, the `if readable_id not in units_data` guard prevents
   this, but the logic is fragile.

---

### Fix Priority

1. **First: Fix tag recycling in `unit_extractor.py` and
   `building_extractor.py`** -- This is the root cause of both data corruption
   (interleaved entity data) and the SCV anomaly (dozens of spurious destroyed
   events). All downstream issues (wrong timeline, wrong entity counts, wrong
   time series) stem from this.

2. **Second: Clean up `ALL_LIFECYCLE_STRINGS` in the notebook** -- Remove
   phantom entries (`"started"`, `"existing"`, `"under_construction"`) and
   unused `event_colors` entries. This is a cosmetic fix but reduces confusion.

3. **Third (optional): Add `unit_started` tracking** -- If the team wants
   "started -> completed -> destroyed" sequences for units, the extractor needs
   a mechanism to emit `unit_started` on the frame a unit first appears, even
   when `build_progress >= 1.0`. This is a design decision rather than a bug
   fix. The current behavior (units appear as `completed` immediately) is
   technically accurate from the observer API's perspective.

4. **After fixing tag recycling: Re-extract all parquet files** -- The existing
   parquet data contains corrupted entity columns from tag reuse. All downstream
   analysis should use freshly extracted data.
