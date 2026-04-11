"""
Entry point — run a simulation batch.

To switch communication mode, change COMM_MODE in config.py:
  "clue_only"          → agents share one word only            (Mode 1)
  "clue_and_statement" → agents share one word + one sentence  (Mode 2)
"""
from simulation import setup_game, run_simulation
from config import NUM_PLAYERS, COMM_MODE


def main():
    print(f"\n  Communication mode: {COMM_MODE}")

    # ── Single game (uncomment to test one game quickly) ───────────────────────
    from game import act
    game = setup_game(names=[f"A{i}" for i in range(1, NUM_PLAYERS + 1)])
    winner, rounds, _ = act(game)
    print(f"\nResult: {winner} in {rounds} round(s)")

    # ── Simulation batch ───────────────────────────────────────────────────────
    # stats = run_simulation(n=100, out_dir="results")
    # agg   = stats["aggregated_metrics"]

    # print("\n\n══════════════ SIMULATION RESULTS ══════════════")
    # print(f"  Mode                    : {COMM_MODE}")
    # print(f"  Simulations             : {stats['num_simulations']}")
    # print(f"  Civilian wins           : {stats['results']['civilian']}")
    # print(f"  Spy wins                : {stats['results']['spy']}")
    # print(f"  Civilian win%           : {stats['win_rates']['civilian']:.1%}")
    # print(f"  Spy win%                : {stats['win_rates']['spy']:.1%}")
    # print(f"  Avg rounds per game     : {stats['avg_rounds']:.1f}")

    # print(f"\n  ── Vote Accuracy ────────────────────────────")
    # print(f"  Overall                 : {agg['overall_accuracy']:.1%}")
    # for p_type, counts in agg["personality_vote_accuracy"].items():
    #     print(f"  {p_type:14s}          : {counts['accuracy']:.1%}  ({counts['correct']}/{counts['total']})")

    # print(f"\n  ── Spy Metrics ──────────────────────────────")
    # print(f"  Spy catch rate          : {agg['spy_catch_rate']:.1%}")
    # print(f"  Avg spy survival (rnds) : {agg['avg_spy_survival_time']:.2f}")
    # print(f"  Avg elimination round   : {agg['avg_spy_elimination_round']:.2f}  (caught spies only)")

    # print(f"\n  ── Personality Survival Rate ────────────────")
    # for p_type, rate in agg["personality_survival_rate"].items():
    #     print(f"  {p_type:14s}          : {rate:.1%}")

    # print(f"\n  Results saved to:")
    # print(f"    JSON             → {stats['saved_to']['json']}")
    # print(f"    Rounds CSV       → {stats['saved_to']['rounds_csv']}")
    # print(f"    Spy CSV          → {stats['saved_to']['spy_csv']}")
    # print(f"    Personality CSV  → {stats['saved_to']['personality_csv']}")


if __name__ == "__main__":
    main()