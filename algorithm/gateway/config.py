from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class WorkerEndpoints:
    i2i: str = os.getenv('I2I_WORKER_URL', 'http://127.0.0.1:18081')
    t2i: str = os.getenv('T2I_WORKER_URL', 'http://127.0.0.1:18082')
    t2v: str = os.getenv('T2V_WORKER_URL', 'http://127.0.0.1:18083')

    def resolve(self, scene: str) -> str:
        if scene == 'i2i':
            return self.i2i
        if scene == 't2i':
            return self.t2i
        if scene == 't2v':
            return self.t2v
        raise ValueError(f'unsupported scene: {scene}')
