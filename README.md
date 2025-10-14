<div align="center">
  <h1>RatatouilleOS</h1>
  <p><strong>Simulador educacional de escalonamento e sincronização</strong> — FCFS vs SJF, com/sem semáforo</p>
  
  <p>
    <a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white"></a>
    <a href="#instala%C3%A7%C3%A3o"><img alt="Poetry" src="https://img.shields.io/badge/Build-Poetry-60A5FA?logo=poetry&logoColor=white"></a>
    <img alt="Status" src="https://img.shields.io/badge/status-WIP-yellow">
  </p>
</div>

## Visão geral

O RatatouilleOS modela a cozinha de um restaurante como um sistema operacional para estudar políticas de escalonamento e sincronização.

- **Pedidos**: processos com tempo de CPU (fogão)
- **Cozinheiros**: threads
- **Fogão único**: seção crítica (recurso exclusivo)
- **Semáforo**: controle de exclusão mútua
- **Escalonador**: política que decide o próximo pedido no fogão

O projeto compara FCFS e SJF, em versões com e sem semáforo, mede métricas de desempenho e gera gráficos prontos para análise.

### Destaques

- **Algoritmos**: FCFS e SJF (não-preemptivo)
- **Cargas**: bursty, Poisson, mix e stress
- **Métricas**: tempo médio de espera, turnaround, utilização e colisões (sem semáforo)
- **Saídas**: CSV/JSON e gráficos (barras, linha e Gantt)

## Demonstração rápida

Resultados gerados em `outputs/` após uma execução padrão:

![Barras de espera](outputs/bursty_wait_bars.png)

![Gantt bursty](outputs/bursty_gantt.png)

## Instalação

Pré-requisitos: Python 3.11+

### Usando Poetry (recomendado)

```bash
pip install poetry
poetry install
```

### Usando pip

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Uso rápido

O projeto expõe um CLI `ratatouille`.

```bash
# via Poetry
poetry run ratatouille --outputs outputs --workers 4

# ou, se instalado com pip -e .
ratatouille --outputs outputs --workers 4
```

Parâmetros principais:

- `--outputs`: diretório de saída para CSV/PNG (padrão: `outputs`)
- `--workers`: número de cozinheiros (threads lógicas)

Ao final, são produzidos CSVs por cenário/variante, um `summaries.csv`/`summaries.json`, e gráficos por cenário (barras), além de um Gantt de referência e uma linha de utilização.

## Estrutura do projeto

```
src/ratatouille/
  generators.py      # geração de cargas (bursty, poisson, mix, stress)
  main.py            # CLI e orquestração dos cenários/variantes
  models.py          # modelos de dados dos jobs
  plots.py           # funções de plotagem
  schedulers/        # implementações FCFS e SJF
  sim/               # motor de simulação e métricas
docs/                # documentação detalhada (arquitetura, algoritmos, etc.)
outputs/             # artefatos gerados (CSV, JSON, PNG)
```

## Métricas e cenários

Métricas: tempo médio de espera, turnaround, throughput, utilização do fogão e colisões (somente nas versões sem semáforo). Cenários: `bursty`, `poisson`, `mix` e `stress`. Cada cenário é executado nas variantes A–D:

- A: FCFS sem semáforo
- B: FCFS com semáforo
- C: SJF sem semáforo
- D: SJF com semáforo

## Desenvolvimento

Linters e tipagem:

```bash
poetry run ruff check .
poetry run mypy src
```

Notebooks (exploração/relatório):

```bash
poetry run jupyter notebook
```

## Documentação

Para detalhes aprofundados, consulte os documentos em `docs/`:

- `docs/architecture.md`
- `docs/algorithms.md`
- `docs/synchronization.md`
- `docs/metrics.md`
- `docs/implementation_plan.md`
 - `docs/indexacao.md` (guia lúdico de indexação do projeto)
 - `docs/indexacao.md` (guia lúdico de indexação do projeto)

## Licença

Este repositório é para fins educacionais. Defina uma licença antes de uso em produção (ex.: MIT).

## Autores

Lucas — contato em `pyproject.toml`.

## Resultados

Resumo quantitativo extraído de `outputs/summaries.csv` (médias por cenário/variante):

### Cenário: bursty

| Variante | Espera média | Turnaround médio | Colisões |
|---|---:|---:|---:|
| A_FCFS_no_sem | 2.49 | 5.54 | 28 |
| B_FCFS_sem | 1.24 | 3.30 | 0 |
| C_SJF_no_sem | 0.65 | 3.37 | 27 |
| D_SJF_sem | 0.12 | 2.45 | 0 |

### Cenário: poisson

| Variante | Espera média | Turnaround médio | Colisões |
|---|---:|---:|---:|
| A_FCFS_no_sem | 1.03 | 3.93 | 37 |
| B_FCFS_sem | 0.30 | 2.80 | 0 |
| C_SJF_no_sem | 0.35 | 3.06 | 35 |
| D_SJF_sem | 0.03 | 1.81 | 0 |

### Cenário: mix

| Variante | Espera média | Turnaround médio | Colisões |
|---|---:|---:|---:|
| A_FCFS_no_sem | 10.85 | 15.47 | 36 |
| B_FCFS_sem | 2.61 | 6.60 | 0 |
| C_SJF_no_sem | 1.75 | 5.87 | 36 |
| D_SJF_sem | 0.18 | 2.74 | 0 |

### Cenário: stress

| Variante | Espera média | Turnaround médio | Colisões |
|---|---:|---:|---:|
| A_FCFS_no_sem | 10.14 | 13.22 | 88 |
| B_FCFS_sem | 0.45 | 2.41 | 0 |
| C_SJF_no_sem | 1.93 | 5.03 | 88 |
| D_SJF_sem | 0.04 | 1.45 | 0 |

### Resumo geral

- **Semáforo** elimina colisões em todos os cenários e estabiliza métricas.
- **SJF com semáforo (D)** apresenta as menores esperas e turnarounds médios.
- **FCFS sem semáforo (A)** e **SJF sem semáforo (C)** exibem colisões significativas, distorcendo desempenho e violando exclusão mútua.

## Resultados

Resumo quantitativo extraído de `outputs/summaries.csv` (médias por cenário/variante):

### Cenário: bursty

| Variante | Espera média | Turnaround médio | Colisões |
|---|---:|---:|---:|
| A_FCFS_no_sem | 2.49 | 5.54 | 28 |
| B_FCFS_sem | 1.24 | 3.30 | 0 |
| C_SJF_no_sem | 0.65 | 3.37 | 27 |
| D_SJF_sem | 0.12 | 2.45 | 0 |

### Cenário: poisson

| Variante | Espera média | Turnaround médio | Colisões |
|---|---:|---:|---:|
| A_FCFS_no_sem | 1.03 | 3.93 | 37 |
| B_FCFS_sem | 0.30 | 2.80 | 0 |
| C_SJF_no_sem | 0.35 | 3.06 | 35 |
| D_SJF_sem | 0.03 | 1.81 | 0 |

### Cenário: mix

| Variante | Espera média | Turnaround médio | Colisões |
|---|---:|---:|---:|
| A_FCFS_no_sem | 10.85 | 15.47 | 36 |
| B_FCFS_sem | 2.61 | 6.60 | 0 |
| C_SJF_no_sem | 1.75 | 5.87 | 36 |
| D_SJF_sem | 0.18 | 2.74 | 0 |

### Cenário: stress

| Variante | Espera média | Turnaround médio | Colisões |
|---|---:|---:|---:|
| A_FCFS_no_sem | 10.14 | 13.22 | 88 |
| B_FCFS_sem | 0.45 | 2.41 | 0 |
| C_SJF_no_sem | 1.93 | 5.03 | 88 |
| D_SJF_sem | 0.04 | 1.45 | 0 |

### Resumo geral

- **Semáforo** elimina colisões em todos os cenários e estabiliza métricas.
- **SJF com semáforo (D)** apresenta as menores esperas e turnarounds médios.
- **FCFS sem semáforo (A)** e **SJF sem semáforo (C)** exibem colisões significativas, distorcendo desempenho e violando exclusão mútua.
