## A Cozinha do RatatouilleOS — Guia de Indexação Lúdico

Bem-vindo à nossa cozinha! Aqui explicamos o problema do mundo real e apontamos, no código, onde cada parte está implementada.

### Personagens do restaurante

- **Pedidos (pratos)**: são as unidades de trabalho que chegam à cozinha. No código, cada pedido é um `Job`:

```1:18:src/ratatouille/models.py
from dataclasses import dataclass

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
```

- **Cozinheiros (threads)**: são os trabalhadores que disputam o fogão. No simulador, configuramos quantos existem via `RunConfig.num_workers` e simulamos a disputa no laço principal:

```56:65:src/ratatouille/sim/engine.py
# Selecionar até num_workers jobs em sequência (não preemptivo, 1 fogão)
# Como há 1 fogão, efetivamente processamos 1 por vez; os workers
# representam threads disputando o fogão. Sem semáforo, permitimos colisões.
picked: List[Job] = []
for _ in range(config.num_workers):
    job = sched.pop()
    if job is not None:
        picked.append(job)
```

- **Fogão (seção crítica)**: é o recurso exclusivo que só aceita um prato por vez. Com semáforo, há exclusão mútua; sem semáforo, ocorrem colisões (acessos simultâneos):

```40:48:src/ratatouille/sim/engine.py
stove_lock = threading.Semaphore(1) if config.use_semaphore else None
stove_in_use = False

# ...

while pending or len(sched) > 0 or any(j.finish_time is None for j in jobs):
    # loop de simulação
```

E a diferença no processamento com/sem semáforo:

```72:93:src/ratatouille/sim/engine.py
if config.use_semaphore:
    job = picked[0]
    job.start_time = current_time
    events.append(Event(timestamp=current_time, kind="job_start", job_id=job.id))
    current_time += job.cook_time
    job.finish_time = current_time
    events.append(Event(timestamp=current_time, kind="job_finish", job_id=job.id))
else:
    # Sem semáforo: todos os picked tentam usar o fogão ao mesmo tempo
    if len(picked) > 1:
        collisions += len(picked) - 1
    max_finish = current_time
    for job in picked:
        job.start_time = current_time
        events.append(Event(timestamp=current_time, kind="job_start", job_id=job.id))
        finish = current_time + job.cook_time
        max_finish = max(max_finish, finish)
        job.finish_time = finish
        events.append(Event(timestamp=finish, kind="job_finish", job_id=job.id))
    current_time = max_finish
```

- **Escalonador (chefe de cozinha)**: decide qual prato vai ao fogão quando ele está livre.
  - FCFS (ordem de chegada):

```9:19:src/ratatouille/schedulers/fcfs.py
class FCFSScheduler:
    def __init__(self) -> None:
        self._queue: Deque[Job] = deque()

    def push(self, job: Job) -> None:
        self._queue.append(job)

    def pop(self) -> Optional[Job]:
        if not self._queue:
            return None
        return self._queue.popleft()
```

  - SJF (pega o prato mais curto primeiro):

```9:20:src/ratatouille/schedulers/sjf.py
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
```

### Como criar pratos e encher a cozinha

Usamos geradores de cargas que criam listas de `Job` com diferentes padrões de chegada e distribuições de tempos de preparo:

```10:21:src/ratatouille/generators.py
@dataclass(slots=True)
class WorkloadConfig:
    num_jobs: int
    arrival_pattern: str  # "bursty" | "poisson" | "mix" | "stress"
    cook_time_dist: str  # "uniform" | "expon_tail" | "mix"
    seed: int

def generate_jobs(config: WorkloadConfig) -> List[Job]:
    rng = np.random.default_rng(config.seed)
    # escolhe arrivals conforme o padrão
```

Exemplo prático: no CLI, definimos cenários pré-configurados para gerar pedidos e rodar todas as variantes (A–D):

```17:30:src/ratatouille/main.py
SCENARIOS: Dict[str, WorkloadConfig] = {
    "bursty": WorkloadConfig(num_jobs=40, arrival_pattern="bursty", cook_time_dist="mix", seed=123),
    "poisson": WorkloadConfig(num_jobs=60, arrival_pattern="poisson", cook_time_dist="expon_tail", seed=123),
    "mix": WorkloadConfig(num_jobs=50, arrival_pattern="mix", cook_time_dist="mix", seed=123),
    "stress": WorkloadConfig(num_jobs=120, arrival_pattern="stress", cook_time_dist="expon_tail", seed=123),
}

VARIANTS: Dict[str, Tuple[str, bool]] = {
    "A_FCFS_no_sem": ("fcfs", False),
    "B_FCFS_sem": ("fcfs", True),
    "C_SJF_no_sem": ("sjf", False),
    "D_SJF_sem": ("sjf", True),
}
```

### O relógio da cozinha (linha do tempo)

Durante a simulação, registramos eventos como início e término de pratos, o que nos permite desenhar linhas do tempo (Gantt) e calcular métricas:

```21:27:src/ratatouille/models.py
def waiting_time(self) -> Optional[float]:
    if self.start_time is None or self.ready_time is None:
        return None
    return self.start_time - self.ready_time

def turnaround_time(self) -> Optional[float]:
    if self.finish_time is None:
        return None
    return self.finish_time - self.arrival_time
```

### Por que o semáforo importa?

Sem semáforo, múltiplos cozinheiros “entram” no fogão ao mesmo tempo — isso cria colisões e resultados incoerentes. Com semáforo, só um prato ocupa o fogão por vez, garantindo correção. Essa diferença está explícita no bloco com/sem semáforo do `engine.py` e se reflete nas métricas em `outputs/summaries.csv`.

### Rode você mesmo

Para ver a cozinha em ação e gerar gráficos e resumos:

```bash
poetry run ratatouille --outputs outputs --workers 4
```


