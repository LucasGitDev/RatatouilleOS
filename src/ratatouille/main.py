from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

from .generators import WorkloadConfig, generate_jobs
from .plots import plot_bars, plot_gantt, plot_line
from .sim.engine import RunConfig, run_simulation
from .sim.metrics import jobs_to_dataframe, summarize


SCENARIOS: Dict[str, WorkloadConfig] = {
    "bursty": WorkloadConfig(num_jobs=40, arrival_pattern="bursty", cook_time_dist="mix", seed=123),
    "poisson": WorkloadConfig(num_jobs=60, arrival_pattern="poisson", cook_time_dist="expon_tail", seed=123),
    "mix": WorkloadConfig(num_jobs=50, arrival_pattern="mix", cook_time_dist="mix", seed=123),
    "stress": WorkloadConfig(num_jobs=120, arrival_pattern="stress", cook_time_dist="expon_tail", seed=123),
}

# Variações A–D
VARIANTS: Dict[str, Tuple[str, bool]] = {
    "A_FCFS_no_sem": ("fcfs", False),
    "B_FCFS_sem": ("fcfs", True),
    "C_SJF_no_sem": ("sjf", False),
    "D_SJF_sem": ("sjf", True),
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RatatouilleOS: simulação de escalonamento e sincronização"
    )
    parser.add_argument(
        "--outputs",
        type=str,
        default="outputs",
        help="Diretório de saída para CSV/PNG",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Número de cozinheiros (threads lógicas)",
    )
    args = parser.parse_args()

    outputs_dir = Path(args.outputs)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    all_summaries: List[Dict] = []

    for scen_name, wl_cfg in SCENARIOS.items():
        jobs = generate_jobs(wl_cfg)

        avg_wait_by_variant: Dict[str, float] = {}
        avg_turn_by_variant: Dict[str, float] = {}

        util_for_line = None  # pegaremos de D_SJF_sem para a linha

        for var_name, (sched_name, use_sem) in VARIANTS.items():
            # Copiamos jobs (imutable em estrutura; criamos novos objetos para tempos)
            jobs_copy = [
                type(j)(id=j.id, arrival_time=j.arrival_time, cook_time=j.cook_time, prep_time=j.prep_time)
                for j in jobs
            ]
            result = run_simulation(jobs_copy, RunConfig(num_workers=args.workers, scheduler=sched_name, use_semaphore=use_sem))

            df_jobs = jobs_to_dataframe(result.jobs)
            df_jobs.to_csv(outputs_dir / f"{scen_name}_{var_name}_jobs.csv", index=False)

            summ = summarize(result.jobs, utilization=result.stove_utilization, collisions=result.collisions)
            summary_row = {
                "scenario": scen_name,
                "variant": var_name,
                **asdict(summ),
            }
            all_summaries.append(summary_row)

            avg_wait_by_variant[var_name] = summ.avg_waiting_time
            avg_turn_by_variant[var_name] = summ.avg_turnaround_time

            if var_name == "D_SJF_sem":
                util_for_line = summ.utilization

        # Plots por cenário
        plot_bars(avg_wait_by_variant, f"Tempo médio de espera — {scen_name}", outputs_dir / f"{scen_name}_wait_bars.png")
        plot_bars(avg_turn_by_variant, f"Turnaround médio — {scen_name}", outputs_dir / f"{scen_name}_turn_bars.png")

        # Gantt apenas para bursty e variante D, se existir
        if scen_name == "bursty":
            # Reusar o CSV gerado
            df_burst_d = pd.read_csv(outputs_dir / f"bursty_D_SJF_sem_jobs.csv")
            plot_gantt(df_burst_d, "Gantt — bursty, D (SJF com semáforo)", outputs_dir / "bursty_gantt.png", max_jobs=12)

    # Agrega e salva summaries
    df_summary = pd.DataFrame(all_summaries)
    df_summary.to_csv(outputs_dir / "summaries.csv", index=False)
    (outputs_dir / "summaries.json").write_text(df_summary.to_json(orient="records", indent=2), encoding="utf-8")

    # Linha de utilização por cenário (usando D_SJF_sem capturado via summaries)
    util_by_scenario: Dict[str, float] = {}
    for scen_name in SCENARIOS.keys():
        row = df_summary[(df_summary["scenario"] == scen_name) & (df_summary["variant"] == "D_SJF_sem")]
        if not row.empty:
            util_by_scenario[scen_name] = float(row["utilization"].iloc[0])
    plot_line(util_by_scenario, "Utilização do fogão por cenário (D_SJF_sem)", outputs_dir / "utilization_line.png")


if __name__ == "__main__":
    main()


