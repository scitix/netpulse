from typing import Any

from .config import initialize_config

g_config = initialize_config()


def mask_sensitive_data(data: Any) -> Any:
    """
    Recursively mask sensitive information in dictionaries or lists.
    """
    if isinstance(data, dict):
        masked = {}
        for k, v in data.items():
            if k.lower() in {"password", "secret", "private_key", "token"}:
                masked[k] = "******"
            else:
                masked[k] = mask_sensitive_data(v)
        return masked
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    return data
