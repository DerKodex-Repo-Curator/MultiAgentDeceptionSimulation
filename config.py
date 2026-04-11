import os
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# ── Game constants ─────────────────────────────────────────────────────────────
NUM_PLAYERS = 8
NUM_SPIES   = 2

PERSONALITIES = ["aggressive", "conservative", "deceptive"]  

# ── Communication modes ────────────────────────────────────────────────────────
# Controls how much agents can communicate each round.
#   "clue_only"       → one word clue only                   (Mode 1)
#   "clue_and_statement" → one word clue + one sentence statement (Mode 2)
COMM_MODE = "clue_and_statement"  # change this to switch modes

# ── Word data ──────────────────────────────────────────────────────────────────
WORD_PAIRS = [
    # Professions
    ("Doctor", "Nurse"),
    ("Teacher", "Student"),
    ("Lawyer", "Judge"),
    ("Chef", "Waiter"),
    ("Pilot", "Driver"),

    # Animals
    ("Lion", "Tiger"),
    ("Cat", "Dog"),
    ("Wolf", "Fox"),
    ("Horse", "Donkey"),
    ("Shark", "Dolphin"),

    # Technology
    ("Laptop", "Tablet"),
    ("Phone", "Camera"),
    ("Keyboard", "Mouse"),
    ("Monitor", "TV"),
    ("Speaker", "Headphones"),

    # Transport
    ("Car", "Bike"),
    ("Train", "Bus"),
    ("Plane", "Helicopter"),
    ("Ship", "Boat"),
    ("Truck", "Van"),

    # Food
    ("Pizza", "Burger"),
    ("Coffee", "Tea"),
    ("Bread", "Toast"),
    ("Rice", "Wheat"),
    ("Apple", "Orange"),

    # Nature
    ("Sun", "Moon"),
    ("River", "Lake"),
    ("Ocean", "Sea"),
    ("Mountain", "Hill"),
    ("Forest", "Jungle"),

    # Objects
    ("Chair", "Table"),
    ("Pen", "Pencil"),
    ("Bottle", "Glass"),
    ("Door", "Window"),
    ("Clock", "Watch"),

    # Clothing
    ("Shirt", "Jacket"),
    ("Shoes", "Sandals"),
    ("Hat", "Cap"),
    ("Jeans", "Trousers"),
    ("Sweater", "Hoodie"),

    # Sports
    ("Football", "Basketball"),
    ("Cricket", "Baseball"),
    ("Tennis", "Badminton"),
    ("Hockey", "Rugby"),
    ("Golf", "Pool"),

    # Places
    ("School", "College"),
    ("Hospital", "Clinic"),
    ("City", "Town"),
    ("Village", "Farm"),
    ("Park", "Garden"),

    # Misc (subtle differences)
    ("Knife", "Sword"),
    ("Ring", "Bracelet"),
    ("Book", "Notebook"),
    ("Map", "Globe"),
    ("Key", "Lock"),
]

CLUE_DICT = {
    # "Doctor": ["hospital", "health", "medicine"],
    # "Nurse": ["care", "hospital", "assist"],

    # "Teacher": ["school", "lesson", "class"],
    # "Student": ["study", "learn", "school"],

    # "Lawyer": ["court", "law", "case"],
    # "Judge": ["court", "decision", "law"],

    # "Chef": ["cook", "kitchen", "food"],
    # "Waiter": ["serve", "restaurant", "food"],

    # "Pilot": ["fly", "air", "cockpit"],
    # "Driver": ["road", "vehicle", "drive"],

    # "Lion": ["wild", "roar", "jungle"],
    # "Tiger": ["stripe", "wild", "hunt"],

    # "Cat": ["pet", "meow", "furry"],
    # "Dog": ["bark", "loyal", "pet"],

    # "Wolf": ["pack", "wild", "hunt"],
    # "Fox": ["sly", "wild", "clever"],

    # "Horse": ["ride", "farm", "fast"],
    # "Donkey": ["load", "farm", "slow"],

    # "Shark": ["sea", "teeth", "danger"],
    # "Dolphin": ["sea", "smart", "jump"],

    # "Laptop": ["computer", "portable", "screen"],
    # "Tablet": ["touch", "screen", "device"],

    # "Phone": ["call", "mobile", "talk"],
    # "Camera": ["photo", "lens", "capture"],

    # "Keyboard": ["type", "keys", "input"],
    # "Mouse": ["click", "cursor", "device"],

    # "Monitor": ["display", "screen", "visual"],
    # "TV": ["watch", "screen", "entertainment"],

    # "Speaker": ["sound", "music", "audio"],
    # "Headphones": ["listen", "audio", "ears"],

    # "Car": ["drive", "road", "engine"],
    # "Bike": ["ride", "two", "pedal"],

    # "Train": ["track", "rail", "travel"],
    # "Bus": ["public", "transport", "road"],

    # "Plane": ["fly", "sky", "airport"],
    # "Helicopter": ["rotor", "air", "hover"],

    # "Ship": ["sea", "travel", "water"],
    # "Boat": ["water", "small", "sail"],

    # "Truck": ["cargo", "load", "road"],
    # "Van": ["transport", "cargo", "vehicle"],

    # "Pizza": ["cheese", "slice", "food"],
    # "Burger": ["bun", "meat", "food"],

    # "Coffee": ["drink", "caffeine", "hot"],
    # "Tea": ["drink", "leaf", "hot"],

    # "Bread": ["bake", "food", "slice"],
    # "Toast": ["crispy", "bread", "breakfast"],

    # "Rice": ["grain", "food", "cook"],
    # "Wheat": ["grain", "farm", "flour"],

    # "Apple": ["fruit", "red", "sweet"],
    # "Orange": ["citrus", "fruit", "juice"],

    # "Sun": ["bright", "day", "hot"],
    # "Moon": ["night", "light", "sky"],

    # "River": ["flow", "water", "stream"],
    # "Lake": ["water", "still", "body"],

    # "Ocean": ["vast", "water", "deep"],
    # "Sea": ["water", "salty", "waves"],

    # "Mountain": ["high", "peak", "rock"],
    # "Hill": ["small", "rise", "land"],

    # "Forest": ["trees", "wild", "nature"],
    # "Jungle": ["dense", "wild", "tropical"],

    # "Chair": ["sit", "seat", "furniture"],
    # "Table": ["surface", "furniture", "flat"],

    # "Pen": ["write", "ink", "paper"],
    # "Pencil": ["write", "lead", "draw"],

    # "Bottle": ["liquid", "container", "drink"],
    # "Glass": ["drink", "clear", "fragile"],

    # "Door": ["enter", "open", "room"],
    # "Window": ["view", "glass", "light"],

    # "Clock": ["time", "wall", "tick"],
    # "Watch": ["time", "wrist", "wear"],

    # "Shirt": ["wear", "cloth", "top"],
    # "Jacket": ["warm", "coat", "wear"],

    # "Shoes": ["wear", "feet", "walk"],
    # "Sandals": ["open", "feet", "wear"],

    # "Hat": ["head", "wear", "cover"],
    # "Cap": ["head", "casual", "wear"],

    # "Jeans": ["denim", "pants", "wear"],
    # "Trousers": ["formal", "pants", "wear"],

    # "Sweater": ["warm", "knit", "wear"],
    # "Hoodie": ["casual", "hood", "wear"],

    # "Football": ["kick", "goal", "sport"],
    # "Basketball": ["dribble", "hoop", "sport"],

    # "Cricket": ["bat", "ball", "wicket"],
    # "Baseball": ["bat", "pitch", "ball"],

    # "Tennis": ["racket", "court", "serve"],
    # "Badminton": ["shuttle", "racket", "net"],

    # "Hockey": ["stick", "puck", "goal"],
    # "Rugby": ["tackle", "ball", "team"],

    # "Golf": ["club", "hole", "swing"],
    # "Pool": ["cue", "table", "balls"],

    # "School": ["learn", "students", "class"],
    # "College": ["higher", "study", "campus"],

    # "Hospital": ["treat", "patients", "care"],
    # "Clinic": ["small", "treat", "health"],

    # "City": ["urban", "crowd", "buildings"],
    # "Town": ["small", "community", "place"],

    # "Village": ["rural", "small", "community"],
    # "Farm": ["animals", "crops", "land"],

    # "Park": ["green", "relax", "trees"],
    # "Garden": ["plants", "flowers", "grow"],

    # "Knife": ["cut", "sharp", "tool"],
    # "Sword": ["weapon", "sharp", "fight"],

    # "Ring": ["finger", "jewel", "circle"],
    # "Bracelet": ["wrist", "jewel", "wear"],

    # "Book": ["read", "pages", "story"],
    # "Notebook": ["write", "notes", "paper"],

    # "Map": ["navigate", "location", "guide"],
    # "Globe": ["earth", "round", "map"],

    # "Key": ["lock", "open", "metal"],
    # "Lock": ["secure", "close", "key"],
}

# ── LLM setup (lazy) ───────────────────────────────────────────────────────────
_llm = None

def get_llm() -> ChatOllama:
    """Returns the shared LLM instance, creating it on first call."""
    global _llm
    if _llm is None:
        api_key  = os.getenv("OLLAMA_API_KEY")
        base_url = os.getenv("OLLAMA_BASE_URL")
        if not api_key or not base_url:
            raise EnvironmentError(
                "Missing required env vars: OLLAMA_API_KEY and OLLAMA_BASE_URL\n"
                "Set them before running:\n"
                "  set OLLAMA_API_KEY=your_key    (Windows)\n"
                "  set OLLAMA_BASE_URL=your_url"
            )
        _llm = ChatOllama(
            model="llama3.2:latest",
            api_key=api_key,
            base_url=base_url,
        )
    return _llm

SYSTEM_PROMPT = SystemMessage(content="""
You are an AI agent playing a social deduction game.

Your goal depends on your role:
- If civilian: identify the spy
- If spy: avoid detection

Respond concisely and strategically.
""")