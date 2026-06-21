from __future__ import annotations

from pathlib import Path
from typing import Any


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ''
    if value[0:1] in {'"', "'"} and value[-1:] == value[0]:
        return value[1:-1]
    if value.lower() == 'true':
        return True
    if value.lower() == 'false':
        return False
    try:
        if any(ch in value for ch in ['.', 'e', 'E']):
            return float(value)
        return int(value)
    except ValueError:
        return value


def load_config(path: str | Path = 'autosolver/config.yaml') -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw_line in Path(path).read_text(encoding='utf-8').splitlines():
        line = raw_line.split('#', 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(' '))
        key, _, value = line.strip().partition(':')
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value.strip() == '':
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_scalar(value)
    return root
