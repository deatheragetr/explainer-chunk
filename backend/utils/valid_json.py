from typing import Any
import json

def is_valid_json(string: Any) -> bool:
    try:
        if string is None:
            return False
        json.loads(string)
        return True
    except json.JSONDecodeError:
        return False
