from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import pandas as pd

from ..models import Job


@dataclass(slots=True)
class MetricsSummary:
    avg_waiting_time: float
    avg_turnaround_time: float
    throughput: float
    utilization: float
    max_queue: int
    collisions: int


def jobs_to_dataframe(jobs: List[Job]) -> pd.DataFrame:
    data = [
        {
            "id": j.id,
            "arrival_time": j.arrival_time,
            "cook_time": j.cook_time,
            "ready_time": j.ready_time,
            "start_time": j.start_time,
            "finish_time": j.finish_time,
            "waiting_time": j.waiting_time(),
            "turnaround_time": j.turnaround_time(),
        }
        for j in jobs
    ]
    return pd.DataFrame(data)


def summarize(jobs: List[Job], utilization: float, collisions: int) -> MetricsSummary:
    df = jobs_to_dataframe(jobs)
    avg_wait = float(df["waiting_time"].mean()) if not df.empty else 0.0
    avg_turn = float(df["turnaround_time"].mean()) if not df.empty else 0.0
    makespan = float(df["finish_time"].max()) if not df.empty else 0.0
    throughput = (len(df) / makespan) if makespan > 0 else 0.0
    # max_queue: proxy simples usando ordenação por start_time
    max_queue = _estimate_max_queue(df)
    return MetricsSummary(
        avg_waiting_time=avg_wait,
        avg_turnaround_time=avg_turn,
        throughput=throughput,
        utilization=utilization,
        max_queue=max_queue,
        collisions=collisions,
    )


def _estimate_max_queue(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    starts = df.sort_values("start_time")["start_time"].tolist()
    arrivals = df.sort_values("arrival_time")["arrival_time"].tolist()
    i = j = 0
    current = maxq = 0
    while i < len(starts) and j < len(arrivals):
        if arrivals[j] <= starts[i]:
            current += 1
            maxq = max(maxq, current)
            j += 1
        else:
            current = max(0, current - 1)
            i += 1
    return maxq



