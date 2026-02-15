#!/usr/bin/env python3
"""
intent_matcher.py — Voice-Link intent matcher (standalone, no deps)
Pattern-based command matching for field operations.
No AI, no LLM — just fast fuzzy string matching.

Usage:
    python3 intent_matcher.py "stop le robot"
    python3 intent_matcher.py "batterie du drone"
    python3 intent_matcher.py --test         # Run built-in tests
    python3 intent_matcher.py --list         # List all commands
    python3 intent_matcher.py --json "stop"  # JSON output
"""

import sys
import json
import unicodedata
from pathlib import Path

# ─── Load intents from YAML (minimal parser, no PyYAML needed) ───

def load_intents_simple(path: str) -> list:
    """Minimal YAML-like parser for intents.yml — handles our specific format."""
    intents = []
    current = None

    with open(path) as f:
        for line in f:
            stripped = line.strip()

            # Skip comments and empty
            if not stripped or stripped.startswith("#"):
                continue

            # New intent block
            if stripped.startswith("- id:"):
                if current:
                    intents.append(current)
                current = {
                    "id": stripped.split(":", 1)[1].strip(),
                    "patterns": [],
                    "action": "",
                    "response": "",
                    "confirm": False,
                    "internal": False,
                }

            elif current:
                if stripped.startswith('- "') and "patterns" not in stripped:
                    # Pattern entry
                    pattern = stripped[3:].rstrip('"')
                    current["patterns"].append(pattern)
                elif stripped.startswith("action:"):
                    current["action"] = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("response:"):
                    val = stripped.split(":", 1)[1].strip().strip('"')
                    current["response"] = val if val != "null" else None
                elif stripped.startswith("confirm:"):
                    current["confirm"] = stripped.split(":", 1)[1].strip() == "true"
                elif stripped.startswith("internal:"):
                    current["internal"] = stripped.split(":", 1)[1].strip() == "true"
                elif stripped.startswith("target_type:"):
                    current["target_type"] = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("panel:"):
                    current["panel"] = stripped.split(":", 1)[1].strip()

    if current:
        intents.append(current)

    return intents


# ─── Intent Matcher ─────────────────────────────────────

def normalize(text: str) -> str:
    """Remove accents, lowercase, strip punctuation."""
    text = text.lower().strip()
    # Remove accents
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    # Remove non-alphanumeric (keep spaces)
    text = "".join(c for c in text if c.isalnum() or c == " ")
    return text.strip()


def similarity(a: str, b: str) -> float:
    """Simple similarity: exact > contains > word overlap."""
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.9
    # Jaccard word overlap
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    intersection = len(words_a & words_b)
    union = len(words_a | words_b)
    return intersection / union


def match_intent(transcript: str, intents: list, threshold: float = 0.6) -> dict | None:
    """Match a transcript to the best intent."""
    input_norm = normalize(transcript)
    best_match = None
    best_score = 0.0

    for intent in intents:
        for pattern in intent["patterns"]:
            score = similarity(input_norm, normalize(pattern))
            if score > best_score and score >= threshold:
                best_score = score
                best_match = {**intent, "score": round(score, 2)}

    return best_match


def extract_target(transcript: str) -> dict | None:
    """Extract target entity from transcript."""
    lower = transcript.lower()
    if any(w in lower for w in ("robot", "spot", "go2")):
        return {"type": "robot"}
    if any(w in lower for w in ("drone", "dji", "quad")):
        return {"type": "drone"}
    import re
    m = re.search(r"gw[- ]?(\d+)", lower)
    if m:
        return {"id": f"gw-{m.group(1).zfill(2)}"}
    return None


# ─── Tests ──────────────────────────────────────────────

TEST_CASES = [
    # (input, expected_intent_id, description)
    ("stop", "stop", "Commande directe"),
    ("stop le robot", "stop", "Stop avec cible"),
    ("stop le drone", "stop", "Stop drone"),
    ("arrête tout", "stop", "Synonyme FR"),
    ("avance", "go", "Reprise simple"),
    ("reprends", "go", "Reprise synonyme"),
    ("retour base", "return_home", "Retour"),
    ("rentre", "return_home", "Retour court"),
    ("atterris", "land", "Landing"),
    ("pose-toi", "land", "Landing FR"),
    ("décolle", "takeoff", "Takeoff"),
    ("batterie", "battery", "Query batterie"),
    ("niveau batterie", "battery", "Query batterie long"),
    ("combien de batterie", "battery", "Query batterie question"),
    ("position", "position", "Query position"),
    ("où est le robot", "position", "Query position FR"),
    ("status", "status", "Status"),
    ("état", "status", "Status FR"),
    ("lance la mission", "start_mission", "Start mission"),
    ("annule la mission", "abort_mission", "Abort mission"),
    ("montre la carte", "show_map", "UI carte"),
    ("ouvre la config", "show_config", "UI config"),
    ("oui", "confirm_yes", "Confirmation"),
    ("non", "confirm_no", "Annulation"),
    ("silence", "mute", "Mute"),
    ("parle", "unmute", "Unmute"),
    ("lance le scan lidar", "start_scan", "LiDAR scan"),
    ("état du lidar", "lidar_status", "LiDAR status"),
    ("stockage", "storage_check", "Storage"),
    # Fuzzy matches
    ("arrete le robot", "stop", "Sans accent"),
    ("ou est le drone", "position", "Sans accent question"),
    # Negative cases
    ("bonjour comment ça va aujourd'hui", "status", "Contient 'comment ça va' → status"),
    ("il fait beau dehors ce matin", None, "Hors vocabulaire"),
    ("fais moi un café", None, "N'importe quoi"),
]


def run_tests(intents: list) -> bool:
    """Run built-in test suite. Returns True if all pass."""
    passed = 0
    failed = 0

    print(f"Running {len(TEST_CASES)} intent matching tests...\n")

    for transcript, expected_id, desc in TEST_CASES:
        result = match_intent(transcript, intents)
        got_id = result["id"] if result else None

        if got_id == expected_id:
            passed += 1
            score_str = f" ({result['score']:.0%})" if result else ""
            print(f"  PASS  \"{transcript}\" -> {got_id}{score_str}  [{desc}]")
        else:
            failed += 1
            score_str = f" ({result['score']:.0%})" if result else ""
            print(f"  FAIL  \"{transcript}\" -> {got_id}{score_str}  (expected: {expected_id})  [{desc}]")

    print(f"\n{'=' * 50}")
    print(f"  {passed} passed, {failed} failed, {len(TEST_CASES)} total")
    print(f"{'=' * 50}")

    return failed == 0


# ─── CLI ────────────────────────────────────────────────

def main():
    intents_path = Path(__file__).parent / "intents.yml"
    if not intents_path.exists():
        print(f"Error: {intents_path} not found")
        sys.exit(1)

    intents = load_intents_simple(str(intents_path))

    if "--test" in sys.argv:
        ok = run_tests(intents)
        sys.exit(0 if ok else 1)

    if "--list" in sys.argv:
        print("Available voice commands:\n")
        for intent in intents:
            if intent.get("internal"):
                continue
            print(f"  [{intent['id']}]")
            for p in intent["patterns"]:
                print(f"    \"{p}\"")
            if intent.get("confirm"):
                print(f"    (requires confirmation)")
            print()
        sys.exit(0)

    use_json = "--json" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if not args:
        print("Usage:")
        print('  python3 intent_matcher.py "stop le robot"')
        print("  python3 intent_matcher.py --test")
        print("  python3 intent_matcher.py --list")
        print('  python3 intent_matcher.py --json "batterie"')
        sys.exit(0)

    transcript = " ".join(args)
    result = match_intent(transcript, intents)
    target = extract_target(transcript)

    if use_json:
        output = {
            "transcript": transcript,
            "intent": result["id"] if result else None,
            "action": result["action"] if result else None,
            "score": result["score"] if result else 0,
            "confirm": result.get("confirm", False) if result else False,
            "response": result.get("response") if result else None,
            "target": target,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        if result:
            print(f"  Input:    \"{transcript}\"")
            print(f"  Intent:   {result['id']}")
            print(f"  Action:   {result['action']}")
            print(f"  Score:    {result['score']:.0%}")
            print(f"  Confirm:  {result.get('confirm', False)}")
            print(f"  Response: {result.get('response', '-')}")
            if target:
                print(f"  Target:   {target}")
        else:
            print(f"  Input:    \"{transcript}\"")
            print(f"  Intent:   (no match)")


if __name__ == "__main__":
    main()
