import json
import csv
import random
from datetime import datetime
from pathlib import Path

from config import NUM_PLAYERS, COMM_MODE, PERSONALITIES
from models import Player, Players
from agents import LLMAgent
from game import assign_roles, assign_words, act


# ── Game setup ─────────────────────────────────────────────────────────────────

def setup_game(names: list[str]) -> Players:
    """Creates and fully initialises a fresh game instance."""
    game         = Players()
    game.members = [Player(name) for name in names]
    game.alive   = game.members.copy()
    game.votes   = {}

    for p in game.members:
        p.personality = random.choice(PERSONALITIES)
        p.agent       = LLMAgent(p)

    assign_roles(game)
    assign_words(game)
    return game


# ── Metric computation ─────────────────────────────────────────────────────────

def compute_metrics(roles: dict[str, str], personalities: dict[str, str], round_log: list[dict]) -> dict:
    """
    Computes research metrics from a single completed game.

    accuracy
        correct_votes / total_votes where correct = voted for a spy.

    spy_elimination_rounds
        [(spy_name, round)] for every spy that was caught.

    spy_survival_times
        [(spy_name, rounds_survived)] for every spy — caught or not.
        Caught spy: rounds_survived = elimination_round - 1
        Surviving spy: rounds_survived = total rounds played

    personality_vote_accuracy
        Per-personality accuracy breakdown:
        {"aggressive": {"correct": int, "total": int, "accuracy": float}, ...}
    """
    total_votes   = 0
    correct_votes = 0

    # Per-personality vote tracking
    personality_votes: dict[str, dict] = {
        p: {"correct": 0, "total": 0} for p in PERSONALITIES
    }

    spy_elimination_rounds: list[tuple[str, int]] = []
    spy_last_round: dict[str, int | None] = {
        name: None for name, role in roles.items() if role == "spy"
    }
    total_rounds = round_log[-1]["round"] if round_log else 0

    for round_record in round_log:
        rnd = round_record["round"]

        # ── Accuracy ──────────────────────────────────────────────────────────
        for voter_name, target_name in round_record["votes"].items():
            if voter_name == target_name:
                continue
            total_votes += 1
            is_correct   = int(roles.get(target_name) == "spy")
            correct_votes += is_correct

            # Per-personality breakdown
            p_type = personalities.get(voter_name)
            if p_type and p_type in personality_votes:
                personality_votes[p_type]["total"]   += 1
                personality_votes[p_type]["correct"] += is_correct

        # ── Spy elimination round ──────────────────────────────────────────
        if round_record["eliminated_role"] == "spy":
            elim_name = round_record["eliminated"]
            spy_elimination_rounds.append((elim_name, rnd))
            spy_last_round[elim_name] = rnd

    accuracy = correct_votes / total_votes if total_votes > 0 else 0.0

    # Finalise per-personality accuracy
    personality_vote_accuracy = {}
    for p_type, counts in personality_votes.items():
        t = counts["total"]
        personality_vote_accuracy[p_type] = {
            "correct":  counts["correct"],
            "total":    t,
            "accuracy": round(counts["correct"] / t, 4) if t > 0 else 0.0,
        }

    # ── Spy survival times ─────────────────────────────────────────────────────
    spy_survival_times: list[tuple[str, int]] = []
    for spy_name, elim_round in spy_last_round.items():
        survived = (elim_round - 1) if elim_round is not None else total_rounds
        spy_survival_times.append((spy_name, survived))

    return {
        "accuracy":                round(accuracy, 4),
        "total_votes":             total_votes,
        "correct_votes":           correct_votes,
        "spy_elimination_rounds":  spy_elimination_rounds,
        "spy_survival_times":      spy_survival_times,
        "personality_vote_accuracy": personality_vote_accuracy,
    }


# ── Result persistence ─────────────────────────────────────────────────────────

def save_results(stats: dict, out_dir: str = "results") -> dict[str, str]:
    """
    Saves simulation results to four files inside `out_dir/`:
      - summary_<timestamp>.json          → high-level + aggregated metrics
      - rounds_<timestamp>.csv            → per-round detail
      - spy_metrics_<timestamp>.csv       → per-spy survival & elimination
      - personality_metrics_<timestamp>.csv → per-personality accuracy & survival
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    agg = stats["aggregated_metrics"]

    # ── JSON summary ───────────────────────────────────────────────────────────
    summary = {
        "timestamp":          ts,
        "comm_mode":          COMM_MODE,
        "num_players":        NUM_PLAYERS,
        "num_simulations":    stats["num_simulations"],
        "results":            stats["results"],
        "avg_rounds":         stats["avg_rounds"],
        "win_rates":          stats["win_rates"],
        "aggregated_metrics": {
            "overall_accuracy":            agg["overall_accuracy"],
            "avg_spy_survival_time":       agg["avg_spy_survival_time"],
            "avg_spy_elimination_round":   agg["avg_spy_elimination_round"],
            "spy_catch_rate":              agg["spy_catch_rate"],
            "personality_vote_accuracy":   agg["personality_vote_accuracy"],
            "personality_survival_rate":   agg["personality_survival_rate"],
        },
    }
    json_path = Path(out_dir) / f"summary_{ts}.json"
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)

    # ── CSV round log ──────────────────────────────────────────────────────────
    rounds_path  = Path(out_dir) / f"rounds_{ts}.csv"
    round_fields = [
        "sim", "round", "comm_mode",
        "player", "role", "personality", "word", "clue", "statement",
        "voted_for", "vote_correct",
        "eliminated", "eliminated_role", "winner",
    ]
    with open(rounds_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=round_fields)
        writer.writeheader()
        for sim_record in stats["sim_logs"]:
            sim_num       = sim_record["sim"]
            winner        = sim_record["winner"]
            roles         = sim_record["roles"]
            personalities = sim_record["personalities"]
            for round_record in sim_record["rounds"]:
                rnd       = round_record["round"]
                eliminated = round_record["eliminated"]
                elim_role  = round_record["eliminated_role"]
                for player_name, clue in round_record["clues"].items():
                    voted_for    = round_record["votes"].get(player_name, "")
                    vote_correct = int(roles.get(voted_for) == "spy") if voted_for else ""
                    writer.writerow({
                        "sim":             sim_num,
                        "round":           rnd,
                        "comm_mode":       COMM_MODE,
                        "player":          player_name,
                        "role":            roles.get(player_name, ""),
                        "personality":     personalities.get(player_name, ""),
                        "word":            sim_record["words"].get(player_name, ""),
                        "clue":            clue,
                        "statement":       round_record["statements"].get(player_name, ""),
                        "voted_for":       voted_for,
                        "vote_correct":    vote_correct,
                        "eliminated":      eliminated or "",
                        "eliminated_role": elim_role   or "",
                        "winner":          winner,
                    })

    # ── CSV spy metrics ────────────────────────────────────────────────────────
    spy_path   = Path(out_dir) / f"spy_metrics_{ts}.csv"
    spy_fields = [
        "sim", "comm_mode", "winner",
        "spy_name", "personality", "survival_time", "elimination_round", "caught",
    ]
    with open(spy_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=spy_fields)
        writer.writeheader()
        for sim_record in stats["sim_logs"]:
            sim_num       = sim_record["sim"]
            winner        = sim_record["winner"]
            metrics       = sim_record["metrics"]
            personalities = sim_record["personalities"]
            elim_map      = dict(metrics["spy_elimination_rounds"])
            for spy_name, survival_time in metrics["spy_survival_times"]:
                caught = spy_name in elim_map
                writer.writerow({
                    "sim":               sim_num,
                    "comm_mode":         COMM_MODE,
                    "winner":            winner,
                    "spy_name":          spy_name,
                    "personality":       personalities.get(spy_name, ""),
                    "survival_time":     survival_time,
                    "elimination_round": elim_map.get(spy_name, ""),
                    "caught":            int(caught),
                })

    # ── CSV personality metrics ────────────────────────────────────────────────
    pers_path   = Path(out_dir) / f"personality_metrics_{ts}.csv"
    pers_fields = [
        "sim", "comm_mode", "winner",
        "personality", "role",
        "survived",          # 1 if this player was alive at game end
        "vote_correct",      # 1 if this vote was correct (one row per vote)
        "voted_for_role",    # role of the player they voted for
    ]
    with open(pers_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=pers_fields)
        writer.writeheader()
        for sim_record in stats["sim_logs"]:
            sim_num        = sim_record["sim"]
            winner         = sim_record["winner"]
            roles          = sim_record["roles"]
            personalities  = sim_record["personalities"]
            survivors      = sim_record["survivors"]
            for round_record in sim_record["rounds"]:
                for voter_name, target_name in round_record["votes"].items():
                    if voter_name == target_name:
                        continue
                    writer.writerow({
                        "sim":            sim_num,
                        "comm_mode":      COMM_MODE,
                        "winner":         winner,
                        "personality":    personalities.get(voter_name, ""),
                        "role":           roles.get(voter_name, ""),
                        "survived":       int(voter_name in survivors),
                        "vote_correct":   int(roles.get(target_name) == "spy"),
                        "voted_for_role": roles.get(target_name, ""),
                    })

    return {
        "json":             str(json_path),
        "rounds_csv":       str(rounds_path),
        "spy_csv":          str(spy_path),
        "personality_csv":  str(pers_path),
    }


# ── Simulation runner ──────────────────────────────────────────────────────────

def run_simulation(n: int = 50, out_dir: str = "results") -> dict:
    """
    Runs n full game simulations, saves results, and returns aggregated stats.
    """
    results:     dict = {"spy": 0, "civilian": 0}
    sim_logs:    list = []
    rounds_list: list = []

    all_accuracies:         list[float] = []
    all_survival_times:     list[int]   = []
    all_elimination_rounds: list[int]   = []
    total_spies  = 0
    total_caught = 0

    # Personality aggregation across all sims
    # vote accuracy per personality
    agg_pers_votes: dict[str, dict] = {p: {"correct": 0, "total": 0} for p in PERSONALITIES}
    # survival tracking per personality
    agg_pers_survival: dict[str, dict] = {p: {"survived": 0, "total": 0} for p in PERSONALITIES}

    for sim in range(n):
        print(f"\n{'═' * 40}")
        print(f"  Simulation {sim + 1} / {n}  [{COMM_MODE}]")
        print(f"{'═' * 40}")

        game = setup_game(names=[f"A{i}" for i in range(1, NUM_PLAYERS + 1)])

        roles         = {p.name: p.role        for p in game.members}
        words         = {p.name: p.word        for p in game.members}
        personalities = {p.name: p.personality for p in game.members}

        winner, rounds, round_log = act(game)

        survivors     = {p.name for p in game.alive}   # snapshot after game ends
        result_label  = "spy" if "Spies" in winner else "civilian"
        results[result_label] += 1
        rounds_list.append(rounds)

        metrics = compute_metrics(roles, personalities, round_log)

        all_accuracies.append(metrics["accuracy"])
        for _, survival in metrics["spy_survival_times"]:
            all_survival_times.append(survival)
        for _, elim_round in metrics["spy_elimination_rounds"]:
            all_elimination_rounds.append(elim_round)
        total_spies  += len(metrics["spy_survival_times"])
        total_caught += len(metrics["spy_elimination_rounds"])

        # Aggregate personality vote accuracy
        for p_type, counts in metrics["personality_vote_accuracy"].items():
            agg_pers_votes[p_type]["correct"] += counts["correct"]
            agg_pers_votes[p_type]["total"]   += counts["total"]

        # Aggregate personality survival
        for p_name, p_type in personalities.items():
            if p_type in agg_pers_survival:
                agg_pers_survival[p_type]["total"]   += 1
                agg_pers_survival[p_type]["survived"] += int(p_name in survivors)

        sim_logs.append({
            "sim":          sim + 1,
            "winner":       result_label,
            "rounds":       round_log,
            "roles":        roles,
            "words":        words,
            "personalities": personalities,
            "survivors":    survivors,
            "metrics":      metrics,
        })

        # Per-sim console summary
        print(f"  Accuracy : {metrics['accuracy']:.1%}  "
              f"({metrics['correct_votes']}/{metrics['total_votes']} votes correct)")
        for spy_name, survival in metrics["spy_survival_times"]:
            elim   = dict(metrics["spy_elimination_rounds"]).get(spy_name)
            status = f"caught round {elim}" if elim else "survived to end"
            print(f"  {spy_name} ({personalities.get(spy_name, '?')}, spy): "
                  f"survived {survival} round(s) — {status}")
        for p_type, counts in metrics["personality_vote_accuracy"].items():
            print(f"  {p_type:14s}: {counts['accuracy']:.1%} accuracy "
                  f"({counts['correct']}/{counts['total']} votes)")

    avg_rounds = sum(rounds_list) / len(rounds_list) if rounds_list else 0

    # Finalise aggregated personality accuracy
    personality_vote_accuracy = {}
    for p_type, counts in agg_pers_votes.items():
        t = counts["total"]
        personality_vote_accuracy[p_type] = {
            "correct":  counts["correct"],
            "total":    t,
            "accuracy": round(counts["correct"] / t, 4) if t > 0 else 0.0,
        }

    # Finalise aggregated personality survival rate
    personality_survival_rate = {}
    for p_type, counts in agg_pers_survival.items():
        t = counts["total"]
        personality_survival_rate[p_type] = round(counts["survived"] / t, 4) if t > 0 else 0.0

    aggregated_metrics = {
        "overall_accuracy":          round(sum(all_accuracies) / len(all_accuracies), 4) if all_accuracies else 0,
        "avg_spy_survival_time":     round(sum(all_survival_times) / len(all_survival_times), 2) if all_survival_times else 0,
        "avg_spy_elimination_round": round(sum(all_elimination_rounds) / len(all_elimination_rounds), 2) if all_elimination_rounds else 0,
        "spy_catch_rate":            round(total_caught / total_spies, 4) if total_spies > 0 else 0,
        "personality_vote_accuracy": personality_vote_accuracy,
        "personality_survival_rate": personality_survival_rate,
    }

    stats = {
        "num_simulations":    n,
        "results":            results,
        "avg_rounds":         round(avg_rounds, 2),
        "win_rates":          {k: v / n for k, v in results.items()},
        "aggregated_metrics": aggregated_metrics,
        "sim_logs":           sim_logs,
    }

    saved_to          = save_results(stats, out_dir=out_dir)
    stats["saved_to"] = saved_to
    return stats