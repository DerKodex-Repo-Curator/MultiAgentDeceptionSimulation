import random
from collections import Counter

from langchain_core.messages import HumanMessage

from config import get_llm, SYSTEM_PROMPT, CLUE_DICT, COMM_MODE
from models import Player, Players


def personality_str(player: Player) -> str:
    """Returns a behaviour instruction string for the LLM prompt."""
    descriptions = {
        "aggressive":   "You accuse quickly and take risks. Be bold in your suspicions.",
        "conservative": "You are cautious and think carefully before acting. Avoid rash accusations.",
        "deceptive":    "You are cunning and may mislead others. Blend in and deflect suspicion.",
    }
    return descriptions.get(player.personality, "You play neutrally.")


# ── Rule-based agent ───────────────────────────────────────────────────────────

class Agent:
    """Rule-based agent — uses clue frequency to vote."""

    def __init__(self, player: Player):
        self.player = player

    def give_clue(self, players: Players) -> str:
        self.player.clue = random.choice(CLUE_DICT[self.player.word])
        return self.player.clue

    def give_statement(self, players: Players) -> str:
        clues = [p.clue for p in players.alive if p.clue and p != self.player]
        if clues:
            self.player.statement = f"I think my clue fits well; '{clues[0]}' seems off to me."
        else:
            self.player.statement = "I am confident my clue is genuine."
        return self.player.statement

    def vote(self, players: Players) -> Player:
        clues       = {p: p.clue for p in players.alive}
        clue_counts = Counter(clues.values())
        suspicion   = {
            other: 1 / clue_counts[clues[other]]
            for other in players.alive
            if other != self.player
        }
        target                = max(suspicion, key=suspicion.get)
        self.player.suspicion = target
        return target


# ── LLM-backed agent ───────────────────────────────────────────────────────────

class LLMAgent(Agent):
    """LLM-backed agent — behaviour switches based on COMM_MODE in config."""

    # ── Clue ──────────────────────────────────────────────────────────────────

    def give_clue(self, players: Players) -> str:
        history = [p.clue for p in players.alive if p.clue]
        personality_line = (
            f"Your personality: {self.player.personality}\n"
            f"Behaviour: {personality_str(self.player)}\n"
            if self.player.personality else ""
        )
        prompt = f"""
You are playing a social deduction game.

Your role: {self.player.role}
Your word: {self.player.word}
{personality_line}
Give a ONE-WORD clue related to your word.
Do not reveal the word directly.
Do NOT repeat previous clues: {history}
Reply with ONLY the single word, nothing else.
"""
        response         = get_llm().invoke([SYSTEM_PROMPT, HumanMessage(content=prompt)])
        self.player.clue = response.content.strip().split()[0]
        return self.player.clue

    # ── Statement (Mode 2 only) ────────────────────────────────────────────────

    def give_statement(self, players: Players) -> str:
        clues_text = "\n".join(
            f"{p.name}: '{p.clue}'" for p in players.alive if p.clue
        )
        personality_line = (
            f"Your personality: {self.player.personality}\n"
            f"Behaviour: {personality_str(self.player)}\n"
            if self.player.personality else ""
        )
        prompt = f"""
You are playing a social deduction game.

Your role: {self.player.role}
Your word: {self.player.word}
Your clue: {self.player.clue}
{personality_line}
All clues given this round:
{clues_text}

Write ONE sentence (max 20 words) expressing your suspicion or defence.
Do NOT reveal your word or role directly.
Reply with ONLY that single sentence.
"""
        response              = get_llm().invoke([SYSTEM_PROMPT, HumanMessage(content=prompt)])
        self.player.statement = response.content.strip()
        return self.player.statement

    # ── Vote ──────────────────────────────────────────────────────────────────

    def vote(self, players: Players) -> Player:
        clues_text = "\n".join(
            f"{p.name} — clue: '{p.clue}'" for p in players.alive
        )
        if COMM_MODE == "clue_and_statement":
            statements_text = "\n".join(
                f"{p.name} — statement: \"{p.statement}\"" for p in players.alive if p.statement
            )
            context = f"Clues:\n{clues_text}\n\nStatements:\n{statements_text}"
        else:
            context = f"Clues:\n{clues_text}"

        personality_line = (
            f"Your personality: {self.player.personality}\n"
            f"Behaviour: {personality_str(self.player)}\n"
            if self.player.personality else ""
        )
        prompt = f"""
You are playing a social deduction game.

{personality_line}
{context}

One player is the spy. Based on the information above, who is most suspicious?
Reply ONLY with that player's name.
"""
        response = get_llm().invoke([SYSTEM_PROMPT, HumanMessage(content=prompt)])
        name     = response.content.strip()

        for p in players.alive:
            if p.name == name:
                return p

        # Fallback if LLM returns an unrecognised name
        return random.choice([p for p in players.alive if p != self.player])