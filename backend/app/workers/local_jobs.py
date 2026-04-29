from __future__ import annotations

import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from subprocess import Popen
from typing import Any, Callable


@dataclass
class JobControl:
    job_id: str
    cancel_event: threading.Event = field(default_factory=threading.Event)
    future: Future | None = None
    processes: list[Popen] = field(default_factory=list)


class LocalJobRunner:
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._controls: dict[str, JobControl] = {}
        self._lock = threading.Lock()

    def submit(self, job_id: str, fn: Callable[..., Any], *args, **kwargs) -> Future:
        control = JobControl(job_id=job_id)
        with self._lock:
            self._controls[job_id] = control

        def wrapped() -> Any:
            try:
                return fn(*args, cancel_event=control.cancel_event, **kwargs)
            finally:
                with self._lock:
                    stored = self._controls.get(job_id)
                    if stored is control:
                        self._controls.pop(job_id, None)

        future = self.executor.submit(wrapped)
        control.future = future
        return future

    def request_terminate(self, job_id: str) -> bool:
        with self._lock:
            control = self._controls.get(job_id)
        if not control:
            return False
        control.cancel_event.set()
        for proc in list(control.processes):
            try:
                if proc.poll() is None:
                    proc.terminate()
            except Exception:
                pass
        if control.future and not control.future.running():
            control.future.cancel()
        return True

    def is_cancelled(self, job_id: str) -> bool:
        with self._lock:
            control = self._controls.get(job_id)
        return bool(control and control.cancel_event.is_set())

    def register_process(self, job_id: str, process: Popen) -> None:
        with self._lock:
            control = self._controls.get(job_id)
            if not control:
                return
            control.processes.append(process)

    def unregister_process(self, job_id: str, process: Popen) -> None:
        with self._lock:
            control = self._controls.get(job_id)
            if not control:
                return
            control.processes = [p for p in control.processes if p is not process]

    def shutdown(self) -> None:
        with self._lock:
            controls = list(self._controls.values())
        for control in controls:
            control.cancel_event.set()
            for proc in list(control.processes):
                try:
                    if proc.poll() is None:
                        proc.terminate()
                except Exception:
                    pass
        self.executor.shutdown(wait=False, cancel_futures=True)
