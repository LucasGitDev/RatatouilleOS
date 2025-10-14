from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class Job:
    id: int
    arrival_time: float
    cook_time: float
    prep_time: float = 0.0

    # Timestamps preenchidos durante simulação
    ready_time: Optional[float] = None
    start_time: Optional[float] = None
    finish_time: Optional[float] = None

    def waiting_time(self) -> Optional[float]:
        if self.start_time is None or self.ready_time is None:
            return None
        return self.start_time - self.ready_time

    def turnaround_time(self) -> Optional[float]:
        if self.finish_time is None:
            return None
        return self.finish_time - self.arrival_time


@dataclass(slots=True)
class Event:
    timestamp: float
    kind: str  # e.g., "job_start", "job_finish", "collision", "chef_pick"
    job_id: Optional[int] = None
    chef_id: Optional[int] = None


