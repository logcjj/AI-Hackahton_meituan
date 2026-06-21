from __future__ import annotations


def validate_strategy_patch(patch_text: str) -> list[str]:
    banned = ['import requests', 'subprocess', 'open(']
    return [item for item in banned if item in patch_text]
