# backend package
# IMPORTANT: sys.path must be set here — this is the FIRST
# code that runs when any `backend.*` module is imported.
import sys
from pathlib import Path

_ROOT    = Path(__file__).parent.parent.resolve()
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
