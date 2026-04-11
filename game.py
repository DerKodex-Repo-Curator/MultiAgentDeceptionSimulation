import random
from collections import Counter
from typing import Optional

from config import NUM_SPIES, WORD_PAIRS, COMM_MODE
from models import Player, Players


# ── Role / word assignment ─────────────────────────────────────────────────────

def assign_roles(players: Players) -> Players:
    """Randomly designates spies; everyone else is a civilian."""
    spy_indices = set(random.sample(range(len(players.members)), NUM_SPIES))
    for i, player in enumerate(players.members):
        player.role = "spy" if i in spy_indices else "civilian"
    return players


def assign_words(players: Players) -> Players:
    """Gives civilians the civilian word and spies the spy word."""
    civilian_word, spy_word = random.choice(WORD_PAIRS)
    for player in players.members:
        player.word = spy_word if player.role == "spy" else civilian_word
    return players


# ── Per-round phases ───────────────────────────────────────────────────────────

def clue_phase(players: Players) -> Players:
    """Each alive player gives a one-word clue."""
    players.votes = {}
    for player in players.alive:
        player.statement = None          # reset statement each round
        player.agent.give_clue(players)
    return players


def statement_phase(players: Players) -> Players:
    """
    Mode 2 only — each alive player broadcasts one sentence after seeing
    all clues. Skipped entirely in 'clue_only' mode.
    """
    if COMM_MODE != "clue_and_statement":
        return players
    for player in players.alive:
        player.agent.give_statement(players)
    return players


def vote_phase(players: Players) -> Players:
    """Each alive player votes for who they suspect."""
    players.votes = {}
    for player in players.alive:
        players.votes[player] = player.agent.vote(players)
    return players


def eliminate(players: Players) -> Optional[Player]:
    """Eliminates the player with the most votes; returns them (or None)."""
    if not players.votes:
        return None
    count         = Counter(players.votes.values())
    eliminated    = count.most_common(1)[0][0]
    players.alive = [p for p in players.alive if p != eliminated]
    return eliminated


# ── Win condition ──────────────────────────────────────────────────────────────

def check_win(players: Players) -> Optional[str]:
    """Civilians win when all spies are gone; spies win when they match/outnumber civilians."""
    spies     = [p for p in players.alive if p.role == "spy"]
    civilians = [p for p in players.alive if p.role == "civilian"]

    if not spies:
        return "Civilians win!"
    if len(spies) >= len(civilians):
        return "Spies win!"
    return None


# ── Full game loop ─────────────────────────────────────────────────────────────

def act(players: Players) -> tuple[str, int, list[dict]]:
    """
    Runs a complete game until a winner is found.

    Returns (winner_string, round_count, round_log).

    round_log is a list of dicts — one per round — containing everything
    that happened (clues, statements, votes, elimination) for result storage.
    """
    for p in players.alive:
        print(f"  {p.name} ({p.role}) → word: {p.word}")

    round_log   = []
    round_count = 0

    while True:
        round_count += 1
        print(f"\n── Round {round_count} [{COMM_MODE}] ──────────────────────────")

        # Clue phase
        clue_phase(players)
        for p in players.alive:
            print(f"  {p.name} clue: '{p.clue}'")

        # Statement phase (Mode 2 only — no-op in Mode 1)
        statement_phase(players)
        if COMM_MODE == "clue_and_statement":
            for p in players.alive:
                print(f"  {p.name} says: \"{p.statement}\"")

        # Vote phase
        vote_phase(players)
        for voter, target in players.votes.items():
            print(f"  {voter.name} → {target.name}")

        # Elimination
        eliminated = eliminate(players)
        if eliminated:
            print(f"  ✗ {eliminated.name} eliminated (was {eliminated.role})")

        # Log this round
        round_log.append({
            "round":       round_count,
            "comm_mode":   COMM_MODE,
            "clues":       {p.name: p.clue      for p in players.alive},
            "statements":  {p.name: p.statement  for p in players.alive} if COMM_MODE == "clue_and_statement" else {},
            "votes":       {voter.name: target.name for voter, target in players.votes.items()},
            "eliminated":  eliminated.name if eliminated else None,
            "eliminated_role": eliminated.role if eliminated else None,
        })

        # Win check
        result = check_win(players)
        if result:
            print(f"\n  🏁 {result} (after {round_count} rounds)")
            return result, round_count, round_log

        print("  Round over — game continues.")