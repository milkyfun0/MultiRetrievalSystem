from __future__ import annotations

from typing import Any, Dict, List, Optional


def encode_response(
    scene: str,
    *,
    query: Optional[str] = None,
    query_embed: Optional[List[float]] = None,
    key_embed: Optional[List[List[float]]] = None,
    trace_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        'scence': scene,
        'key_embed': key_embed or [],
    }
    if query is not None:
        data['query'] = query
    if query_embed is not None:
        data['query_embed'] = query_embed
    if trace_id is not None:
        data['trace_id'] = trace_id
    if extra:
        data.update(extra)
    return data


def health_response(name: str, loaded: bool, cwd: str, detail: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        'service': name,
        'loaded': loaded,
        'cwd': cwd,
    }
    if detail:
        payload['detail'] = detail
    return payload
