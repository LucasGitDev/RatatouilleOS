from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional, Tuple

from ..models import Event, Job
from ..schedulers.fcfs import FCFSScheduler
from ..schedulers.sjf import SJFScheduler


@dataclass(slots=True)
class RunConfig:
    num_workers: int
    scheduler: str  # "fcfs" | "sjf"
    use_semaphore: bool


@dataclass(slots=True)
class RunResult:
    events: List[Event]
    jobs: List[Job]
    collisions: int
    stove_utilization: float


def run_simulation(jobs: List[Job], config: RunConfig) -> RunResult:
    # Escolha do escalonador
    if config.scheduler == "fcfs":
        sched = FCFSScheduler()
    elif config.scheduler == "sjf":
        sched = SJFScheduler()
    else:
        raise ValueError("scheduler inválido")

    # Eventos e controle
    events: List[Event] = []
    collisions = 0
    stove_lock = threading.Semaphore(1) if config.use_semaphore else None
    stove_in_use = False

    # Ordena por chegada para liberar inicialmente
    pending = sorted(jobs, key=lambda j: j.arrival_time)
    current_time = 0.0

    # Simulação discreta com workers lógicos (não real time)
    # Loop até todos os jobs finalizarem
    while pending or len(sched) > 0 or any(j.finish_time is None for j in jobs):
        # Liberar chegadas
        while pending and pending[0].arrival_time <= current_time:
            job = pending.pop(0)
            job.ready_time = max(job.arrival_time, current_time)
            sched.push(job)

        # Selecionar até num_workers jobs em sequência (não preemptivo, 1 fogão)
        # Como há 1 fogão, efetivamente processamos 1 por vez; os workers
        # representam threads disputando o fogão. Sem semáforo, permitimos colisões.
        picked: List[Job] = []
        for _ in range(config.num_workers):
            job = sched.pop()
            if job is not None:
                picked.append(job)

        if not picked and pending:
            # Avança tempo até próxima chegada
            current_time = pending[0].arrival_time
            continue
        if not picked and not pending:
            break

        # Semáforo: só um job pode usar o fogão por vez
        if config.use_semaphore:
            job = picked[0]
            # Devolve demais jobs para a fila, já que apenas 1 pode usar o fogão
            for rest in picked[1:]:
                sched.push(rest)
            # Chef mais simples: índice 0 neste tick
            events.append(Event(timestamp=current_time, kind="chef_pick", job_id=job.id, chef_id=0))
            job.start_time = current_time
            events.append(Event(timestamp=current_time, kind="job_start", job_id=job.id))
            current_time += job.cook_time
            job.finish_time = current_time
            events.append(Event(timestamp=current_time, kind="job_finish", job_id=job.id))
        else:
            # Sem semáforo: todos os picked tentam usar o fogão ao mesmo tempo
            # Simulamos colisões: se mais de 1 picked, contam overlaps.
            if len(picked) > 1:
                collisions += len(picked) - 1
            max_finish = current_time
            for job in picked:
                events.append(Event(timestamp=current_time, kind="chef_pick", job_id=job.id, chef_id=0))
                job.start_time = current_time
                events.append(Event(timestamp=current_time, kind="job_start", job_id=job.id))
                finish = current_time + job.cook_time
                max_finish = max(max_finish, finish)
                job.finish_time = finish
                events.append(Event(timestamp=finish, kind="job_finish", job_id=job.id))
            if len(picked) > 1:
                # Evento explícito de colisão para visual
                events.append(Event(timestamp=current_time, kind="collision", job_id=None, chef_id=None))
            current_time = max_finish

    # Utilização do fogão: total de tempo ocupado / makespan
    makespan = max(j.finish_time or 0.0 for j in jobs) if jobs else 0.0
    busy = sum(j.cook_time for j in jobs)
    utilization = (busy / makespan) if makespan > 0 else 0.0

    return RunResult(events=events, jobs=jobs, collisions=collisions, stove_utilization=utilization)



