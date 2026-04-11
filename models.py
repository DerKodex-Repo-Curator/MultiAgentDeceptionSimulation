from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass(eq=True)
class Player:
    name: str
    role: Optional[str]         = None   # "spy" | "civilian"
    word: Optional[str]         = None
    clue: Optional[str]         = None   # one-word clue (Mode 1 & 2)
    statement: Optional[str]    = None   # one-sentence statement (Mode 2 only)
    suspicion: Optional[Any]    = None   # Player this agent suspects
    personality: Optional[str]  = None   # "aggressive" | "conservative" | "deceptive" | None
    agent: Optional[Any]        = None   # set after construction

    def __hash__(self):
        return hash(self.name)           # name is unique per game


@dataclass
class Players:
    members: list[Player]         = field(default_factory=list)
    alive:   list[Player]         = field(default_factory=list)
    votes:   dict[Player, Player] = field(default_factory=dict)