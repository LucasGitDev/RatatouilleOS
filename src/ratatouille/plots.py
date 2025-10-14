from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import pandas as pd


def plot_bars(metric_by_variant: Dict[str, float], title: str, out: Path) -> None:
    names = list(metric_by_variant.keys())
    values = [metric_by_variant[k] for k in names]
    x = list(range(len(names)))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x, values, color="#4C78A8")
    ax.set_title(title)
    ax.set_ylabel("tempo")
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    for i, v in enumerate(values):
        ax.text(i, v, f"{v:.2f}", ha="center", va="bottom", fontsize=8)
    plt.subplots_adjust(bottom=0.25, top=0.9)
    fig.savefig(out, dpi=150, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)


def plot_line(utilization_by_scenario: Dict[str, float], title: str, out: Path) -> None:
    names = list(utilization_by_scenario.keys())
    values = [utilization_by_scenario[k] for k in names]
    x = list(range(len(names)))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(x, values, marker="o", color="#F58518")
    ax.set_title(title)
    ax.set_ylabel("utilização")
    ax.set_ylim(0, 1.05)
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    for xi, v in zip(x, values):
        ax.text(xi, v, f"{v:.2f}", ha="center", va="bottom", fontsize=8)
    plt.subplots_adjust(bottom=0.25, top=0.9)
    fig.savefig(out, dpi=150, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)


def plot_gantt(df: pd.DataFrame, title: str, out: Path, max_jobs: int = 10) -> None:
    d = df.sort_values("start_time").head(max_jobs)
    fig, ax = plt.subplots(figsize=(9, 5))
    for idx, row in d.iterrows():
        ax.broken_barh(
            [(row["start_time"], row["cook_time"])],
            (row["id"] * 10, 9),
            facecolors="#54A24B",
        )
    ax.set_xlabel("tempo")
    ax.set_ylabel("job id")
    ax.set_title(title)
    plt.subplots_adjust(bottom=0.2, top=0.9)
    fig.savefig(out, dpi=150, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)



