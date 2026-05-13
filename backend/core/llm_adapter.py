"""
LLM Floor Plan Adapter — Layers 1 + 2 combined.

Replaces the T5 NLP (Layer 1) + StructuralGNN (Layer 2) with a single
LLM API call that generates a complete room layout from a text prompt.

Supported providers:
  openai            → GPT-3.5-turbo, GPT-4o, etc.
  anthropic         → Claude 3 Haiku, Sonnet, Opus
  openai_compatible → Any OpenAI-compatible endpoint:
                        Groq   (free):   https://api.groq.com/openai/v1
                        Ollama (free):   http://localhost:11434/v1
                        OpenRouter:      https://openrouter.ai/api/v1

Configuration via environment variables (or .env file in project root):
  LLM_PROVIDER   openai | anthropic | openai_compatible  (default: auto-detect)
  LLM_API_KEY    Your API key
  LLM_MODEL      Model name (see defaults below)
  LLM_BASE_URL   Base URL — required for openai_compatible

Quickest free setup:
  Sign up at console.groq.com (no credit card) then set:
    LLM_PROVIDER=openai_compatible
    LLM_API_KEY=<your groq key>
    LLM_BASE_URL=https://api.groq.com/openai/v1
    LLM_MODEL=llama-3.3-70b-versatile
"""

import os
import re
import json
import asyncio
import random
from pathlib import Path
from typing import Dict, Any, Optional

# Load .env from project root if present
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass  # python-dotenv not installed — use system env vars


# ── Default models per provider ────────────────────────────────────────────────
_DEFAULTS = {
    "openai":            "gpt-4o-mini",
    "anthropic":         "claude-haiku-4-5-20251001",
    "openai_compatible": "llama-3.3-70b-versatile",
}

# ── System prompt ──────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are an expert residential architect generating precise 2D floor plan layouts as JSON.

═══ ABSOLUTE CONSTRAINTS (violating any of these makes the output invalid) ═══
1. Units: all x, y, width, height in METRES. x increases right, y increases up.
2. No overlaps: for every pair of rooms, their rectangles must not share interior area.
   Verify: if rooms A and B overlap, they must satisfy at least one of:
     A.x+A.width ≤ B.x  OR  B.x+B.width ≤ A.x  OR  A.y+A.height ≤ B.y  OR  B.y+B.height ≤ A.y
3. No gaps: every room must touch at least one other room with a shared edge (not diagonal).
   A shared edge means one room's edge coordinate exactly equals another's:
     e.g. room A right edge (A.x + A.width) == room B left edge (B.x)
4. Anchor: the first room in the array starts at x=0, y=0.
5. Connectivity: the entire layout forms one connected block — no isolated rooms.
6. Hallways must span the FULL width of the plan so all doors off the hallway are reachable.

═══ ARCHITECTURAL RULES ═══
Zone separation (y-axis, low to high):
  • Ground zone (y=0): public rooms — living, kitchen, dining, garage/parking, veranda
  • Middle zone: hallway/corridor running FULL plan width, height 1.2–1.8 m
  • Upper zone: private rooms — all bedrooms, all bathrooms, storage
  Bathrooms always adjoin a bedroom or hallway, never isolated.

Room sizing (width × depth in metres):
  living    : 4.5–6.5 × 4.0–5.5   kitchen  : 2.8–4.0 × 2.8–4.5
  dining    : 3.0–4.5 × 2.5–3.5   bedroom  : 3.2–5.5 × 3.2–4.5  (master ≥ 4.0×4.0)
  bathroom  : 1.8–2.8 × 2.0–3.0   hallway  : full-width × 1.2–1.8
  balcony   : 1.5–3.0 × 1.0–2.0   parking  : 2.8–3.5 × 5.0–6.5
  storage   : 1.2–2.5 × 1.2–2.5   stair    : 2.0–2.5 × 2.5–3.5
  veranda   : 2.5–4.5 × 1.5–2.5   garden   : 3.5–7.0 × 3.5–6.0

Layout patterns by bedroom count:
  1–2 bed: public zone at y=0 (living + kitchen side-by-side), hallway above, bedrooms + bath above hallway in a row.
  3–4 bed: wide public zone, full-width hallway, then TWO ROWS of bedrooms side-by-side (not a single tall column). 2 bathrooms flanking the hallway entry.
  5+ bed : two parallel hallways forming a spine, or L/U shaped corridors. Keep width >> depth.

Style hints per prompt:
  "haveli" / "courtyard" → wider plan, add veranda at front (y=0), thicker walls implied by larger rooms
  "apartment" → more compact, add balcony off living or bedroom
  "bungalow" → single storey feel, wider rather than taller plan
  "villa" → generous room sizes, add garden + parking

VALID type strings (use exactly): bedroom, bathroom, living, kitchen, dining, hallway, balcony, garden, parking, storage, stair, veranda

═══ SELF-CHECK BEFORE OUTPUTTING ═══
For each room R, confirm:
  a) At least one neighbour N where R shares an edge: R.x+R.width==N.x OR N.x+N.width==R.x OR R.y+R.height==N.y OR N.y+N.height==R.y
  b) No pair (R, N) where rectangles overlap in both axes simultaneously.
If any room fails (a), move it flush against its nearest neighbour before outputting.

OUTPUT FORMAT — return only this JSON object, no markdown, no explanation:
{"rooms":[{"id":"type_index","type":"TYPE","x":X.XX,"y":Y.YY,"width":W.WW,"height":H.HH},...],"metadata":{"unit_type":"house","total_area":AREA}}"""

# ── Few-shot examples ──────────────────────────────────────────────────────────
# Four verified layouts: zero overlaps, all shared-wall edges, realistic Pakistani house sizes.
_EXAMPLES = [
    {
        # 2-bed compact house
        "user": "A 2 bedroom house with 1 bathroom, living room, and kitchen",
        "assistant": json.dumps({
            "rooms": [
                {"id": "living_0",   "type": "living",   "x": 0.0, "y": 0.0, "width": 5.0, "height": 4.5},
                {"id": "kitchen_1",  "type": "kitchen",  "x": 5.0, "y": 0.0, "width": 3.2, "height": 4.5},
                {"id": "hallway_2",  "type": "hallway",  "x": 0.0, "y": 4.5, "width": 8.2, "height": 1.4},
                {"id": "bathroom_3", "type": "bathroom", "x": 0.0, "y": 5.9, "width": 2.2, "height": 2.8},
                {"id": "bedroom_4",  "type": "bedroom",  "x": 2.2, "y": 5.9, "width": 3.0, "height": 3.6},
                {"id": "bedroom_5",  "type": "bedroom",  "x": 5.2, "y": 5.9, "width": 3.0, "height": 3.6},
            ],
            "metadata": {"unit_type": "house", "total_area": 76}
        }, separators=(',', ':'))
    },
    {
        # 4-bed house, two-row bedroom zone
        "user": "A 4 bedroom house with 2 bathrooms, living room, kitchen, and dining room",
        "assistant": json.dumps({
            "rooms": [
                {"id": "living_0",   "type": "living",   "x": 0.0, "y": 0.0, "width": 5.5, "height": 4.5},
                {"id": "kitchen_1",  "type": "kitchen",  "x": 5.5, "y": 0.0, "width": 3.5, "height": 3.0},
                {"id": "dining_2",   "type": "dining",   "x": 5.5, "y": 3.0, "width": 3.5, "height": 1.5},
                {"id": "hallway_3",  "type": "hallway",  "x": 0.0, "y": 4.5, "width": 9.0, "height": 1.5},
                {"id": "bathroom_4", "type": "bathroom", "x": 0.0, "y": 6.0, "width": 2.2, "height": 2.8},
                {"id": "bathroom_5", "type": "bathroom", "x": 2.2, "y": 6.0, "width": 2.2, "height": 2.8},
                {"id": "bedroom_6",  "type": "bedroom",  "x": 4.4, "y": 6.0, "width": 4.6, "height": 3.8},
                {"id": "bedroom_7",  "type": "bedroom",  "x": 0.0, "y": 8.8, "width": 3.2, "height": 3.8},
                {"id": "bedroom_8",  "type": "bedroom",  "x": 3.2, "y": 8.8, "width": 3.0, "height": 3.8},
                {"id": "bedroom_9",  "type": "bedroom",  "x": 6.2, "y": 8.8, "width": 2.8, "height": 3.8},
            ],
            "metadata": {"unit_type": "house", "total_area": 120}
        }, separators=(',', ':'))
    },
    {
        # 3-bed apartment with balcony
        "user": "A 3 bedroom apartment with 2 bathrooms, open plan living and kitchen, dining, and a balcony",
        "assistant": json.dumps({
            "rooms": [
                {"id": "living_0",   "type": "living",   "x": 0.0, "y": 0.0, "width": 5.5, "height": 4.5},
                {"id": "kitchen_1",  "type": "kitchen",  "x": 5.5, "y": 0.0, "width": 3.0, "height": 3.0},
                {"id": "dining_2",   "type": "dining",   "x": 5.5, "y": 3.0, "width": 3.0, "height": 1.5},
                {"id": "balcony_3",  "type": "balcony",  "x": 8.5, "y": 0.0, "width": 1.8, "height": 4.5},
                {"id": "hallway_4",  "type": "hallway",  "x": 0.0, "y": 4.5, "width": 8.5, "height": 1.4},
                {"id": "bathroom_5", "type": "bathroom", "x": 0.0, "y": 5.9, "width": 2.2, "height": 2.6},
                {"id": "bathroom_6", "type": "bathroom", "x": 2.2, "y": 5.9, "width": 2.2, "height": 2.6},
                {"id": "bedroom_7",  "type": "bedroom",  "x": 4.4, "y": 5.9, "width": 4.1, "height": 4.0},
                {"id": "bedroom_8",  "type": "bedroom",  "x": 0.0, "y": 8.5, "width": 4.2, "height": 3.8},
                {"id": "bedroom_9",  "type": "bedroom",  "x": 4.2, "y": 9.9, "width": 4.3, "height": 2.4},
            ],
            "metadata": {"unit_type": "apartment", "total_area": 116}
        }, separators=(',', ':'))
    },
    {
        # 5-marla Pakistani haveli-style house with parking and veranda
        "user": "A traditional Pakistani 5 marla house with 3 bedrooms, 2 bathrooms, lounge, kitchen, and a veranda at the front with parking",
        "assistant": json.dumps({
            "rooms": [
                {"id": "parking_0",  "type": "parking",  "x": 0.0, "y": 0.0, "width": 2.8, "height": 5.5},
                {"id": "veranda_1",  "type": "veranda",  "x": 2.8, "y": 0.0, "width": 4.7, "height": 2.0},
                {"id": "living_2",   "type": "living",   "x": 2.8, "y": 2.0, "width": 4.7, "height": 3.5},
                {"id": "kitchen_3",  "type": "kitchen",  "x": 7.5, "y": 0.0, "width": 3.0, "height": 5.5},
                {"id": "hallway_4",  "type": "hallway",  "x": 0.0, "y": 5.5, "width":10.5, "height": 1.4},
                {"id": "bathroom_5", "type": "bathroom", "x": 0.0, "y": 6.9, "width": 2.4, "height": 2.6},
                {"id": "bathroom_6", "type": "bathroom", "x": 2.4, "y": 6.9, "width": 2.4, "height": 2.6},
                {"id": "bedroom_7",  "type": "bedroom",  "x": 4.8, "y": 6.9, "width": 5.7, "height": 4.0},
                {"id": "bedroom_8",  "type": "bedroom",  "x": 0.0, "y": 9.5, "width": 4.8, "height": 4.0},
                {"id": "bedroom_9",  "type": "bedroom",  "x": 4.8, "y":10.9, "width": 5.7, "height": 2.6},
            ],
            "metadata": {"unit_type": "house", "total_area": 140}
        }, separators=(',', ':'))
    },
]


# ── Layout variant pool ────────────────────────────────────────────────────────
# One is picked at random per generation call and appended to the user prompt.
# Each variant forces a structurally different spatial arrangement.
_LAYOUT_VARIANTS = [
    # 0 – wide shallow (standard Pakistani residential, bedrooms across full back)
    "Spatial arrangement: WIDE SHALLOW plan. Ground floor: living + kitchen + dining "
    "placed side-by-side in a wide front band (width >> depth). Full-width hallway "
    "above. All bedrooms span the full width at the back in a single row. "
    "Total width should be 10–14 m, depth 10–16 m.",

    # 1 – standard with central corridor spine
    "Spatial arrangement: CENTRAL CORRIDOR. A wide hallway or passage runs down the "
    "middle of the plan. Living and kitchen on one side of the corridor (or below it). "
    "Bedrooms and bathrooms on the other side. Compact and efficient.",

    # 2 – front veranda / street-facing
    "Spatial arrangement: FRONT VERANDA. Add a veranda or covered entrance at y=0 "
    "spanning at least 40% of the total width. Living room directly behind veranda. "
    "Kitchen to the side. Bedrooms at the back above the hallway. "
    "Typical of older Lahore / Karachi residential plots.",

    # 3 – double-storey feel (private zone stacked)
    "Spatial arrangement: STACKED ZONES. Ground zone is entirely public: living, "
    "kitchen, dining, and optionally parking all share y=0. "
    "Private zone (bedrooms, bathrooms) is a separate deep band above the hallway. "
    "Bedrooms arranged in TWO side-by-side rows (not a single column).",

    # 4 – open-plan social core
    "Spatial arrangement: OPEN SOCIAL CORE. Living, kitchen, and dining are merged "
    "into one large open-plan zone at y=0 with no internal walls between them "
    "(represent as three touching rooms with shared edges). "
    "Bedrooms cluster privately at the top behind the hallway.",

    # 5 – courtyard / haveli inspired
    "Spatial arrangement: HAVELI-INSPIRED. Rooms are arranged around three sides of "
    "a central implied courtyard (do NOT include the courtyard as a room). "
    "Veranda or living on the south-facing side (y=0). Bedrooms on the east and west "
    "arms. Kitchen at the back. Parking to one side.",
]


def _pick_layout_variant() -> str:
    return random.choice(_LAYOUT_VARIANTS)


# ── JSON extraction helpers ────────────────────────────────────────────────────

def _extract_json(text: str) -> dict:
    """
    Extract and parse a JSON object from an LLM response.
    Handles markdown code fences and extra surrounding text.
    """
    # 1. Direct parse — works when response is clean JSON
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown fences (```json ... ``` or ``` ... ```)
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. Greedy: find the outermost {...} block
    brace = re.search(r"\{[\s\S]*\}", text)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from LLM response:\n{text[:500]}")


def _validate_room_graph(data: dict) -> dict:
    """
    Validate and normalise the LLM-generated room_graph dict.
    Raises ValueError with a clear message if the structure is wrong.
    """
    if not isinstance(data, dict):
        raise ValueError("LLM output is not a JSON object")

    rooms = data.get("rooms")
    if not rooms or not isinstance(rooms, list):
        raise ValueError("LLM output missing 'rooms' list")

    required = {"type", "x", "y", "width", "height"}
    valid_types = {
        "bedroom", "bathroom", "living", "kitchen", "dining",
        "hallway", "balcony", "garden", "parking", "storage",
        "stair", "veranda", "other",
    }

    cleaned = []
    for i, r in enumerate(rooms):
        if not isinstance(r, dict):
            continue
        missing = required - r.keys()
        if missing:
            print(f"[LLM] Room {i} missing fields {missing} — skipping")
            continue
        # Normalise type to lowercase, replace spaces
        rtype = str(r["type"]).lower().strip().replace(" ", "_")
        # Map common aliases
        rtype = {
            "living_room": "living", "lounge": "living",
            "dining_room": "dining",
            "balcony": "balcony", "terrace": "balcony", "veranda": "balcony",
        }.get(rtype, rtype)
        if rtype not in valid_types:
            rtype = "other"

        cleaned.append({
            "id":     r.get("id", f"{rtype}_{i}"),
            "type":   rtype,
            "x":      round(float(r["x"]),      2),
            "y":      round(float(r["y"]),      2),
            "width":  round(max(float(r["width"]),  0.5), 2),
            "height": round(max(float(r["height"]), 0.5), 2),
            "area":   round(float(r["width"]) * float(r["height"]), 2),
        })

    if not cleaned:
        raise ValueError("LLM output contained no valid room entries")

    meta = data.get("metadata", {})
    total_area = sum(r["width"] * r["height"] for r in cleaned)

    return {
        "rooms": cleaned,
        "metadata": {
            "unit_type":    str(meta.get("unit_type", "house")),
            "total_area":   round(float(meta.get("total_area", total_area)), 1),
            "generated_by": "llm_adapter",
            "is_mock":      False,
        }
    }


# ── Custom exceptions ──────────────────────────────────────────────────────────

class _QuotaExhausted(Exception):
    """Raised when a provider returns HTTP 429 (quota / rate-limit exhausted)."""


# ── Provider implementations ───────────────────────────────────────────────────

def _call_openai(prompt: str, api_key: str, model: str,
                 base_url: Optional[str] = None) -> str:
    try:
        from openai import OpenAI, RateLimitError
    except ImportError:
        raise ImportError(
            "openai package not installed.\n"
            "Run: pip install openai"
        )
    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url

    client = OpenAI(**kwargs)
    messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
    for ex in _EXAMPLES:
        messages.append({"role": "user",      "content": ex["user"]})
        messages.append({"role": "assistant", "content": ex["assistant"]})
    messages.append({"role": "user", "content": prompt})

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.4,
            max_tokens=8192,
        )
    except RateLimitError as exc:
        raise _QuotaExhausted(str(exc)) from exc

    return resp.choices[0].message.content


def _call_anthropic(prompt: str, api_key: str, model: str) -> str:
    try:
        from anthropic import Anthropic
    except ImportError:
        raise ImportError(
            "anthropic package not installed.\n"
            "Run: pip install anthropic"
        )
    client = Anthropic(api_key=api_key)

    # Build user message that embeds few-shot examples as Human/Assistant turns
    # Anthropic uses alternating user/assistant in `messages`
    messages = []
    for ex in _EXAMPLES:
        messages.append({"role": "user",      "content": ex["user"]})
        messages.append({"role": "assistant", "content": ex["assistant"]})
    messages.append({"role": "user", "content": prompt})

    resp = client.messages.create(
        model=model,
        max_tokens=2000,
        system=_SYSTEM_PROMPT,
        messages=messages,
    )
    return resp.content[0].text


# ── Public async interface ─────────────────────────────────────────────────────

async def generate_room_layout(prompt: str) -> Dict[str, Any]:
    """
    Generate a room_graph dict from a natural language prompt.

    Returns a standard room_graph dict compatible with pipeline Layer 3+4:
        {
            "rooms": [{"id":..., "type":..., "x":..., "y":..., "width":..., "height":...}, ...],
            "metadata": {"unit_type": "house", "total_area": 120, ...}
        }

    Raises RuntimeError if no provider is configured and all fallbacks fail.
    """
    provider = os.getenv("LLM_PROVIDER", "").lower()
    api_key  = os.getenv("LLM_API_KEY",  "")
    model    = os.getenv("LLM_MODEL",    "")
    base_url = os.getenv("LLM_BASE_URL", "")

    # Groq fallback — used automatically when the primary provider hits a quota error
    _groq_key      = os.getenv("GROQ_API_KEY",   "")
    _groq_model    = os.getenv("GROQ_MODEL",      "llama-3.3-70b-versatile")
    _groq_base_url = os.getenv("GROQ_BASE_URL",   "https://api.groq.com/openai/v1")
    _has_groq      = bool(_groq_key)

    # Auto-detect provider if not set
    if not provider:
        if os.getenv("ANTHROPIC_API_KEY"):
            provider = "anthropic"
            api_key  = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        elif os.getenv("OPENAI_API_KEY"):
            provider = "openai"
            api_key  = api_key or os.getenv("OPENAI_API_KEY", "")
        else:
            raise RuntimeError(
                "No LLM provider configured.\n\n"
                "Set one of these in your .env file:\n"
                "  Option A — Groq (free, recommended):\n"
                "    LLM_PROVIDER=openai_compatible\n"
                "    LLM_API_KEY=<your groq key from console.groq.com>\n"
                "    LLM_BASE_URL=https://api.groq.com/openai/v1\n"
                "    LLM_MODEL=llama-3.3-70b-versatile\n\n"
                "  Option B — OpenAI:\n"
                "    LLM_PROVIDER=openai\n"
                "    LLM_API_KEY=<your openai key>\n\n"
                "  Option C — Anthropic:\n"
                "    LLM_PROVIDER=anthropic\n"
                "    LLM_API_KEY=<your anthropic key>\n\n"
                "  Option D — Ollama (local, fully free):\n"
                "    LLM_PROVIDER=openai_compatible\n"
                "    LLM_BASE_URL=http://localhost:11434/v1\n"
                "    LLM_MODEL=llama3.2\n"
                "    LLM_API_KEY=ollama\n"
            )

    if not model:
        model = _DEFAULTS.get(provider, "llama-3.3-70b-versatile")

    # Append a randomly-chosen layout archetype to the user prompt.
    # This drives structural variety across repeated calls with the same input.
    variant = _pick_layout_variant()
    augmented_prompt = f"{prompt}\n\n{variant}"

    loop = asyncio.get_event_loop()

    last_error: Exception | None = None
    for attempt in range(1, 4):          # up to 3 attempts
        variant           = _pick_layout_variant()
        augmented_prompt  = f"{prompt}\n\n{variant}"
        print(f"[LLM] Attempt {attempt}/3 via {provider}/{model}  [{variant[:55]}...]")

        try:
            if provider == "anthropic":
                raw = await loop.run_in_executor(
                    None, lambda: _call_anthropic(augmented_prompt, api_key, model)
                )
            elif provider in ("openai", "openai_compatible"):
                url = base_url or None
                raw = await loop.run_in_executor(
                    None, lambda: _call_openai(augmented_prompt, api_key, model, url)
                )
            else:
                raise RuntimeError(
                    f"Unknown LLM_PROVIDER: '{provider}'. "
                    "Use openai, anthropic, or openai_compatible."
                )

            print(f"[LLM] Response received ({len(raw)} chars)")
            data       = _extract_json(raw)
            room_graph = _validate_room_graph(data)
            print(f"[LLM] Generated {len(room_graph['rooms'])} rooms, "
                  f"total_area={room_graph['metadata']['total_area']}m²")
            return room_graph

        except _QuotaExhausted as exc:
            # Primary provider quota exhausted — try Groq fallback immediately (no retry)
            print(f"[LLM] Primary provider quota exhausted: {exc}")
            if not _has_groq:
                raise RuntimeError(
                    "Primary provider quota exhausted and no Groq fallback configured.\n"
                    "Add GROQ_API_KEY to your .env file."
                ) from exc
            print(f"[LLM] Switching to Groq fallback ({_groq_model})...")
            try:
                raw = await loop.run_in_executor(
                    None,
                    lambda: _call_openai(augmented_prompt, _groq_key, _groq_model, _groq_base_url),
                )
                print(f"[LLM] Groq response received ({len(raw)} chars)")
                data       = _extract_json(raw)
                room_graph = _validate_room_graph(data)
                print(f"[LLM] Groq fallback OK — {len(room_graph['rooms'])} rooms, "
                      f"total_area={room_graph['metadata']['total_area']}m²")
                return room_graph
            except Exception as groq_exc:
                raise RuntimeError(f"Groq fallback failed: {groq_exc}") from groq_exc

        except (ValueError, RuntimeError) as exc:
            last_error = exc
            print(f"[LLM] Attempt {attempt} failed: {exc} — retrying...")

    raise RuntimeError(
        f"LLM failed after 3 attempts. Last error: {last_error}"
    )


def spec_from_room_graph(room_graph: dict) -> dict:
    """
    Derive a spec dict from a room_graph so Layer 3's injection logic
    (which expects a spec) can identify what rooms are already present.
    """
    from collections import Counter
    counts = Counter(r["type"] for r in room_graph.get("rooms", []))

    # Map LLM type names → spec_converter canonical names
    return {
        "unit_type":   room_graph.get("metadata", {}).get("unit_type", "house"),
        "net_area":    float(room_graph.get("metadata", {}).get("total_area", 100)),
        "bedroom":     counts.get("bedroom",  0),
        "bathroom":    counts.get("bathroom", 0),
        "kitchen":     counts.get("kitchen",  0),
        "living_room": counts.get("living",   0),
        "dining_room": counts.get("dining",   0),
        "balcony":     counts.get("balcony",  0),
        "garden":      counts.get("garden",   0),
        "storage":     counts.get("storage",  0),
        "parking":     counts.get("parking",  0),
    }
