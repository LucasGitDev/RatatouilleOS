from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence
import numpy as np

from .models import Job


@dataclass(slots=True)
class WorkloadConfig:
    num_jobs: int
    arrival_pattern: str  # "bursty" | "poisson" | "mix" | "stress"
    cook_time_dist: str  # "uniform" | "expon_tail" | "mix"
    seed: int


def generate_jobs(config: WorkloadConfig) -> List[Job]:
    rng = np.random.default_rng(config.seed)

    if config.arrival_pattern == "bursty":
        arrivals = _arrivals_bursty(rng, config.num_jobs)
    elif config.arrival_pattern == "poisson":
        arrivals = _arrivals_poisson(rng, rate=1.0, n=config.num_jobs)
    elif config.arrival_pattern == "mix":
        a1 = _arrivals_bursty(rng, config.num_jobs // 2)
        a2 = _arrivals_poisson(rng, rate=0.7, n=config.num_jobs - len(a1))
        arrivals = np.sort(np.concatenate([a1, a2]))
    elif config.arrival_pattern == "stress":
        arrivals = _arrivals_poisson(rng, rate=2.0, n=config.num_jobs)
    else:
        raise ValueError("arrival_pattern inválido")

    if config.cook_time_dist == "uniform":
        cook_times = rng.uniform(0.5, 4.0, size=config.num_jobs)
    elif config.cook_time_dist == "expon_tail":
        cook_times = np.clip(rng.exponential(scale=1.5, size=config.num_jobs), 0.2, 12.0)
    elif config.cook_time_dist == "mix":
        u = rng.uniform(0.5, 3.0, size=config.num_jobs // 2)
        e = np.clip(rng.exponential(scale=2.0, size=config.num_jobs - len(u)), 0.2, 15.0)
        cook_times = np.concatenate([u, e])
        rng.shuffle(cook_times)
    else:
        raise ValueError("cook_time_dist inválido")

    jobs = [
        Job(id=i+1, arrival_time=float(arrivals[i]), cook_time=float(cook_times[i]))
        for i in range(config.num_jobs)
    ]
    return jobs


def _arrivals_bursty(rng: np.random.Generator, n: int) -> np.ndarray:
    bursts = max(1, n // 5)
    times: List[float] = []
    current = 0.0
    for _ in range(bursts):
        k = max(1, n // bursts)
        times.extend([current] * k)
        current += float(rng.uniform(2.0, 5.0))
    arr = np.array(times[:n], dtype=float)
    return np.sort(arr)


def _arrivals_poisson(rng: np.random.Generator, rate: float, n: int) -> np.ndarray:
    gaps = rng.exponential(1.0 / rate, size=n)
    return np.cumsum(gaps).astype(float)


