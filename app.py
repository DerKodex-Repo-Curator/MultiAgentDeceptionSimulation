"""
app.py — Streamlit GUI for the Social Deduction Simulation
Run:  streamlit run app.py
Place this file in the same directory as agents.py, config.py,
game.py, models.py, and simulation.py.
"""

import random
import importlib
import logging
from collections import Counter
import streamlit as st
import streamlit.components.v1 as components

logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(logging.ERROR)

st.set_page_config(page_title="Social Deduction Lab", page_icon="🕵️", layout="wide")

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono&display=swap');

.log-wrap {
    background: #0e0e16;
    border: 1px solid #3a3a5a;
    border-radius: 12px;
    padding: 20px 28px;
    height: 520px;
    overflow-y: auto;
    font-family: 'Space Mono', monospace;
    font-size: 13px;
    line-height: 1.6;
    color: #e4e1ff;
    margin-bottom: 20px;
}

.log-wrap .dim   { color: #7aa2f7; }
.log-wrap .hi    { color: #ffffff; font-weight: 700; }
.log-wrap .clue  { color: #f5c542; }
.log-wrap .stmt  { color: #c4b5fd; font-style: italic; }
.log-wrap .good  { color: #3de6b0; }
.log-wrap .bad   { color: #ff6b81; }
.log-wrap .sep   { color: #7aa2f7; }
.log-wrap .pers  { color: #c084fc; }
.log-wrap .word  { color: #38bdf8; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("🕵️ Social Deduction Lab")
st.sidebar.caption("Configure and run a game below.")
st.sidebar.divider()

num_players   = st.sidebar.number_input("Players",  min_value=4,  max_value=16, value=8)
num_spies     = st.sidebar.number_input("Spies",    min_value=1,  max_value=4,  value=2)
comm_mode     = st.sidebar.radio(
    "Communication Mode",
    ["clue_only", "clue_and_statement"],
    format_func=lambda x: "Clue Only" if x == "clue_only" else "Clue + Statement",
)
personalities = st.sidebar.multiselect(
    "Personalities",
    ["aggressive", "conservative", "deceptive"],
    default=["aggressive", "conservative", "deceptive"],
)
raw_names = st.sidebar.text_input("Player names", placeholder="A1, A2, A3 ... (optional)")

st.sidebar.divider()
run_btn   = st.sidebar.button("▶  Run Game", use_container_width=True, type="primary")
reset_btn = st.sidebar.button("↺  Reset",    use_container_width=True)


# ── Session state ─────────────────────────────────────────────────────────────
if "log_html" not in st.session_state:
    st.session_state.log_html = ""
if "done" not in st.session_state:
    st.session_state.done = False
if "stats" not in st.session_state:
    st.session_state.stats = None

if reset_btn:
    st.session_state.log_html = ""
    st.session_state.done     = False
    st.session_state.stats    = None
    st.rerun()


# ── Page header ───────────────────────────────────────────────────────────────
st.markdown("## 🕵️ Social Deduction Lab")
st.caption("A multi-agent social deduction experiment. Agents give clues, make statements, and vote to eliminate the spy.")
st.divider()

log_slot   = st.empty()
# FIX 1: Use a container for stats so multiple widgets (.divider, .columns) can coexist
stats_slot = st.container()

# ── Auto-scroll helper ────────────────────────────────────────────────────────
# FIX 2: st.markdown strips <script> tags — use components.html() instead
_SCROLL_JS = """
<script>
    // Target the scrollable log div inside the Streamlit iframe
    const logDiv = window.parent.document.querySelector('.log-wrap');
    if (logDiv) { logDiv.scrollTop = logDiv.scrollHeight; }
</script>
"""

def inject_scroll():
    """Inject JS that scrolls .log-wrap to the bottom. Height=0 keeps it invisible."""
    components.html(_SCROLL_JS, height=0)

# ── Render helpers ────────────────────────────────────────────────────────────
def render_log(scroll: bool = False):
    content = st.session_state.log_html or '<span class="dim">Game not started — hit ▶ Run Game in the sidebar.</span>'
    log_slot.markdown(
        f'<div class="log-wrap">{content}</div>',
        unsafe_allow_html=True,
    )
    if scroll:
        inject_scroll()

def render_stats():
    if not st.session_state.stats:
        return
    s = st.session_state.stats
    # FIX 1 cont.: write everything into the container — it supports multiple widgets
    with stats_slot:
        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Rounds Played", s["rounds"])
        c2.metric("Winner",        s["winner"])
        c3.metric("Vote Accuracy", f"{s['acc']:.0f}%")
        c4.metric("Spies Caught",  f"{s['caught']} / {s['total_spies']}")


# Initial render on page load / reruns
if st.session_state.log_html:
    render_log(scroll=False)   # don't auto-scroll on plain reruns
if st.session_state.stats:
    render_stats()


# ── Log helper ────────────────────────────────────────────────────────────────
# FIX 3: Use a single <br> instead of <br><br> to reduce spacing
def log(html: str, extra_gap: bool = False):
    """Append one line to the log and re-render with auto-scroll."""
    sep = "<br><br>" if extra_gap else "<br>"
    st.session_state.log_html += html + sep
    render_log(scroll=True)


# ── Run game ──────────────────────────────────────────────────────────────────
if run_btn:
    if not personalities:
        st.error("Select at least one personality.")
        st.stop()

    # Reset
    st.session_state.log_html = ""
    st.session_state.done     = False
    st.session_state.stats    = None

    names = (
        [n.strip() for n in raw_names.split(",") if n.strip()]
        if raw_names.strip()
        else [f"P{i}" for i in range(1, int(num_players) + 1)]
    )
    names = names[:int(num_players)]

    # Patch config
    import config as cfg
    cfg.NUM_PLAYERS   = int(num_players)
    cfg.NUM_SPIES     = int(num_spies)
    cfg.COMM_MODE     = comm_mode
    cfg.PERSONALITIES = list(personalities)

    import agents as ag_mod
    import game   as gm_mod
    importlib.reload(ag_mod)
    importlib.reload(gm_mod)

    from models import Player, Players

    # Build game
    game         = Players()
    game.members = [Player(name=n) for n in names]
    game.alive   = game.members.copy()
    game.votes   = {}

    for p in game.members:
        p.personality = random.choice(personalities)
        p.agent       = ag_mod.LLMAgent(p)

    gm_mod.assign_roles(game)
    gm_mod.assign_words(game)

    # Setup log — batch player rows so the header and list feel like one block
    lines = ['<span class="hi">── Setup ─────────────────────────────────────────────</span>']
    for p in game.members:
        role_tag = f'<span class="bad">spy</span>' if p.role == "spy" else f'<span class="good">civilian</span>'
        lines.append(f'&nbsp;&nbsp;<span class="hi">{p.name}</span>&nbsp;&nbsp;{role_tag}&nbsp;&nbsp;<span class="pers">{p.personality}</span>&nbsp;&nbsp;<span class="dim">·</span>&nbsp;&nbsp;<span class="word">{p.word}</span>')
    log("<br>".join(lines), extra_gap=True)

    # Game loop
    round_count   = 0
    total_votes   = 0
    correct_votes = 0
    spies_caught  = 0
    acc           = 0

    while True:
        round_count += 1
        mode_label = "Clue+Statement" if comm_mode == "clue_and_statement" else "Clue Only"
        log(f'<span class="hi">── Round {round_count} · {mode_label} ─────────────────────────────</span>', extra_gap=False)

        # Clues — collect all then log as one block
        game.votes = {}
        clue_lines = ['<span class="dim">&nbsp;&nbsp;Clues</span>']
        for p in game.alive:
            p.statement = None
            p.agent.give_clue(game)
            clue_lines.append(f'&nbsp;&nbsp;&nbsp;&nbsp;{p.name} → <span class="clue">{p.clue}</span>')
        log("<br>".join(clue_lines))

        # Statements — collect all then log as one block
        if comm_mode == "clue_and_statement":
            for p in game.alive:
                p.agent.give_statement(game)
            stmt_lines = ['<span class="dim">&nbsp;&nbsp;Statements</span>']
            for p in game.alive:
                stmt_lines.append(f'&nbsp;&nbsp;&nbsp;&nbsp;{p.name} · <span class="stmt">"{p.statement}"</span>')
            log("<br>".join(stmt_lines))

        # Votes
        game.votes = {}
        vote_lines = ['<span class="dim">&nbsp;&nbsp;Votes</span>']
        for p in game.alive:
            target = p.agent.vote(game)
            game.votes[p] = target
            correct        = target.role == "spy"
            total_votes   += 1
            correct_votes += int(correct)
            mark = '<span class="good">✓</span>' if correct else '<span class="bad">✗</span>'
            vote_lines.append(f'&nbsp;&nbsp;&nbsp;&nbsp;{p.name} → {target.name} {mark}')
        log("<br>".join(vote_lines))

        # Elimination
        count      = Counter(game.votes.values())
        eliminated = count.most_common(1)[0][0]
        game.alive = [p for p in game.alive if p != eliminated]

        if eliminated.role == "spy":
            spies_caught += 1
        role_tag = '<span class="bad">spy</span>' if eliminated.role == "spy" else '<span class="good">civilian</span>'
        acc = correct_votes / total_votes * 100 if total_votes else 0
        log(
            f'&nbsp;&nbsp;<span class="bad">✗ {eliminated.name} eliminated</span> — was {role_tag}<br>'
            f'&nbsp;&nbsp;<span class="dim">accuracy so far: {acc:.0f}% ({correct_votes}/{total_votes})</span>',
            extra_gap=True,
        )

        # Win check
        spies     = [p for p in game.alive if p.role == "spy"]
        civilians = [p for p in game.alive if p.role == "civilian"]

        if not spies:
            log(f'<span class="good">🏁 Civilians win! ({round_count} rounds)</span>', extra_gap=True)
            winner = "Civilians 🟢"
            break
        if len(spies) >= len(civilians):
            log(f'<span class="bad">🏁 Spies win! ({round_count} rounds)</span>', extra_gap=True)
            winner = "Spies 🔴"
            break

    # Save stats and render
    st.session_state.stats = {
        "rounds":      round_count,
        "winner":      winner,
        "acc":         acc,
        "caught":      spies_caught,
        "total_spies": int(num_spies),
    }
    st.session_state.done = True
    render_stats()