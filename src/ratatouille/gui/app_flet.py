from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List

import flet as ft
import asyncio

from ..generators import WorkloadConfig, generate_jobs
from ..sim.engine import RunConfig, run_simulation


@dataclass
class AnimationEvent:
    t: float
    kind: str
    job_id: int
    chef_id: int | None = None


def build_timeline(sched: str, use_sem: bool) -> tuple[list[AnimationEvent], float, list]:
    wl = WorkloadConfig(num_jobs=12, arrival_pattern="stress", cook_time_dist="mix", seed=123)
    jobs = generate_jobs(wl)
    res = run_simulation(jobs, RunConfig(num_workers=4, scheduler=sched, use_semaphore=use_sem))
    events: list[AnimationEvent] = []
    for ev in res.events:
        if ev.kind in {"chef_pick", "job_start", "job_finish", "collision"}:
            events.append(AnimationEvent(t=ev.timestamp, kind=ev.kind, job_id=ev.job_id or -1, chef_id=ev.chef_id))
    events.sort(key=lambda e: e.t)
    makespan = max((e.t for e in events), default=0.0)
    return events, makespan, res.jobs


class KitchenPage:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.page.title = "RatatouilleOS — Flet"
        self.page.horizontal_alignment = ft.MainAxisAlignment.CENTER
        self.page.vertical_alignment = ft.MainAxisAlignment.START
        self.page.scroll = ft.ScrollMode.AUTO

        # Controls
        self.algo = ft.Dropdown(options=[ft.dropdown.Option("fcfs"), ft.dropdown.Option("sjf")], value="sjf", width=140)
        self.sem = ft.Switch(label="Semáforo", value=True)
        self.speed = ft.Slider(min=0.1, max=10, divisions=99, value=2.0, label="{value}x", width=260)
        self.start_btn = ft.ElevatedButton("Iniciar", on_click=self.on_start)

        self.controls_row = ft.Row(controls=[
            ft.Text("Algoritmo:"), self.algo, self.sem, ft.Text("Velocidade:"), self.speed, self.start_btn
        ], alignment=ft.MainAxisAlignment.CENTER)

        # Canvas via Stack (3 colunas + bolinhas)
        self.width = 900
        self.height = 420
        self.queue_x = 80
        self.stove_x = 450
        self.done_x = 820
        self.y_base = 360
        self.row_h = 26

        self.stack = ft.Stack(width=self.width, height=self.height)
        self._draw_layout()

        # Legenda e status
        self.legend = ft.Text("Fila → Fogão (seção crítica) → Prontos. Chef pega o pedido na Fila, cozinha no Fogão (1 por vez com semáforo), e entrega em Prontos.", size=12)
        self.status = ft.Row(controls=[
            ft.Chip(label=ft.Text("Fogão: Livre"), bgcolor="#e8f5e9"),
            ft.Chip(label=ft.Text("Colisões: 0"), bgcolor="#ffebee", color="#b71c1c24"),
        ], spacing=10)
        self.page.add(self.controls_row, self.legend, self.status, self.stack)

        # Anim state
        self.events: List[AnimationEvent] = []
        self.makespan = 0.0
        self.t0 = 0.0
        self.running = False
        self.job_dots: Dict[int, ft.Container] = {}
        self.chefs: Dict[int, ft.Container] = {}
        self.collisions_count: int = 0
        self.jobs_info: Dict[int, dict] = {}
        # Sorting state for table
        self.sort_key: str = "id"  # id | ready | start
        self.sort_desc: bool = False

        # Table area
        self.sort_row = ft.Row(
            controls=[
                ft.Text("Ordenar por:"),
                ft.ElevatedButton("ID", on_click=lambda _: self._set_sort("id")),
                ft.ElevatedButton("Fila (ready)", on_click=lambda _: self._set_sort("ready")),
                ft.ElevatedButton("Execução (start)", on_click=lambda _: self._set_sort("start")),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        )
        self.table = ft.DataTable(columns=[
            ft.DataColumn(ft.Text("Ordem Fila")),
            ft.DataColumn(ft.Text("Ordem Exec.")),
            ft.DataColumn(ft.Text("ID")),
            ft.DataColumn(ft.Text("Chegada")),
            ft.DataColumn(ft.Text("Pronto (ready)")),
            ft.DataColumn(ft.Text("Início")),
            ft.DataColumn(ft.Text("Fim")),
            ft.DataColumn(ft.Text("Espera")),
            ft.DataColumn(ft.Text("Turnaround")),
            ft.DataColumn(ft.Text("Cozinho")),
        ], rows=[])
        self.page.add(self.sort_row, self.table)
        # Chef avatar
        chef = ft.Container(left=self.stove_x - 40, top=200, width=32, height=32, bgcolor="#8E44AD", border_radius=6,
                            content=ft.Text("Chef", color="white", size=10), alignment=ft.alignment.center)
        self.chefs[0] = chef
        self.stack.controls.append(chef)

    def _draw_layout(self) -> None:
        self.stack.controls.clear()
        # Column panels
        def panel(x: int, label: str, color: str) -> None:
            self.stack.controls.append(ft.Container(left=x-70, top=50, width=140, height=320, bgcolor=color, opacity=0.07, border_radius=8))
            self.stack.controls.append(ft.Text(label, left=x-60, top=12, size=16, weight=ft.FontWeight.BOLD, color="#333"))
            self.stack.controls.append(ft.Container(left=x-1, top=40, width=2, height=360, bgcolor="#bbbbbb"))
        panel(self.queue_x, "Fila", "#1E88E5")
        panel(self.stove_x, "Fogão (seção crítica)", "#FB8C00")
        panel(self.done_x, "Prontos", "#2E7D32")
        self.page.update()

    def on_start(self, _e: ft.ControlEvent) -> None:
        if self.running:
            return
        self.running = True
        self._draw_layout()
        self.events, self.makespan, jobs = build_timeline(self.algo.value or "sjf", bool(self.sem.value))
        # reset colisões
        self.collisions_count = 0
        self._update_collision_chip()
        # jobs info map - filtra apenas jobs com ID válido (maior que 0)
        self.jobs_info = {j.id: {"arrival": j.arrival_time, "ready": j.ready_time, "cook": j.cook_time, "start": j.start_time, "finish": j.finish_time} for j in jobs if j.id > 0}
        self.job_dots.clear()
        # Create dots - filtra IDs válidos (maior que 0)
        ids = sorted({e.job_id for e in self.events if e.job_id is not None and e.job_id > 0})
        for i, jid in enumerate(ids):
            # Usa índice sequencial em vez do ID para posicionamento
            y = self.y_base - (i * self.row_h)
            info = getattr(self, "jobs_info", {}).get(jid, {})
            tip = f"Pedido {jid}\nchegada={info.get('arrival', 0):.2f}\ncozimento={info.get('cook', 0):.2f}"
            dot = ft.Container(left=self.queue_x-12, top=y-12, width=24, height=24, bgcolor="#1976D2", border_radius=12,
                               content=ft.Text(str(jid), color="white", size=10, weight=ft.FontWeight.BOLD),
                               alignment=ft.alignment.center, tooltip=tip)
            self.job_dots[jid] = dot
            self.stack.controls.append(dot)
        self.page.update()
        self.t0 = time.time()
        self.page.run_task(self._tick)
        # build table
        self._rebuild_table()

    async def _tick(self) -> None:
        while self.running:
            sim_t = (time.time() - self.t0) * max(self.speed.value or 1.0, 0.01)
            while self.events and self.events[0].t <= sim_t:
                ev = self.events.pop(0)
                self._apply_event(ev)
            if sim_t >= self.makespan:
                self.running = False
            await self.page.update_async()
            await asyncio.sleep(0.03)

    def _apply_event(self, ev: AnimationEvent) -> None:
        # Ignora eventos de jobs com ID inválido, EXCETO colisões
        if ev.job_id <= 0 and ev.kind != "collision":
            return
        dot = self.job_dots.get(ev.job_id)
        # Chef move/le evento de colisão
        if ev.kind == "chef_pick" and ev.chef_id is not None:
            c = self.chefs.get(ev.chef_id)
            if c is not None and dot is not None:
                target_top = getattr(dot, "top", None)
                if isinstance(dot, ft.Tooltip):
                    target_top = getattr(dot.content, "top", 200)
                c.top = (target_top or 200) - 10
        if ev.kind == "collision":
            # Fogão vermelho (breve)
            blink = ft.Container(left=self.stove_x - 80, top=180, width=160, height=60, bgcolor="#ffcccc", opacity=0.6)
            self.stack.controls.append(blink)
            self.collisions_count += 1
            self._update_collision_chip()
            async def _remove():
                await asyncio.sleep(0.3)
                if blink in self.stack.controls:
                    self.stack.controls.remove(blink)
            self.page.run_task(_remove)
        if dot is None:
            return
        if ev.kind == "job_start":
            if isinstance(dot, ft.Tooltip):
                dot.content.left = self.stove_x - 12
                dot.content.bgcolor = "#FBC02D"
            else:
                dot.left = self.stove_x - 12
            self._set_stove_status(occupied=True)
        elif ev.kind == "job_finish":
            if isinstance(dot, ft.Tooltip):
                dot.content.left = self.done_x - 12
                dot.content.bgcolor = "#2E7D32"
            else:
                dot.left = self.done_x - 12
            self._set_stove_status(occupied=False)
        # update table once finishes may change
        if ev.kind in ("job_start", "job_finish"):
            self._rebuild_table()

    def _set_stove_status(self, occupied: bool) -> None:
        if occupied:
            self.status.controls[0] = ft.Chip(label=ft.Text("Fogão: Ocupado"), bgcolor="#fff3e0", color="#e65100")
        else:
            self.status.controls[0] = ft.Chip(label=ft.Text("Fogão: Livre"), bgcolor="#e8f5e9")

    def _update_collision_chip(self) -> None:
        self.status.controls[1] = ft.Chip(label=ft.Text(f"Colisões: {self.collisions_count}"), bgcolor="#ffebee", color="#b71c1c")

    def _set_sort(self, key: str) -> None:
        if self.sort_key == key:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_key = key
            self.sort_desc = False
        self._rebuild_table()

    def _rebuild_table(self) -> None:
        # Build list with computed order indexes - filtra apenas jobs válidos
        jobs = []
        for jid, info in self.jobs_info.items():
            # Ignora jobs com ID inválido (0 ou menor)
            if jid <= 0:
                continue
            arrival = info.get("arrival")
            ready = info.get("ready", info.get("arrival"))
            start = info.get("start")
            finish = info.get("finish")
            cook = info.get("cook")
            wait = (start - ready) if (start is not None and ready is not None) else None
            turn = (finish - arrival) if (finish is not None and arrival is not None) else None
            jobs.append({
                "jid": jid,
                "arrival": arrival,
                "ready": ready,
                "start": start,
                "finish": finish,
                "wait": wait,
                "turn": turn,
                "cook": cook,
            })
        # compute orders
        by_ready = sorted(jobs, key=lambda x: (float('inf') if x["ready"] is None else x["ready"], x["jid"]))
        ready_rank = {row["jid"]: i+1 for i, row in enumerate(by_ready)}
        by_start = sorted(jobs, key=lambda x: (float('inf') if x["start"] is None else x["start"], x["jid"]))
        start_rank = {row["jid"]: i+1 for i, row in enumerate(by_start)}
        # sort table view
        keymap = {
            "id": lambda x: (x["jid"]),
            "ready": lambda x: (float('inf') if x["ready"] is None else x["ready"], x["jid"]),
            "start": lambda x: (float('inf') if x["start"] is None else x["start"], x["jid"]),
        }
        sorted_jobs = sorted(jobs, key=keymap.get(self.sort_key, keymap["id"]), reverse=self.sort_desc)
        # rows
        rows: list[ft.DataRow] = []
        for r in sorted_jobs:
            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(ready_rank.get(r["jid"], "-")))) ,
                ft.DataCell(ft.Text(str(start_rank.get(r["jid"], "-")))) ,
                ft.DataCell(ft.Text(str(r["jid"]))),
                ft.DataCell(ft.Text(f"{r['arrival']:.2f}" if r['arrival'] is not None else "-")),
                ft.DataCell(ft.Text(f"{r['ready']:.2f}" if r['ready'] is not None else "-")),
                ft.DataCell(ft.Text(f"{r['start']:.2f}" if r['start'] is not None else "-")),
                ft.DataCell(ft.Text(f"{r['finish']:.2f}" if r['finish'] is not None else "-")),
                ft.DataCell(ft.Text(f"{r['wait']:.2f}" if r['wait'] is not None else "-")),
                ft.DataCell(ft.Text(f"{r['turn']:.2f}" if r['turn'] is not None else "-")),
                ft.DataCell(ft.Text(f"{r['cook']:.2f}" if r['cook'] is not None else "-")),
            ]))
        self.table.rows = rows
        # Atualiza a tabela imediatamente
        try:
            self.table.update()
        except Exception:
            # fallback
            self.page.update()


def main() -> None:
    def _view(page: ft.Page) -> None:
        KitchenPage(page)
    ft.app(target=_view)


if __name__ == "__main__":
    main()


