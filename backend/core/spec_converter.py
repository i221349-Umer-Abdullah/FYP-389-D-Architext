"""
Spec Converter — bridges Layer 1 (NLP) output to Layer 2 (GNN) input.

Condition vector format (18-dim) — must EXACTLY match preprocess_dataset.py:
  [0]     bedroom count   / 5.0
  [1]     bathroom count  / 5.0
  [2]     kitchen count   / 5.0
  [3]     living_room count / 5.0
  [4]     dining_room count / 5.0
  [5]     balcony count   / 5.0
  [6]     garden count    / 5.0
  [7]     storage count   / 5.0
  [8]     parking count   / 5.0
  [9]     total_rooms / max_nodes (16)
  [10]    is_apartment
  [11]    is_house
  [12:18] padding zeros
"""

import numpy as np
from typing import Dict, Any

# ── Constants (MUST stay in sync with preprocess_dataset.py) ──────────────────
COND_ROOM_KEYS = [
    'bedroom', 'bathroom', 'kitchen', 'living_room',
    'dining_room', 'balcony', 'garden', 'storage', 'parking',
]
MAX_ROOM_COUNT  = 5       # normaliser denominator
MAX_NODES       = 16      # for total_rooms_norm
CONDITION_DIM   = 18

# NLP key aliases → canonical COND_ROOM_KEYS
_NLP_ALIASES = {
    'living':       'living_room',
    'living room':  'living_room',
    'drawing room': 'living_room',
    'drawing_room': 'living_room',
    'lounge':       'living_room',
    'dining':       'dining_room',
    'dining room':  'dining_room',
    'terrace':      'balcony',
    'veranda':      'balcony',
    'yard':         'garden',
    'garage':       'parking',
    'utility':      'storage',
    'closet':       'storage',
    'storageroom':  'storage',
}


def _resolve_key(key: str) -> str:
    """Map any NLP output key to a canonical COND_ROOM_KEY."""
    k = key.lower().strip().replace(' ', '_')
    return _NLP_ALIASES.get(k, _NLP_ALIASES.get(key.lower().strip(), k))


def spec_to_condition_vector(spec: Dict[str, Any]) -> np.ndarray:
    """
    Convert NLP output spec dict → 18-dim float32 condition vector.

    Handles both old-style NLP keys (living, veranda, stair etc.) and
    new canonical keys (living_room, dining_room etc.) transparently.
    """
    vec = np.zeros(CONDITION_DIM, dtype=np.float32)

    # Gather all room counts, resolving aliases
    resolved: Dict[str, int] = {}
    for k, v in spec.items():
        if k in ('unit_type', 'net_area'):
            continue
        canonical = _resolve_key(k)
        if canonical in COND_ROOM_KEYS:
            resolved[canonical] = resolved.get(canonical, 0) + int(v or 0)

    # Fill condition vector
    total_rooms = 0
    for i, key in enumerate(COND_ROOM_KEYS):
        count = resolved.get(key, 0)
        vec[i] = min(count / MAX_ROOM_COUNT, 1.0)
        total_rooms += count

    vec[9]  = min(total_rooms / MAX_NODES, 1.0)

    unit = str(spec.get('unit_type', 'house')).lower()
    vec[10] = 1.0 if 'apartment' in unit or 'flat' in unit else 0.0
    vec[11] = 1.0 if 'house' in unit or 'villa' in unit or unit == '' else 0.0

    # [12:18] stays zero (padding)
    return vec


def normalise_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fill in missing keys with sensible defaults so Layer 2 always
    receives a complete spec regardless of what Layer 1 produced.
    Maps old-style keys (living, veranda, etc.) to canonical names.
    """
    # Resolve sums for each canonical key
    resolved: Dict[str, int] = {k: 0 for k in COND_ROOM_KEYS}
    for k, v in spec.items():
        canonical = _resolve_key(k)
        if canonical in COND_ROOM_KEYS:
            resolved[canonical] = max(resolved.get(canonical, 0), int(v or 0))

    # Ensure living_room defaults to 1 if nothing social is present
    if resolved.get('living_room', 0) == 0 and resolved.get('dining_room', 0) == 0:
        resolved['living_room'] = 1

    # Ensure at least 1 kitchen
    if resolved.get('kitchen', 0) == 0:
        resolved['kitchen'] = 1

    out = {
        'unit_type': spec.get('unit_type', 'house'),
        'net_area':  float(spec.get('net_area', 100)),
    }
    out.update(resolved)
    return out


def condition_vector_to_spec(vec: np.ndarray) -> Dict[str, Any]:
    """Reverse: decode condition vector back to human-readable spec (for debugging)."""
    spec = {
        'total_rooms_norm': float(vec[9]),
        'is_apartment': bool(vec[10] > 0.5),
        'is_house':     bool(vec[11] > 0.5),
    }
    for i, key in enumerate(COND_ROOM_KEYS):
        spec[key] = round(float(vec[i]) * MAX_ROOM_COUNT)
    return spec


if __name__ == '__main__':
    test = {
        'unit_type': 'house', 'net_area': 150,
        'bedroom': 3, 'bathroom': 2, 'living': 1, 'kitchen': 1,
        'balcony': 1, 'dining room': 1, 'parking': 1,
    }
    vec = spec_to_condition_vector(test)
    print(f'Condition vector (dim={len(vec)}):')
    for i, v in enumerate(vec):
        label = COND_ROOM_KEYS[i] if i < len(COND_ROOM_KEYS) else f'dim{i}'
        print(f'  [{i}] {label:15s} = {v:.3f}')
    print(f'\nRecovered: {condition_vector_to_spec(vec)}')
