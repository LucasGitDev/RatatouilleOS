from __future__ import annotations

from collections import deque
from typing import Deque, Optional

from ..models import Job


class FCFSScheduler:
    def __init__(self) -> None:
        self._queue: Deque[Job] = deque()

    def push(self, job: Job) -> None:
        self._queue.append(job)

    def push_front(self, job: Job) -> None:
        """Adiciona job no início da fila (para devolver jobs rejeitados pelo semáforo)"""
        self._queue.appendleft(job)

    def pop(self) -> Optional[Job]:
        if not self._queue:
            return None
        return self._queue.popleft()

    def __len__(self) -> int:  # pragma: no cover
        return len(self._queue)



