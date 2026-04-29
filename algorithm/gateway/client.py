from __future__ import annotations

from typing import Any, Dict

import httpx

from .config import WorkerEndpoints


class WorkerClient:
    def __init__(self, endpoints: WorkerEndpoints) -> None:
        self.endpoints = endpoints
        self.timeout = httpx.Timeout(connect=10.0, read=600.0, write=600.0, pool=10.0)

    async def post_encode(self, scene: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        base_url = self.endpoints.resolve(scene)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f'{base_url}/encode', json=payload)
            response.raise_for_status()
            return response.json()

    async def health(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=10.0, write=10.0, pool=5.0)) as client:
            for scene in ('i2i', 't2i', 't2v'):
                base_url = self.endpoints.resolve(scene)
                try:
                    response = await client.get(f'{base_url}/health')
                    response.raise_for_status()
                    result[scene] = response.json()
                except Exception as exc:
                    result[scene] = {'loaded': False, 'error': str(exc), 'service': scene}
        return result
