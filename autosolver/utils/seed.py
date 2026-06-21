from __future__ import annotations

import hashlib


def stable_hash(value: object) -> int:
    text = str(value).encode("utf-8")
    digest = hashlib.sha256(text).digest()
    return int.from_bytes(digest[:8], "big") & 0x7FFFFFFF


def get_seed(instance, module_name: str, fallback_seed: int = 42) -> int:
    instance_id = getattr(instance, "id", None)
    if instance_id is None:
        return fallback_seed
    return stable_hash(f"{instance_id}::{module_name}")
