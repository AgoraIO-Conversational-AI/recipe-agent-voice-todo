"""Pure RPG game engine — SQLite-backed, no MCP import (fully unit-testable).

Self-contained actions: each function resolves a whole action and rolls dice
INTERNALLY, so the recipe never depends on the LLM chaining tool calls. State is
global (single-player demo — the MCP server gets no session id from Agora).
"""
import json
import os
import random
import sqlite3

_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv("RPG_DB_PATH") or os.path.join(_base_dir, "rpg.db")

# Seedable RNG: set RPG_SEED for deterministic combat (tests); unset = random play.
_seed = os.getenv("RPG_SEED")
_RNG = random.Random(int(_seed)) if _seed not in (None, "") else random.Random()

# Static tables (replace the source's Cerebras dynamic generation).
CLASSES = {
    "warrior": {"hp": 30, "die": 8, "spell": "shield bash"},
    "mage":    {"hp": 18, "die": 6, "spell": "fireball"},
    "rogue":   {"hp": 22, "die": 6, "spell": "backstab"},
    "cleric":  {"hp": 24, "die": 6, "spell": "smite"},
}
ENCOUNTERS = [
    {"name": "goblin",   "hp": 12, "atk": 4},
    {"name": "skeleton", "hp": 16, "atk": 5},
    {"name": "orc",      "hp": 22, "atk": 7},
]
LOOT = ["a pouch of gold", "a health potion", "a rusty dagger", "a glowing gem"]


def get_db(path: str = DB_PATH) -> "sqlite3.Connection":
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS character (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            class TEXT, hp INTEGER, max_hp INTEGER, gold INTEGER, inventory TEXT
        );
        CREATE TABLE IF NOT EXISTS enemy (
            id INTEGER PRIMARY KEY CHECK (id = 1), name TEXT, hp INTEGER, atk INTEGER
        );
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        """
    )
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('mode', 'narration')")
    conn.commit()
    return conn


def roll(sides: int, rng: random.Random = _RNG) -> int:
    return rng.randint(1, sides)


def current_mode(conn) -> str:
    return conn.execute("SELECT value FROM settings WHERE key='mode'").fetchone()[0]


def _set_mode(conn, mode: str) -> None:
    conn.execute("UPDATE settings SET value=? WHERE key='mode'", (mode,))
    conn.commit()


def _char(conn):
    return conn.execute(
        "SELECT class, hp, max_hp, gold, inventory FROM character WHERE id=1"
    ).fetchone()


def _enemy(conn):
    return conn.execute("SELECT name, hp, atk FROM enemy WHERE id=1").fetchone()


def create_character(conn, char_class: str) -> str:
    cls = (char_class or "").strip().lower()
    if cls not in CLASSES:
        return "Choose a class: warrior, mage, rogue, or cleric."
    stats = CLASSES[cls]
    conn.execute("DELETE FROM character")
    conn.execute("DELETE FROM enemy")
    conn.execute(
        "INSERT INTO character (id, class, hp, max_hp, gold, inventory) VALUES (1,?,?,?,?,?)",
        (cls, stats["hp"], stats["hp"], 0, "[]"),
    )
    _set_mode(conn, "narration")
    conn.commit()
    return (f"You are a {cls} with {stats['hp']} HP; your signature move is "
            f"{stats['spell']}. Your adventure begins.")


def get_character(conn) -> str:
    c = _char(conn)
    if not c:
        return "No hero yet — choose a class: warrior, mage, rogue, or cleric."
    cls, hp, max_hp, gold, inv = c
    items = json.loads(inv) or ["nothing"]
    mode = current_mode(conn)
    e = _enemy(conn)
    fighting = f" Fighting a {e[0]} ({e[1]} HP)." if (mode == "combat" and e) else ""
    return (f"{cls.title()} — {hp}/{max_hp} HP, {gold} gold, carrying "
            f"{', '.join(items)}. Mode: {mode}.{fighting}")


def start_encounter(conn, rng: random.Random = _RNG) -> str:
    if not _char(conn):
        return "Create a character first (warrior, mage, rogue, or cleric)."
    if current_mode(conn) == "combat":
        e = _enemy(conn)
        return f"You're already fighting a {e[0]}!"
    enc = ENCOUNTERS[rng.randint(0, len(ENCOUNTERS) - 1)]
    conn.execute("DELETE FROM enemy")
    conn.execute(
        "INSERT INTO enemy (id, name, hp, atk) VALUES (1,?,?,?)",
        (enc["name"], enc["hp"], enc["atk"]),
    )
    _set_mode(conn, "combat")
    conn.commit()
    return f"A {enc['name']} appears ({enc['hp']} HP)! Attack or cast your spell."


def _resolve(conn, label: str, die: int, rng: random.Random) -> str:
    cls, hp, max_hp, gold, inv = _char(conn)
    name, ehp, eatk = _enemy(conn)
    dmg = roll(die, rng)
    ehp -= dmg
    if ehp <= 0:
        loot = LOOT[rng.randint(0, len(LOOT) - 1)]
        items = json.loads(inv)
        gold_gain = 10 if "gold" in loot else 0
        if gold_gain == 0:
            items.append(loot)
        conn.execute("DELETE FROM enemy")
        conn.execute(
            "UPDATE character SET gold=gold+?, inventory=? WHERE id=1",
            (gold_gain, json.dumps(items)),
        )
        _set_mode(conn, "narration")
        conn.commit()
        return (f"Your {label} rolls {dmg} — the {name} takes {dmg} and falls! "
                f"You find {loot}. The path is quiet again.")
    ehit = roll(eatk, rng)
    hp -= ehit
    if hp <= 0:
        conn.execute("DELETE FROM character")
        conn.execute("DELETE FROM enemy")
        _set_mode(conn, "narration")
        conn.commit()
        return (f"Your {label} rolls {dmg}; the {name} drops to {ehp} HP but its "
                f"reprisal hits for {ehit} and you fall. Game over — create a new hero.")
    conn.execute("UPDATE character SET hp=? WHERE id=1", (hp,))
    conn.execute("UPDATE enemy SET hp=? WHERE id=1", (ehp,))
    conn.commit()
    return (f"Your {label} rolls {dmg} — the {name} drops to {ehp} HP, then strikes "
            f"back for {ehit}. You have {hp} HP left.")


def attack(conn, rng: random.Random = _RNG) -> str:
    c = _char(conn)
    if not c:
        return "Create a character first."
    if current_mode(conn) != "combat" or not _enemy(conn):
        return "There's no enemy here — explore to find a fight."
    return _resolve(conn, "attack", CLASSES[c[0]]["die"], rng)


def cast_spell(conn, name: str, rng: random.Random = _RNG) -> str:
    c = _char(conn)
    if not c:
        return "Create a character first."
    spell = CLASSES[c[0]]["spell"]
    if spell not in (name or "").strip().lower():
        return f"Your {c[0]} can only cast {spell}."
    if current_mode(conn) != "combat" or not _enemy(conn):
        return f"You ready {spell}, but there's no enemy here."
    return _resolve(conn, spell, CLASSES[c[0]]["die"] + 2, rng)


def flee(conn) -> str:
    if current_mode(conn) != "combat":
        return "You're not in combat."
    e = _enemy(conn)
    conn.execute("DELETE FROM enemy")
    _set_mode(conn, "narration")
    conn.commit()
    return f"You flee from the {e[0] if e else 'enemy'} and slip into the shadows."
