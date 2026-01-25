# Processing Algorithm Pseudocode

## Overview

This document provides step-by-step algorithms for the main processing loops in the SC2 Replay Ground Truth Extraction Pipeline.

---

## Algorithm 1: Batch Processing (Main Entry Point)

```
FUNCTION run_batch_processing(replay_dir, output_dir, config):
    """
    Main entry point for batch processing multiple replays
    """

    # 1. INITIALIZATION
    PRINT "Initializing batch processing..."

    # Scan for replay files
    replay_paths = find_replays(replay_dir, pattern=config.file_pattern)
    total_replays = LENGTH(replay_paths)
    PRINT "Found {total_replays} replay files"

    # Create output directory
    CREATE_DIRECTORY(output_dir)

    # Validate configuration
    config.validate()

    # 2. SETUP MULTIPROCESSING
    PRINT "Setting up {config.num_workers} worker processes..."

    # Create queues for inter-process communication
    replay_queue = JoinableQueue(maxsize=config.num_workers * 10)
    stats_queue = Queue()

    # 3. START WORKER PROCESSES
    workers = []
    FOR i = 0 TO config.num_workers - 1:
        worker = ReplayProcessor(
            proc_id=i,
            replay_queue=replay_queue,
            stats_queue=stats_queue,
            output_dir=output_dir,
            config=config
        )
        worker.start()
        workers.APPEND(worker)
    END FOR

    # 4. START MONITORING THREADS

    # Thread 1: Fill replay queue
    queue_filler_thread = Thread(target=fill_replay_queue)
    queue_filler_thread.daemon = True
    queue_filler_thread.start(replay_queue, replay_paths)

    # Thread 2: Monitor progress
    stats_printer_thread = Thread(target=print_progress)
    stats_printer_thread.daemon = True
    stats_printer_thread.start(stats_queue, total_replays)

    # 5. WAIT FOR COMPLETION
    PRINT "Processing replays..."
    TRY:
        replay_queue.join()  # Wait for all replays to be processed
    EXCEPT KeyboardInterrupt:
        PRINT "Interrupted by user, cleaning up..."
        # Workers will exit gracefully

    # 6. CLEANUP
    PRINT "Shutting down workers..."
    FOR worker IN workers:
        worker.join(timeout=30)
    END FOR

    # 7. COLLECT FINAL STATISTICS
    final_stats = collect_statistics(stats_queue)

    # 8. GENERATE SUMMARY REPORT
    PRINT "\n=== BATCH PROCESSING COMPLETE ==="
    PRINT "Total replays: {final_stats.total}"
    PRINT "Processed: {final_stats.processed}"
    PRINT "Failed: {final_stats.failed}"
    PRINT "Skipped: {final_stats.skipped}"
    PRINT "Total time: {final_stats.duration} seconds"
    PRINT "Average time per replay: {final_stats.avg_time} seconds"

    RETURN final_stats
END FUNCTION


FUNCTION fill_replay_queue(replay_queue, replay_paths):
    """
    Thread function to fill replay queue
    """
    FOR replay_path IN replay_paths:
        replay_queue.put(replay_path)
    END FOR
END FUNCTION


FUNCTION print_progress(stats_queue, total_replays):
    """
    Thread function to monitor and print progress
    """
    processed = 0
    failed = 0
    start_time = CURRENT_TIME()

    WHILE True:
        # Wait for stats update (with timeout)
        TRY:
            stats = stats_queue.get(timeout=10)

            IF stats.status == "completed":
                processed += 1
            ELSE IF stats.status == "failed":
                failed += 1
            END IF

            # Print progress
            elapsed = CURRENT_TIME() - start_time
            percent = (processed + failed) / total_replays * 100
            rate = (processed + failed) / elapsed
            eta = (total_replays - processed - failed) / rate

            PRINT "[{elapsed:.0f}s] Progress: {processed}/{total_replays} ({percent:.1f}%) | "
                  "Failed: {failed} | Rate: {rate:.2f} replays/sec | ETA: {eta:.0f}s"

        EXCEPT Timeout:
            # No update in 10 seconds, just continue
            CONTINUE
        END TRY
    END WHILE
END FUNCTION
```

---

## Algorithm 2: Single Replay Processing (Worker Process)

```
CLASS ReplayProcessor(Process):
    """
    Worker process for processing individual replays
    """

    FUNCTION __init__(proc_id, replay_queue, stats_queue, output_dir, config):
        self.proc_id = proc_id
        self.replay_queue = replay_queue
        self.stats_queue = stats_queue
        self.output_dir = output_dir
        self.config = config
    END FUNCTION

    FUNCTION run():
        """
        Main worker loop - pulls replays from queue and processes them
        """

        PRINT "[Worker {self.proc_id}] Starting..."

        replays_processed = 0
        controller = NULL

        TRY:
            # Initialize SC2 controller
            run_config = get_run_config(version=config.sc2_version)
            interface = create_interface_options(raw=True, score=True)

            # Process replays until queue is empty
            WHILE True:
                # Get next replay from queue
                TRY:
                    replay_path = self.replay_queue.get(timeout=1)
                EXCEPT QueueEmpty:
                    BREAK  # No more replays
                END TRY

                # Process the replay
                start_time = CURRENT_TIME()
                success = False

                TRY:
                    # Start SC2 if needed (or restart every 300 replays)
                    IF controller == NULL OR replays_processed % 300 == 0:
                        IF controller != NULL:
                            controller.quit()
                        END IF
                        controller = run_config.start()
                    END IF

                    # Process based on strategy
                    IF config.strategy == "two_pass":
                        self.process_two_pass(replay_path, controller, interface)
                    ELSE:
                        self.process_single_pass(replay_path, controller, interface)
                    END IF

                    success = True
                    replays_processed += 1

                EXCEPT Exception AS e:
                    LOG_ERROR("[Worker {self.proc_id}] Failed to process {replay_path}: {e}")
                    success = False
                END TRY

                # Report status
                elapsed = CURRENT_TIME() - start_time
                self.stats_queue.put({
                    'worker_id': self.proc_id,
                    'replay': replay_path,
                    'status': 'completed' IF success ELSE 'failed',
                    'time': elapsed
                })

                # Mark task as done
                self.replay_queue.task_done()
            END WHILE

        FINALLY:
            # Cleanup
            IF controller != NULL:
                controller.quit()
            END IF
            PRINT "[Worker {self.proc_id}] Shutting down. Processed {replays_processed} replays."
        END FINALLY
    END FUNCTION
END CLASS
```

---

## Algorithm 3: Two-Pass Processing

```
FUNCTION process_two_pass(replay_path, controller, interface):
    """
    Process replay using two-pass strategy:
    Pass 1: Discover schema (max units/buildings)
    Pass 2: Extract data using fixed schema
    """

    # =======================
    # PASS 1: SCHEMA DISCOVERY
    # =======================

    PRINT "Pass 1: Scanning {replay_path} for schema..."

    # Load replay
    replay_data = load_replay_data(replay_path)
    replay_info = get_replay_info(replay_data)

    # Validate replay
    IF NOT validate_replay(replay_info, config):
        PRINT "Replay failed validation, skipping"
        RETURN False
    END IF

    # Initialize schema manager
    schema_manager = SchemaManager()

    # Process for Player 1
    PRINT "  Scanning player 1..."
    scan_player_for_schema(
        controller=controller,
        replay_data=replay_data,
        interface=interface,
        player_id=1,
        schema_manager=schema_manager
    )

    # Process for Player 2
    IF config.multi_player:
        PRINT "  Scanning player 2..."
        scan_player_for_schema(
            controller=controller,
            replay_data=replay_data,
            interface=interface,
            player_id=2,
            schema_manager=schema_manager
        )
    END IF

    # Generate schema from max counts
    schema = schema_manager.generate_schema(player_ids=[1, 2])
    PRINT "  Schema generated: {schema.column_count} columns"

    # =======================
    # PASS 2: DATA EXTRACTION
    # =======================

    PRINT "Pass 2: Extracting data..."

    # Initialize extractors
    state_extractor_p1 = StateExtractor(player_id=1)
    state_extractor_p2 = StateExtractor(player_id=2)
    wide_table_builder = WideTableBuilder(schema)

    # Extract data for Player 1
    PRINT "  Extracting player 1 data..."
    rows_p1 = extract_player_data(
        controller=controller,
        replay_data=replay_data,
        interface=interface,
        player_id=1,
        state_extractor=state_extractor_p1,
        schema=schema
    )

    # Extract data for Player 2
    rows_p2 = {}
    IF config.multi_player:
        PRINT "  Extracting player 2 data..."
        rows_p2 = extract_player_data(
            controller=controller,
            replay_data=replay_data,
            interface=interface,
            player_id=2,
            state_extractor=state_extractor_p2,
            schema=schema
        )
    END IF

    # =======================
    # MERGE & WRITE OUTPUT
    # =======================

    PRINT "  Merging player data..."

    # Merge player 1 and player 2 data by game_loop
    final_rows = []
    FOR loop IN SORTED(SET(rows_p1.keys()) UNION SET(rows_p2.keys())):
        row = {'game_loop': loop}

        # Add player 1 data
        IF loop IN rows_p1:
            row.UPDATE(rows_p1[loop])
        END IF

        # Add player 2 data
        IF loop IN rows_p2:
            row.UPDATE(rows_p2[loop])
        END IF

        final_rows.APPEND(row)
    END FOR

    PRINT "  Writing output..."

    # Convert to DataFrame
    df = DataFrame(final_rows)

    # Validate data
    IF config.validation.enabled:
        validate_data(df, schema)
    END IF

    # Write Parquet file
    output_path = generate_output_path(replay_path, output_dir)
    writer = ParquetWriter(compression=config.compression)
    writer.write_dataframe(
        df=df,
        output_path=output_path,
        metadata=create_metadata(replay_info, schema, config)
    )

    # Generate schema and dictionary files
    IF config.generate_schema:
        schema.to_json(output_path.replace('.parquet', '_schema.json'))
    END IF

    IF config.generate_dictionary:
        generate_data_dictionary(df, schema, replay_info, output_path)
    END IF

    PRINT "  Complete! Wrote {LENGTH(final_rows)} rows to {output_path}"
    RETURN True
END FUNCTION
```

---

## Algorithm 4: Schema Discovery (Single Player)

```
FUNCTION scan_player_for_schema(controller, replay_data, interface, player_id, schema_manager):
    """
    Scan replay to determine max unit/building counts
    """

    # Start replay
    controller.start_replay(
        replay_data=replay_data,
        options=interface,
        observed_player_id=player_id
    )

    # Initial step
    controller.step()

    # Iterate through all game loops
    WHILE True:
        # Get observation
        obs = controller.observe()

        # Check if game ended
        IF obs.player_result:
            BREAK
        END IF

        # Count units by type
        unit_counts = {}
        FOR unit IN obs.observation.raw_data.units:
            # Filter by player
            IF unit.owner == player_id OR unit.alliance == SELF:
                unit_type = unit.unit_type
                unit_counts[unit_type] = unit_counts.GET(unit_type, 0) + 1
            END IF
        END FOR

        # Count buildings by type
        building_counts = {}
        FOR unit IN obs.observation.raw_data.units:
            IF is_building(unit.unit_type) AND unit.owner == player_id:
                building_type = unit.unit_type
                building_counts[building_type] = building_counts.GET(building_type, 0) + 1
            END IF
        END FOR

        # Collect upgrades
        upgrades = SET(obs.observation.raw_data.player.upgrade_ids)

        # Update schema manager with max counts
        schema_manager.update_max_counts(
            player_id=player_id,
            unit_counts=unit_counts,
            building_counts=building_counts,
            upgrades=upgrades
        )

        # Step to next observation
        controller.step(config.step_mul)
    END WHILE

    # Cleanup
    controller.leave()
END FUNCTION
```

---

## Algorithm 5: Data Extraction (Single Player)

```
FUNCTION extract_player_data(controller, replay_data, interface, player_id, state_extractor, schema):
    """
    Extract complete data for one player
    """

    # Start replay
    controller.start_replay(
        replay_data=replay_data,
        options=interface,
        observed_player_id=player_id
    )

    # Initial step
    controller.step()

    # Storage for rows (keyed by game_loop)
    rows = {}

    # Iterate through all game loops
    WHILE True:
        # Get observation
        obs = controller.observe()

        # Check if game ended
        IF obs.player_result:
            BREAK
        END IF

        # Extract game loop
        game_loop = obs.observation.game_loop

        # Extract complete state
        state = state_extractor.extract(obs)

        # Build wide-format row
        row = build_wide_row(state, schema, player_id)

        # Store row
        rows[game_loop] = row

        # Step to next observation
        controller.step(config.step_mul)
    END WHILE

    # Cleanup
    controller.leave()

    RETURN rows
END FUNCTION
```

---

## Algorithm 6: State Extraction

```
FUNCTION extract_state(obs, player_id):
    """
    Extract all state components from observation
    """

    state = {
        'game_loop': obs.observation.game_loop,
        'units': {},
        'buildings': {},
        'economy': {},
        'upgrades': {}
    }

    # -----------------------
    # EXTRACT UNITS
    # -----------------------

    current_tags = SET()

    FOR unit IN obs.observation.raw_data.units:
        # Filter by alliance/owner
        IF unit.owner != player_id AND unit.alliance != SELF:
            CONTINUE
        END IF

        # Skip buildings
        IF is_building(unit.unit_type):
            CONTINUE
        END IF

        # Track tag
        current_tags.ADD(unit.tag)

        # Assign readable ID
        readable_id = assign_readable_id(unit.tag, unit.unit_type, player_id)

        # Determine state (built/existing/killed)
        unit_state = determine_unit_state(unit.tag, current_tags, previous_tags, dead_tags)

        # Extract unit data
        unit_data = {
            'tag': unit.tag,
            'readable_id': readable_id,
            'unit_type': unit.unit_type,
            'x': unit.pos.x,
            'y': unit.pos.y,
            'z': unit.pos.z,
            'health': unit.health,
            'health_max': unit.health_max,
            'shields': unit.shield,
            'shields_max': unit.shield_max,
            'energy': unit.energy,
            'energy_max': unit.energy_max,
            'state': unit_state
        }

        state['units'][readable_id] = unit_data
    END FOR

    # Update previous tags for next iteration
    previous_tags = current_tags
    dead_tags = SET(obs.observation.raw_data.event.dead_units)

    # -----------------------
    # EXTRACT BUILDINGS
    # -----------------------

    FOR unit IN obs.observation.raw_data.units:
        # Filter buildings only
        IF NOT is_building(unit.unit_type):
            CONTINUE
        END IF

        IF unit.owner != player_id:
            CONTINUE
        END IF

        # Assign readable ID
        readable_id = assign_readable_id(unit.tag, unit.unit_type, player_id)

        # Determine status
        building_status = determine_building_status(
            tag=unit.tag,
            build_progress=unit.build_progress,
            game_loop=obs.observation.game_loop,
            is_dead=unit.tag IN dead_tags
        )

        # Extract building data
        building_data = {
            'tag': unit.tag,
            'readable_id': readable_id,
            'building_type': unit.unit_type,
            'x': unit.pos.x,
            'y': unit.pos.y,
            'z': unit.pos.z,
            'status': building_status,
            'progress': unit.build_progress * 100.0,
            'started_loop': get_started_loop(unit.tag),
            'completed_loop': get_completed_loop(unit.tag),
            'destroyed_loop': get_destroyed_loop(unit.tag)
        }

        state['buildings'][readable_id] = building_data
    END FOR

    # -----------------------
    # EXTRACT ECONOMY
    # -----------------------

    state['economy'] = {
        'minerals': obs.observation.player_common.minerals,
        'vespene': obs.observation.player_common.vespene,
        'supply_used': obs.observation.player_common.food_used,
        'supply_cap': obs.observation.player_common.food_cap,
        'supply_workers': obs.observation.player_common.food_workers,
        'supply_army': obs.observation.player_common.food_army,
        'idle_workers': obs.observation.player_common.idle_worker_count,
        'army_count': obs.observation.player_common.army_count
    }

    # -----------------------
    # EXTRACT UPGRADES
    # -----------------------

    current_upgrades = SET(obs.observation.raw_data.player.upgrade_ids)

    FOR upgrade_id IN current_upgrades:
        upgrade_info = parse_upgrade(upgrade_id)
        upgrade_name = upgrade_info.name
        state['upgrades'][upgrade_name] = True
    END FOR

    RETURN state
END FUNCTION
```

---

## Algorithm 7: Wide Row Building

```
FUNCTION build_wide_row(state, schema, player_id):
    """
    Convert extracted state to wide-format row
    """

    # Initialize row with game_loop
    row = {'game_loop': state['game_loop']}

    # -----------------------
    # ADD UNIT COLUMNS
    # -----------------------

    FOR column IN schema.unit_columns:
        # Parse column name to get unit type and ID
        # e.g., "p1_marine_001_x" -> unit_type=marine, id=001, field=x
        parsed = parse_column_name(column)

        IF parsed.player_id != player_id:
            CONTINUE
        END IF

        # Find matching unit
        readable_id = f"p{player_id}_{parsed.unit_type}_{parsed.id}"

        IF readable_id IN state['units']:
            unit = state['units'][readable_id]
            row[column] = unit[parsed.field]
        ELSE:
            row[column] = NaN
        END IF
    END FOR

    # Add unit count columns
    unit_counts = count_by_type(state['units'])
    FOR unit_type, count IN unit_counts:
        column = f"p{player_id}_{unit_type}_count"
        row[column] = count
    END FOR

    # -----------------------
    # ADD BUILDING COLUMNS
    # -----------------------

    FOR column IN schema.building_columns:
        parsed = parse_column_name(column)

        IF parsed.player_id != player_id:
            CONTINUE
        END IF

        readable_id = f"p{player_id}_{parsed.building_type}_{parsed.id}"

        IF readable_id IN state['buildings']:
            building = state['buildings'][readable_id]
            row[column] = building[parsed.field]
        ELSE:
            row[column] = NaN
        END IF
    END FOR

    # Add building count columns
    building_counts = count_by_type(state['buildings'])
    FOR building_type, count IN building_counts:
        column = f"p{player_id}_{building_type}_count"
        row[column] = count
    END FOR

    # -----------------------
    # ADD ECONOMY COLUMNS
    # -----------------------

    FOR field, value IN state['economy']:
        column = f"p{player_id}_{field}"
        row[column] = value
    END FOR

    # -----------------------
    # ADD UPGRADE COLUMNS
    # -----------------------

    FOR column IN schema.upgrade_columns:
        parsed = parse_column_name(column)

        IF parsed.player_id != player_id:
            CONTINUE
        END IF

        upgrade_name = parsed.upgrade_name
        row[column] = state['upgrades'].GET(upgrade_name, False)
    END FOR

    RETURN row
END FUNCTION
```

---

## Algorithm 8: Unit Tag Management

```
# Global state (persists across frames within a replay)
tag_to_readable_id = {}
unit_type_counters = {}
previous_tags = SET()

FUNCTION assign_readable_id(tag, unit_type, player_id):
    """
    Assign human-readable ID to unit tag
    Maintains persistence - same tag always gets same ID
    """

    # Check if we've seen this tag before
    IF tag IN tag_to_readable_id:
        RETURN tag_to_readable_id[tag]
    END IF

    # New unit - assign sequential ID
    unit_name = get_unit_name(unit_type)
    counter = unit_type_counters.GET(unit_type, 1)

    readable_id = f"p{player_id}_{unit_name}_{counter:03d}"

    tag_to_readable_id[tag] = readable_id
    unit_type_counters[unit_type] = counter + 1

    RETURN readable_id
END FUNCTION


FUNCTION determine_unit_state(tag, current_tags, previous_tags, dead_tags):
    """
    Determine if unit was built/existing/killed this frame
    """

    IF tag IN dead_tags:
        RETURN "killed"
    ELSE IF tag IN current_tags AND tag NOT IN previous_tags:
        RETURN "built"
    ELSE:
        RETURN "existing"
    END IF
END FUNCTION
```

---

## Algorithm Summary

The complete pipeline flow:

```
1. Main Process
   ├─> Scan for replays
   ├─> Create worker processes
   ├─> Fill replay queue
   └─> Monitor progress

2. Worker Process (for each replay)
   ├─> PASS 1: Schema Discovery
   │   ├─> Load replay (Player 1)
   │   ├─> Iterate all loops
   │   ├─> Track max unit/building counts
   │   ├─> Load replay (Player 2)
   │   ├─> Iterate all loops
   │   ├─> Track max unit/building counts
   │   └─> Generate schema
   │
   ├─> PASS 2: Data Extraction
   │   ├─> Load replay (Player 1)
   │   ├─> For each loop:
   │   │   ├─> Extract state
   │   │   ├─> Build wide row
   │   │   └─> Store row
   │   ├─> Load replay (Player 2)
   │   ├─> For each loop:
   │   │   ├─> Extract state
   │   │   ├─> Build wide row
   │   │   └─> Store row
   │   └─> Merge player data by game_loop
   │
   └─> OUTPUT
       ├─> Convert to DataFrame
       ├─> Validate data
       ├─> Write Parquet file
       ├─> Generate schema file
       └─> Generate data dictionary

3. Report Results
```

---

## Key Algorithmic Principles

1. **Two-Pass Strategy**: Scan first to determine schema, then extract with fixed schema
2. **Tag Persistence**: Use uint64 tags from SC2 as ground truth IDs
3. **Set Operations**: Use set difference for detecting new/dead units
4. **Dictionary Mapping**: Map tags to readable IDs with persistent counters
5. **Sparse Representation**: Use NaN for missing units/buildings
6. **Batch Writing**: Buffer all rows in memory, write once to Parquet
7. **Process Isolation**: Each worker has independent SC2 instance
8. **Queue-Based Distribution**: Workers pull from shared queue

---

## Performance Characteristics

- **Time Complexity**: O(replays × loops × units)
- **Space Complexity**: O(loops × columns) per replay
- **Parallelization**: Linear scaling up to RAM limit
- **Memory per Worker**: ~2 GB (SC2) + buffer size
- **Bottleneck**: SC2 engine simulation speed

---

## Error Handling Points

Each algorithm includes try-except blocks at:
1. Replay loading
2. SC2 controller operations
3. State extraction
4. File writing
5. Validation

Failed operations log errors and continue processing (unless configured otherwise).
