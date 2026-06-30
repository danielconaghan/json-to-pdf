import copy
import json
from pathlib import Path

_DEFAULTS_PATH = Path(__file__).parent / "defaults.json"


def load_defaults():
    return json.loads(_DEFAULTS_PATH.read_text())


def deep_merge(base, override):
    """Recursively merge override into base. Arrays and primitives: override wins.
    Dicts: merged key-by-key so partial overrides preserve unspecified defaults."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result
