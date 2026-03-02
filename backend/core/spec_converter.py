"""
Spec Converter — bridges Layer 1 (NLP) output to Layer 2 (GNN) input.

Layer 1 outputs a dict like:
    {"unit_type": "house", "net_area": 120, "bedroom": 3, "bathroom": 2,
     "living": 1, "kitchen": 1, "balcony": 1, ...}

Layer 2 expects an 18-dimensional condition vector:
    [unit_type_one_hot (5), net_area_norm (1), room_counts (12)]

Room types order (12):  bedroom, bathroom, living, kitchen, balcony,
                        storage, parking, garden, pool, stair, veranda, inner
Unit types order (5):   house, apartment, villa, commercial, other
"""

import numpy as np
from typing import Dict, Any

UNIT_TYPES  = ["house", "apartment", "villa", "commercial", "other"]
ROOM_TYPES  = ["bedroom", "bathroom", "living", "kitchen", "balcony",
               "storage", "parking", "garden", "pool", "stair", "veranda", "inner"]

# Normalization constants (based on ResPlan dataset statistics)
MAX_AREA        = 500.0   # m² — clamp and normalize
MAX_ROOM_COUNT  = 8       # max reasonable count per type

CONDITION_DIM   = 18      # 5 (unit) + 1 (area) + 12 (rooms)


def spec_to_condition_vector(spec: Dict[str, Any]) -> np.ndarray:
    """
    Convert NLP output spec dict → 18-dim float32 condition vector.

    Args:
        spec: Dict from NLP Layer 1 output

    Returns:
        numpy array of shape (18,), dtype float32
    """
    vec = np.zeros(CONDITION_DIM, dtype=np.float32)

    # ── Unit type one-hot (dims 0–4) ──────────────────────────────────────────
    unit = str(spec.get("unit_type", "other")).lower()
    if unit not in UNIT_TYPES:
        unit = "other"
    vec[UNIT_TYPES.index(unit)] = 1.0

    # ── Normalised area (dim 5) ───────────────────────────────────────────────
    area = float(spec.get("net_area", 100.0))
    vec[5] = min(area / MAX_AREA, 1.0)

    # ── Room counts (dims 6–17) ───────────────────────────────────────────────
    for i, room in enumerate(ROOM_TYPES):
        count = int(spec.get(room, 0))
        # Also accept old-style keys (living_room, bathroom → bathroom)
        if count == 0:
            legacy = {"living": "living_room", "bathroom": "bathrooms",
                      "bedroom": "bedrooms"}.get(room)
            if legacy:
                count = int(spec.get(legacy, 0))
        vec[6 + i] = min(count / MAX_ROOM_COUNT, 1.0)

    return vec


def condition_vector_to_spec(vec: np.ndarray) -> Dict[str, Any]:
    """
    Reverse: decode a condition vector back to a human-readable spec dict.
    Useful for debugging and logging.
    """
    unit_idx  = int(np.argmax(vec[:5]))
    unit_type = UNIT_TYPES[unit_idx]
    net_area  = float(vec[5]) * MAX_AREA

    spec = {
        "unit_type": unit_type,
        "net_area":  round(net_area, 1),
    }
    for i, room in enumerate(ROOM_TYPES):
        count = round(float(vec[6 + i]) * MAX_ROOM_COUNT)
        spec[room] = max(0, count)

    return spec


def normalise_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fill in missing keys with sensible defaults so Layer 2 always
    receives a complete spec regardless of what Layer 1 produced.
    """
    out = {
        "unit_type": spec.get("unit_type", "house"),
        "net_area":  float(spec.get("net_area", 100)),
        "bedroom":   int(spec.get("bedroom", spec.get("bedrooms", 2))),
        "bathroom":  int(spec.get("bathroom", spec.get("bathrooms", 1))),
        "living":    int(spec.get("living",   spec.get("living_room", 1))),
        "kitchen":   int(spec.get("kitchen",  1)),
        "balcony":   int(spec.get("balcony",  0)),
        "storage":   int(spec.get("storage",  0)),
        "parking":   int(spec.get("parking",  0)),
        "garden":    int(spec.get("garden",   0)),
        "pool":      int(spec.get("pool",     0)),
        "stair":     int(spec.get("stair",    0)),
        "veranda":   int(spec.get("veranda",  0)),
        "inner":     int(spec.get("inner",    0)),
    }
    return out


if __name__ == "__main__":
    test = {
        "unit_type": "house", "net_area": 150,
        "bedroom": 3, "bathroom": 2, "living": 1, "kitchen": 1,
        "balcony": 1, "storage": 0, "parking": 1, "garden": 1,
        "pool": 0, "stair": 0, "veranda": 1, "inner": 1,
    }
    vec = spec_to_condition_vector(test)
    print(f"Condition vector (dim={len(vec)}): {vec}")
    recovered = condition_vector_to_spec(vec)
    print(f"Recovered spec: {recovered}")
