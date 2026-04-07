"""
tmptest.py — Replay Seek Test

QUESTION BEING TESTED:
  Does the pysc2 API support seeking to an arbitrary game loop in replay mode?
  Specifically: if the SC2 engine has already computed and cached game state
  up to loop N, can we request an observation at loop M < N (backward seek)?

  pysc2's controller.observe() wraps RequestObservation which has a game_loop
  field. The s2client-proto spec says "if specified, the game will progress up
  to and including this step" — but if states are already cached in memory,
  "progress to" might mean "seek to" rather than "simulate forward to".

TEST PROCEDURE:
  Phase 1 — Baseline: step forward in coarse increments (22 game loops per
            sample) for 100 samples, recording a "fingerprint"
            (unit count + game_loop) at each sampled frame so we have ground
            truth to compare seeks against across a wider portion of the replay.

  Phase 2 — Forward seek past current position:
            From sample 100, request observe(target_game_loop=sample 200).
            Does the engine jump ahead to that target loop?

  Phase 3 — Backward seek: from wherever we are now, request
            observe(target_game_loop=sample 50).
            Does the engine return the state from that earlier sampled frame?
            Does the game_loop in the observation match the requested loop?
            Does the unit count match our Phase 1 fingerprint at sample 50?

  Phase 4 — Same-position seek: request observe(target_game_loop=current).
            Should always work as a sanity check.

VERDICT LOGIC:
  BACKWARD SEEK WORKS  → one SC2 instance can serve N worker processes with
                          near-instant frame access; multi-process extraction
                          architecture is feasible with minimal RAM overhead.
  BACKWARD SEEK FAILS  → N SC2 instances required for N-way parallelism;
                          RAM cost is unavoidable.

HOW TO RUN:
  cd SC2-gamestate-extractor
  ../.venv-3_11/Scripts/python.exe ../tmptest.py
"""

import sys
import logging
from pathlib import Path

# ── CONFIG ──────────────────────────────────────────────────────────────────
REPLAY_PATH = r"C:\Users\matae\AppData\Roaming\Code\User\globalStorage\stephanzlatarev.vscode-starcraft\replays\1_basic_bot_vs_loser_bot.SC2Replay"

# Number of game loops to advance between each sampled observation.
STEP_SIZE = 22

# Number of sampled observations to build in Phase 1.
BASELINE_SAMPLES = 100

# Sample index to seek FORWARD to (converted to target game loop via STEP_SIZE).
FORWARD_SAMPLE_TARGET = 200

# Sample index to seek BACKWARD to (converted to target game loop via STEP_SIZE).
BACKWARD_SAMPLE_TARGET = 50
# ────────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.WARNING)  # suppress pysc2 noise


def fingerprint(obs_response) -> dict:
    """
    Extract a minimal fingerprint from an observation to use as ground truth.

    Records game_loop and per-owner unit count so we can verify that a seek
    actually returned the state at the expected game loop rather than some
    other frame.

    Args:
        obs_response: ResponseObservation from controller.observe()

    Returns:
        Dict with 'game_loop', 'p1_units', 'p2_units', 'total_units'
    """
    obs = obs_response.observation
    raw_units = obs.raw_data.units
    return {
        'game_loop':   obs.game_loop,
        'p1_units':    sum(1 for u in raw_units if u.owner == 1),
        'p2_units':    sum(1 for u in raw_units if u.owner == 2),
        'total_units': len(raw_units),
    }


def seek_observe(controller, target_game_loop: int) -> tuple:
    """
    Attempt to observe at a specific game loop using RequestObservation.game_loop.

    pysc2's RemoteController.observe() accepts a target_game_loop kwarg that
    maps to RequestObservation.game_loop in the s2client-proto spec. We wrap
    it here to cleanly capture errors vs. success.

    Args:
        controller: pysc2 RemoteController instance
        target_game_loop: The game loop to seek to (or advance up to)

    Returns:
        Tuple of (success: bool, obs_response_or_None, error_str_or_None)

    Depends on / calls:
        - controller.observe(target_game_loop=N) from pysc2 RemoteController
    """
    try:
        obs_response = controller.observe(target_game_loop=target_game_loop)
        return True, obs_response, None
    except TypeError:
        # pysc2 version may not support target_game_loop kwarg —
        # fall back to building the request manually via the low-level client.
        try:
            from s2clientprotocol import sc2api_pb2 as sc_pb
            obs_response = controller._client.send(
                sc_pb.Request(
                    observation=sc_pb.RequestObservation(game_loop=target_game_loop)
                )
            )
            return True, obs_response, None
        except Exception as e:
            return False, None, f"low-level send failed: {e}"
    except Exception as e:
        return False, None, str(e)


def sample_to_game_loop(sample_idx: int) -> int:
    """Convert a coarse sample index into the corresponding target game loop."""
    return sample_idx * STEP_SIZE


def run_test():
    """
    Main test function. Runs all four phases and prints a clear verdict.

    Phase 1: step forward BASELINE_SAMPLES times, record fingerprint at each sample.
    Phase 2: attempt forward seek to FORWARD_SAMPLE_TARGET.
    Phase 3: attempt backward seek to BACKWARD_SAMPLE_TARGET.
    Phase 4: same-position seek as sanity check.
    """
    from absl import flags
    flags.FLAGS(["tmptest.py"])

    from pysc2 import run_configs
    from pysc2.lib import replay as sc2_replay
    from s2clientprotocol import sc2api_pb2 as sc_pb, common_pb2

    replay_path_abs = str(Path(REPLAY_PATH).resolve())

    print(f"\n{'='*65}")
    print("  REPLAY SEEK TEST")
    print(f"{'='*65}")
    print(f"  Replay         : {Path(REPLAY_PATH).name}")
    print(f"  Step size      : {STEP_SIZE} game loops/sample")
    print(f"  Baseline       : {BASELINE_SAMPLES} samples "
          f"(through loop {sample_to_game_loop(BASELINE_SAMPLES)})")
    print(f"  Forward seek   : sample {FORWARD_SAMPLE_TARGET} "
          f"(loop {sample_to_game_loop(FORWARD_SAMPLE_TARGET)})")
    print(f"  Backward seek  : sample {BACKWARD_SAMPLE_TARGET} "
          f"(loop {sample_to_game_loop(BACKWARD_SAMPLE_TARGET)})")
    print(f"{'='*65}\n")

    # ── Load replay ───────────────────────────────────────────────────────────
    initial_config = run_configs.get()
    replay_data = initial_config.replay_data(replay_path_abs)
    replay_version = sc2_replay.get_replay_version(replay_data)
    run_config = run_configs.get(version=replay_version)

    interface = sc_pb.InterfaceOptions(
        raw=True,
        score=True,
        show_cloaked=True,
        show_burrowed_shadows=True,
        show_placeholders=True,
    )

    with run_config.start(want_rgb=False) as controller:
        info = controller.replay_info(replay_data)
        print(f"Map: {info.map_name}  |  "
              f"Duration: {info.game_duration_loops} loops  |  "
              f"Players: {', '.join(common_pb2.Race.Name(p.player_info.race_actual) for p in info.player_info)}\n")

        controller.start_replay(sc_pb.RequestStartReplay(
            replay_data=replay_data,
            options=interface,
            observed_player_id=0,
            disable_fog=True,
            realtime=False,
        ))

        # ── PHASE 1: Build baseline fingerprints ─────────────────────────────
        print(f"[Phase 1] Stepping forward {BASELINE_SAMPLES} samples "
              f"(step size = {STEP_SIZE} game loops)...")
        baseline = {}  # sample_idx -> fingerprint dict

        for sample_idx in range(1, BASELINE_SAMPLES + 1):
            controller.step(STEP_SIZE)
            obs = controller.observe()
            if obs.player_result:
                print("  Game ended early — reduce BASELINE_SAMPLES or use a longer replay.")
                break
            fp = fingerprint(obs)
            baseline[sample_idx] = fp

        current_sample = max(baseline.keys()) if baseline else 0
        current_loop = baseline[current_sample]['game_loop'] if baseline else 0
        print(f"  Stepped to game_loop={current_loop}. "
              f"Recorded {len(baseline)} sampled fingerprints.\n")

        # Show a few sample fingerprints for reference
        sample_indices = sorted(baseline.keys())[::20]  # every 20th sample
        print(f"  Sample fingerprints (every 20th sample):")
        print(f"  {'sample':>8}  {'game_loop':>10}  {'p1_units':>8}  {'p2_units':>8}")
        print(f"  {'-'*8}  {'-'*10}  {'-'*8}  {'-'*8}")
        for sample_idx in sample_indices:
            fp = baseline[sample_idx]
            print(f"  {sample_idx:>8}  {fp['game_loop']:>10}  {fp['p1_units']:>8}  {fp['p2_units']:>8}")
        print()

        # ── PHASE 2: Forward seek ─────────────────────────────────────────────
        forward_target_loop = sample_to_game_loop(FORWARD_SAMPLE_TARGET)
        print(f"[Phase 2] Forward seek: requesting sample {FORWARD_SAMPLE_TARGET} "
              f"(game_loop={forward_target_loop}, currently at {current_loop})...")
        success, obs_fwd, err = seek_observe(controller, forward_target_loop)
        if success:
            fp_fwd = fingerprint(obs_fwd)
            print(f"  Requested : sample {FORWARD_SAMPLE_TARGET} (loop {forward_target_loop})")
            print(f"  Got       : game_loop={fp_fwd['game_loop']}  "
                  f"p1={fp_fwd['p1_units']}u  p2={fp_fwd['p2_units']}u")
            if fp_fwd['game_loop'] == forward_target_loop:
                print(f"  RESULT    : FORWARD SEEK WORKS — jumped directly to loop {forward_target_loop}")
            elif fp_fwd['game_loop'] > current_loop:
                print(f"  RESULT    : Partial forward — advanced to {fp_fwd['game_loop']} "
                      f"(not exactly {forward_target_loop})")
            else:
                print(f"  RESULT    : No movement — still at {fp_fwd['game_loop']}")
            current_loop = fp_fwd['game_loop']
        else:
            print(f"  RESULT    : ERROR — {err}")
        print()

        # ── PHASE 3: Backward seek ────────────────────────────────────────────
        backward_target_loop = sample_to_game_loop(BACKWARD_SAMPLE_TARGET)
        print(f"[Phase 3] Backward seek: requesting sample {BACKWARD_SAMPLE_TARGET} "
              f"(game_loop={backward_target_loop}, currently at {current_loop})...")

        if backward_target_loop >= current_loop:
            print(f"  SKIPPED — backward target loop ({backward_target_loop}) is not "
                  f"behind current loop ({current_loop}). Adjust config.")
        else:
            success, obs_bwd, err = seek_observe(controller, backward_target_loop)
            if success:
                fp_bwd = fingerprint(obs_bwd)
                print(f"  Requested : sample {BACKWARD_SAMPLE_TARGET} (loop {backward_target_loop})")
                print(f"  Got       : game_loop={fp_bwd['game_loop']}  "
                      f"p1={fp_bwd['p1_units']}u  p2={fp_bwd['p2_units']}u")

                # Check against baseline fingerprint if we have it
                if BACKWARD_SAMPLE_TARGET in baseline:
                    baseline_fp = baseline[BACKWARD_SAMPLE_TARGET]
                    unit_match = (fp_bwd['p1_units'] == baseline_fp['p1_units'] and
                                  fp_bwd['p2_units'] == baseline_fp['p2_units'])
                    loop_match = fp_bwd['game_loop'] == backward_target_loop
                    print(f"\n  Baseline at sample {BACKWARD_SAMPLE_TARGET} "
                          f"(loop {baseline_fp['game_loop']}): "
                          f"p1={baseline_fp['p1_units']}u  p2={baseline_fp['p2_units']}u")
                    print(f"  Loop match  : {loop_match}  "
                          f"({'exact' if loop_match else 'MISMATCH'})")
                    print(f"  Units match : {unit_match}  "
                          f"({'matches baseline' if unit_match else 'MISMATCH — different state'})")

                    if loop_match and unit_match:
                        print(f"\n  *** BACKWARD SEEK WORKS ***")
                        print(f"  The engine returned the exact cached state from loop {backward_target_loop}.")
                        print(f"  Single-instance multi-process architecture is FEASIBLE.")
                    elif loop_match and not unit_match:
                        print(f"\n  PARTIAL: Loop number matches but units differ.")
                        print(f"  Engine may have re-simulated from a keyframe (slightly off).")
                    else:
                        print(f"\n  BACKWARD SEEK FAILED: Got loop {fp_bwd['game_loop']}, "
                              f"not {backward_target_loop}.")
                        print(f"  The API does not support seeking backward.")
                        print(f"  Multi-process architecture requires N SC2 instances.")
                else:
                    # No baseline for this exact loop — just report what we got
                    if fp_bwd['game_loop'] < current_loop:
                        print(f"  Returned a loop BEHIND current position — backward seek likely works.")
                    elif fp_bwd['game_loop'] == current_loop:
                        print(f"  Returned current loop — seek was ignored.")
                    else:
                        print(f"  Returned a loop AHEAD of request — unexpected.")
            else:
                print(f"  RESULT : ERROR — {err}")
        print()

        # ── PHASE 4: Same-position seek (sanity check) ────────────────────────
        print(f"[Phase 4] Same-position seek sanity check "
              f"(requesting current loop {current_loop})...")
        success, obs_same, err = seek_observe(controller, current_loop)
        if success:
            fp_same = fingerprint(obs_same)
            match = fp_same['game_loop'] == current_loop
            print(f"  Requested : {current_loop}")
            print(f"  Got       : game_loop={fp_same['game_loop']}")
            print(f"  RESULT    : {'PASS — same-position seek works' if match else 'FAIL — unexpected loop returned'}")
        else:
            print(f"  RESULT    : ERROR — {err}")
        print()

        print(f"{'='*65}")
        print("  TEST COMPLETE")
        print(f"{'='*65}\n")


if __name__ == "__main__":
    run_test()
