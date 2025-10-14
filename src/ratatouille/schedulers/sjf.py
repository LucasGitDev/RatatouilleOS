from __future__ import annotations

import heapq
from typing import List, Optional, Tuple

from ..models import Job


class SJFScheduler:
    def __init__(self) -> None:
        self._heap: List[Tuple[float, int, Job]] = []

    def push(self, job: Job) -> None:
        heapq.heappush(self._heap, (job.cook_time, job.id, job))

    def pop(self) -> Optional[Job]:
        if not self._heap:
            return None
        _, _, job = heapq.heappop(self._heap)
        return job

    def __len__(self) -> int:  # pragma: no cover
        return len(self._heap)



