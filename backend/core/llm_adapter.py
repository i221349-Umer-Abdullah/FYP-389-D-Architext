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
_SYSTEM_PROMPT = """You are an expert residential architect. Given a description of a house or apartment, output a JSON floor plan layout with realistic room positions and sizes.

STRICT RULES:
1. All x, y, width, height values are in METRES.
2. Rooms must NOT overlap — check every pair before outputting.
3. Adjacent rooms should share a wall edge (one room's right edge == neighbour's left edge, etc.).
4. Start the layout near x=0, y=0. x increases rightward, y increases upward.
5. Arrange logically: living + kitchen near entry (low y), bedrooms grouped at higher y, bathrooms near bedrooms.
6. Keep the overall footprint compact and roughly rectangular.

REALISTIC ROOM SIZES (width × depth):
  living room : 4.5–6.0 × 4.0–5.0 m
  kitchen     : 2.5–4.0 × 2.5–3.5 m
  dining      : 3.0–4.0 × 2.5–3.5 m
  bedroom     : 3.0–4.5 × 3.0–4.0 m  (master can be up to 5.0 × 4.5)
  bathroom    : 1.8–2.5 × 1.8–2.5 m
  hallway     : 1.2–2.0 × 2.0–4.0 m
  balcony     : 1.5–3.0 × 1.0–2.0 m  (attached to outer edge)
  garden      : 3.0–6.0 × 3.0–5.0 m
  parking     : 2.5–3.5 × 4.5–6.0 m
  storage     : 1.2–2.5 × 1.2–2.5 m
  stair       : 2.0–2.5 × 2.5–3.5 m
  veranda     : 2.0–4.0 × 1.5–2.5 m

VALID room type strings: bedroom, bathroom, living, kitchen, dining, hallway, balcony, garden, parking, storage, stair, veranda

OUTPUT: Return ONLY the JSON object below. No markdown fences, no explanation.
{"rooms":[{"id":"TYPE_INDEX","type":"TYPE","x":X,"y":Y,"width":W,"height":H},...], "metadata":{"unit_type":"house","total_area":AREA}}"""

# ── Few-shot examples ──────────────────────────────────────────────────────────
# Carefully verified: zero overlaps, walls touching, realistic sizes.
_EXAMPLES = [
    {
        "user": "A 2 bedroom house with 1 bathroom, a living room, kitchen, and a small garden",
        "assistant": json.dumps({
            "rooms": [
                {"id": "living_0",   "type": "living",   "x": 0.0, "y": 0.0, "width": 5.0, "height": 4.0},
                {"id": "kitchen_1",  "type": "kitchen",  "x": 5.0, "y": 0.0, "width": 3.0, "height": 4.0},
                {"id": "hallway_2",  "type": "hallway",  "x": 0.0, "y": 4.0, "width": 2.0, "height": 2.0},
                {"id": "bathroom_3", "type": "bathroom", "x": 2.0, "y": 4.0, "width": 2.0, "height": 2.0},
                {"id": "bedroom_4",  "type": "bedroom",  "x": 4.0, "y": 4.0, "width": 4.0, "height": 3.5},
                {"id": "bedroom_5",  "type": "bedroom",  "x": 0.0, "y": 6.0, "width": 4.0, "height": 3.5},
                {"id": "garden_6",   "type": "garden",   "x": 4.0, "y": 7.5, "width": 4.0, "height": 4.0}
            ],
            "metadata": {"unit_type": "house", "total_area": 92}
        }, separators=(',', ':'))
    },
    {
        "user": "A 3 bedroom house with 2 bathrooms, open plan living and kitchen, dining room, and a balcony",
        "assistant": json.dumps({
            "rooms": [
                {"id": "living_0",    "type": "living",   "x": 0.0, "y": 0.0, "width": 5.5, "height": 4.5},
                {"id": "kitchen_1",   "type": "kitchen",  "x": 5.5, "y": 0.0, "width": 3.5, "height": 3.0},
                {"id": "dining_2",    "type": "dining",   "x": 5.5, "y": 3.0, "width": 3.5, "height": 3.0},
                {"id": "balcony_3",   "type": "balcony",  "x": 9.0, "y": 0.0, "width": 2.0, "height": 3.0},
                {"id": "hallway_4",   "type": "hallway",  "x": 0.0, "y": 4.5, "width": 2.0, "height": 2.5},
                {"id": "bathroom_5",  "type": "bathroom", "x": 2.0, "y": 4.5, "width": 2.0, "height": 2.5},
                {"id": "bathroom_6",  "type": "bathroom", "x": 4.0, "y": 4.5, "width": 2.5, "height": 2.5},
                {"id": "bedroom_7",   "type": "bedroom",  "x": 0.0, "y": 7.0, "width": 3.5, "height": 3.5},
                {"id": "bedroom_8",   "type": "bedroom",  "x": 3.5, "y": 7.0, "width": 3.5, "height": 3.5},
                {"id": "bedroom_9",   "type": "bedroom",  "x": 7.0, "y": 7.0, "width": 4.0, "height": 3.5}
            ],
            "metadata": {"unit_type": "house", "total_area": 132}
        }, separators=(',', ':'))
    },
]


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


# ── Provider implementations ───────────────────────────────────────────────────

def _call_openai(prompt: str, api_key: str, model: str,
                 base_url: Optional[str] = None) -> str:
    try:
        from openai import OpenAI
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

    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
        max_tokens=2000,
    )
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

    print(f"[LLM] Generating layout via {provider} / {model}")

    # Run the blocking API call in a thread so it doesn't block the event loop
    loop = asyncio.get_event_loop()

    if provider == "anthropic":
        raw = await loop.run_in_executor(
            None, lambda: _call_anthropic(prompt, api_key, model)
        )
    elif provider in ("openai", "openai_compatible"):
        url = base_url or None
        raw = await loop.run_in_executor(
            None, lambda: _call_openai(prompt, api_key, model, url)
        )
    else:
        raise RuntimeError(f"Unknown LLM_PROVIDER: '{provider}'. Use openai, anthropic, or openai_compatible.")

    print(f"[LLM] Response received ({len(raw)} chars)")

    data       = _extract_json(raw)
    room_graph = _validate_room_graph(data)

    print(f"[LLM] Generated {len(room_graph['rooms'])} rooms, "
          f"total_area={room_graph['metadata']['total_area']}m²")

    return room_graph


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
