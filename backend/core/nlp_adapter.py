"""
NLP Adapter — Layer 1 wrapper.

Loads the fine-tuned T5 model and wraps it for use in the pipeline.
Falls back to a rule-based extractor if the model weights aren't present.
"""

import os
import re
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

NLP_MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "nlp_t5" / "final_model"


class NLPAdapter:
    """
    Wraps the T5-based NLP model (Layer 1) for the pipeline.
    Falls back to rule-based extraction if model isn't trained/available.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path  = Path(model_path) if model_path else NLP_MODEL_PATH
        self._model      = None
        self._tokenizer  = None
        self.is_fallback = False
        self._load()

    def _load(self):
        """Try to load T5 model; fall back to regex if unavailable."""
        if not self.model_path.exists():
            print(f"[NLP] Model not found at {self.model_path} — using rule-based fallback")
            self.is_fallback = True
            return

        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
            from inference_nlp import TextToSpecInference
            self._model      = TextToSpecInference(str(self.model_path))
            self.is_fallback = False
            print(f"[NLP] T5 model loaded from {self.model_path}")
        except Exception as e:
            print(f"[NLP] Failed to load T5 model ({e}) — using rule-based fallback")
            self.is_fallback = True

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parse a natural language description into a structured spec dict.

        Returns a dict compatible with spec_converter.normalise_spec().
        """
        if not self.is_fallback and self._model is not None:
            try:
                result = self._model.predict(text)
                if isinstance(result, dict) and result:
                    return result
            except Exception as e:
                print(f"[NLP] Inference error ({e}), falling back to regex")

        return self._fallback_parse(text)

    @staticmethod
    def _fallback_parse(text: str) -> Dict[str, Any]:
        """
        Rule-based extraction from text when T5 model isn't available.
        Handles common patterns like '3 bedroom house' / '5 marla' / 'with balcony'.
        """
        t = text.lower()
        spec: Dict[str, Any] = {}

        # Unit type
        if any(w in t for w in ["villa", "farmhouse", "manor", "estate"]):
            spec["unit_type"] = "villa"
        elif any(w in t for w in ["apartment", "flat", "condo", "penthouse", "unit"]):
            spec["unit_type"] = "apartment"
        else:
            spec["unit_type"] = "house"

        # Bedroom count
        m = re.search(r'(\d+)\s*(?:bed(?:room)?s?|br|bhk)', t)
        spec["bedroom"] = int(m.group(1)) if m else 2

        # Bathroom count
        m = re.search(r'(\d+)\s*(?:bath(?:room)?s?|ba\b|washroom)', t)
        spec["bathroom"] = int(m.group(1)) if m else 1

        # Area
        m = re.search(r'(\d+(?:\.\d+)?)\s*marla', t)
        if m:
            spec["net_area"] = round(float(m.group(1)) * 25.2)  # 1 marla ≈ 25.2 m²
        else:
            m = re.search(r'(\d+)\s*(?:sqm|sq\.?\s*m(?:etre|eter)?s?|m2)', t)
            if m:
                spec["net_area"] = int(m.group(1))
            else:
                m = re.search(r'(\d+)\s*(?:sq\.?\s*ft|sqft)', t)
                if m:
                    spec["net_area"] = round(int(m.group(1)) * 0.0929)
                else:
                    spec["net_area"] = 60 + spec["bedroom"] * 28

        # Fixed rooms
        spec["living"]  = 1
        spec["kitchen"] = 1
        spec["inner"]   = 1 if spec["bedroom"] >= 3 else 0

        # Optional rooms from keywords
        spec["balcony"]  = 1 if re.search(r'balcon', t) else 0
        spec["veranda"]  = 1 if re.search(r'veranda|porch', t) else 0
        spec["garden"]   = 1 if re.search(r'garden|lawn|yard', t) else 0
        spec["pool"]     = 1 if re.search(r'\bpool\b|swimming', t) else 0
        spec["storage"]  = 1 if re.search(r'storage|store\s*room', t) else 0
        spec["parking"]  = 1 if re.search(r'park|garage|car\s*port', t) else 0
        spec["stair"]    = 1 if re.search(r'stair|two\s*stor|2\s*stor|double\s*stor', t) else 0

        return spec


# Singleton — used by pipeline
_nlp_adapter: Optional[NLPAdapter] = None

def get_nlp_adapter() -> NLPAdapter:
    global _nlp_adapter
    if _nlp_adapter is None:
        _nlp_adapter = NLPAdapter()
    return _nlp_adapter
