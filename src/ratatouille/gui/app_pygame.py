"""
Interface gráfica DIDÁTICA com Pygame para visualizar escalonamento de jobs.
Mostra claramente:
- Fila de pedidos com jobs coloridos
- 4 Chefs (workers) trabalhando em paralelo em 1 fogão (seção crítica)
- Colisões visíveis quando múltiplos pratos estão no fogão
- Controle de semáforo ON/OFF
- Área de pedidos concluídos organizada
- Tela completa de resultados ao final com tabela detalhada
- Controles para algoritmo (FCFS/SJF) e velocidade
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Set

import pygame
import pygame.freetype
from pygame import Surface, Rect

from ..generators import WorkloadConfig, generate_jobs
from ..sim.engine import RunConfig, run_simulation


# Cores tema profissional e limpo
COLORS = {
    'background': (250, 250, 250),
    'panel_bg': (255, 255, 255),
    'panel_border': (220, 220, 220),
    'text': (60, 60, 60),
    'text_light': (150, 150, 150),
    'text_white': (255, 255, 255),

    'counter': (240, 240, 240),
    'stove_free': (230, 230, 230),
    'stove_busy': (255, 120, 120),
    'stove_collision': (255, 80, 80),
    'stove_border': (180, 180, 180),

    'chef_idle': (200, 200, 200),
    'chef_cooking': (255, 150, 100),

    'job_waiting': (150, 150, 150),
    'job_cooking': (255, 180, 100),
    'job_done': (120, 200, 120),

    'button': (90, 120, 150),
    'button_hover': (110, 140, 170),
    'button_pressed': (70, 100, 130),
    'button_success': (100, 180, 100),
    'button_danger': (220, 100, 100),

    'metric_bg': (248, 248, 248),
    'metric_border': (230, 230, 230),
    'table_header': (240, 240, 240),
    'table_row_alt': (252, 252, 252),
}

SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 900
FPS = 60

CONTROL_AREA = Rect(20, 20, SCREEN_WIDTH - 40, 70)
KITCHEN_AREA = Rect(20, 110, SCREEN_WIDTH - 40, 500)
STATUS_AREA = Rect(20, 630, SCREEN_WIDTH - 40, 50)

# Área para a tela de resultados (tela cheia)
RESULTS_AREA = Rect(20, 20, SCREEN_WIDTH - 40, SCREEN_HEIGHT - 40)

JOB_SIZE = 28
CHEF_SIZE = 36


@dataclass
class AnimationEvent:
    t: float
    kind: str
    job_id: int
    chef_id: Optional[int] = None


def build_timeline(sched: str, use_sem: bool) -> Tuple[List[AnimationEvent], float, List]:
    wl = WorkloadConfig(num_jobs=12, arrival_pattern="stress", cook_time_dist="mix", seed=123)
    jobs = generate_jobs(wl)
    res = run_simulation(jobs, RunConfig(num_workers=4, scheduler=sched, use_semaphore=use_sem))

    events: List[AnimationEvent] = []
    for ev in res.events:
        if ev.kind in {"chef_pick", "job_start", "job_finish", "collision"}:
            events.append(AnimationEvent(
                t=ev.timestamp,
                kind=ev.kind,
                job_id=ev.job_id or -1,
                chef_id=ev.chef_id
            ))

    events.sort(key=lambda e: e.t)
    makespan = max((e.t for e in events), default=0.0)
    return events, makespan, res.jobs


class Button:
    def __init__(self, x: int, y: int, width: int, height: int, text: str, font,
                 color='button', text_color='text_white'):
        self.rect = Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.pressed = False
        self.hover = False
        self.color = color
        self.text_color = text_color
        self.enabled = True

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.enabled:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
                return False
        elif event.type == pygame.MOUSEBUTTONUP:
            if self.pressed:
                self.pressed = False
                if self.rect.collidepoint(event.pos):
                    return True
        elif event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        return False

    def draw(self, screen: Surface):
        if not self.enabled:
            color = COLORS['panel_border']
            text_color = COLORS['text_light']
        elif self.pressed:
            color = COLORS.get(f'{self.color}_pressed', COLORS['button_pressed'])
            text_color = COLORS[self.text_color]
        elif self.hover:
            color = COLORS.get(f'{self.color}_hover', COLORS['button_hover'])
            text_color = COLORS[self.text_color]
        else:
            color = COLORS[self.color]
            text_color = COLORS[self.text_color]

        pygame.draw.rect(screen, color, self.rect, border_radius=6)
        pygame.draw.rect(screen, COLORS['panel_border'], self.rect, 1, border_radius=6)

        if hasattr(self.font, 'render'):
            text_surface, text_rect = self.font.render(self.text, text_color)
            text_rect.center = self.rect.center
            screen.blit(text_surface, text_rect)


class KitchenSimulationPygame:
    def __init__(self):
        pygame.init()
        pygame.freetype.init()

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("RatatouilleOS - Visualização de Escalonamento")
        self.clock = pygame.time.Clock()

        self.font_large = pygame.freetype.Font(None, 22)
        self.font_medium = pygame.freetype.Font(None, 18)
        self.font_small = pygame.freetype.Font(None, 15)
        self.font_tiny = pygame.freetype.Font(None, 13)

        self.events: List[AnimationEvent] = []
        self.t0 = 0.0
        self.running = False
        self.simulation_finished = False
        self.show_results_screen = False  # Nova tela de resultados
        self.job_dots: Dict[int, Tuple[int, int]] = {}
        self.chefs: Dict[int, Tuple[int, int]] = {}
        self.chef_states: Dict[int, str] = {}
        self.chef_jobs: Dict[int, Optional[int]] = {}
        self.collisions_count = 0
        self.jobs_info: Dict[int, dict] = {}
        self.done_jobs_positions: Dict[int, Tuple[int, int]] = {}

        # Controle de jobs no fogão para detectar colisões visuais
        self.jobs_in_stove: Set[int] = set()

        self.algorithm = "sjf"
        self.use_semaphore = True
        self.speed = 2.0

        self.width = KITCHEN_AREA.width - 40
        self.height = KITCHEN_AREA.height - 40
        self.queue_x = 100
        self.stove_x = self.width // 2
        self.done_x = self.width - 150
        self.y_base = self.height - 60
        self.row_h = 35

        # Controle da tabela de resultados
        self.sort_key = "id"  # "id", "ready", "start"
        self.sort_desc = False
        self.table_scroll = 0

        # Posições iniciais dos 4 chefs em volta do fogão
        self.chef_init_positions = [
            (self.stove_x - 100, 180),
            (self.stove_x + 100, 180),
            (self.stove_x - 100, 280),
            (self.stove_x + 100, 280),
        ]

        for i in range(4):
            self.chefs[i] = self.chef_init_positions[i]
            self.chef_states[i] = 'idle'
            self.chef_jobs[i] = None

        self._create_buttons()

    def _create_buttons(self):
        y = CONTROL_AREA.centery - 15
        x_start = CONTROL_AREA.left + 20

        self.btn_start = Button(x_start, y, 90, 30, "INICIAR", self.font_medium, 'button_success')
        self.btn_reset = Button(x_start + 100, y, 90, 30, "RESET", self.font_medium, 'button_danger')

        algo_text = f"Algoritmo: {self.algorithm.upper()}"
        self.btn_algo = Button(x_start + 220, y, 180, 30, algo_text, self.font_small)

        sem_text = f"Semáforo: {'ON' if self.use_semaphore else 'OFF'}"
        self.btn_sem = Button(x_start + 410, y, 180, 30, sem_text, self.font_small)

        self.btn_speed_down = Button(x_start + 620, y, 35, 30, "-", self.font_medium)
        self.btn_speed_up = Button(x_start + 665, y, 35, 30, "+", self.font_medium)

        # Botões para tela de resultados
        self.btn_results = Button(x_start + 750, y, 150, 30, "VER RESULTADOS", self.font_small, 'button')
        self.btn_back = Button(50, 50, 120, 35, "VOLTAR", self.font_medium, 'button')

        # Botões de ordenação (apenas ID e Execução)
        results_y = RESULTS_AREA.top + 120
        self.btn_sort_id = Button(RESULTS_AREA.left + 30, results_y, 100, 28, "Por ID", self.font_small)
        self.btn_sort_start = Button(RESULTS_AREA.left + 140, results_y, 120, 28, "Por Execucao", self.font_small)

        self.buttons = [
            self.btn_start, self.btn_reset,
            self.btn_algo, self.btn_sem,
            self.btn_speed_down, self.btn_speed_up,
            self.btn_results
        ]

        self.results_buttons = [self.btn_back, self.btn_sort_id, self.btn_sort_start]

    def _generate_simulation_data(self):
        print(f"Gerando simulação: {self.algorithm}, semáforo: {self.use_semaphore}")
        self.events, self.makespan, jobs = build_timeline(self.algorithm, self.use_semaphore)

        self.collisions_count = 0
        self.simulation_finished = False
        self.show_results_screen = False
        self.done_jobs_positions.clear()
        self.jobs_in_stove.clear()

        self.jobs_info = {
            j.id: {
                "arrival": j.arrival_time,
                "ready": j.ready_time,
                "cook": j.cook_time,
                "start": j.start_time,
                "finish": j.finish_time
            }
            for j in jobs if j.id > 0
        }

        self.job_dots.clear()

        ids = sorted({e.job_id for e in self.events if e.job_id is not None and e.job_id > 0})
        for i, jid in enumerate(ids):
            y = self.y_base - (i * self.row_h)
            x = self.queue_x
            self.job_dots[jid] = (x, y)

        self.running = True
        self.t0 = time.time()

        # Reseta os 4 chefs para posições iniciais
        for i in range(4):
            self.chefs[i] = self.chef_init_positions[i]
            self.chef_states[i] = 'idle'
            self.chef_jobs[i] = None

        print(f"Chefs inicializados: {len(self.chefs)} chefs nas posições: {list(self.chefs.values())}")

    def _update_simulation(self):
        if not self.running:
            return

        sim_t = (time.time() - self.t0) * max(self.speed, 0.01)

        while self.events and self.events[0].t <= sim_t:
            ev = self.events.pop(0)
            self._apply_event(ev)

        if sim_t >= self.makespan:
            self.running = False
            self.simulation_finished = True
            # Habilita botão de resultados
            self.btn_results.enabled = True

    def _apply_event(self, ev: AnimationEvent):
        if ev.job_id <= 0 and ev.kind != "collision":
            return

        if ev.kind == "collision":
            self.collisions_count += 1

        if ev.job_id not in self.job_dots:
            return

        if ev.kind == "job_start":
            # Adiciona job ao fogão
            self.jobs_in_stove.add(ev.job_id)

            # Posiciona jobs lado a lado quando há colisão - MELHORADO
            jobs_list = sorted(list(self.jobs_in_stove))
            num_jobs = len(jobs_list)
            idx = jobs_list.index(ev.job_id)

            if num_jobs == 1:
                offset_x = 0
                offset_y = 0
            elif num_jobs == 2:
                offset_x = -35 + (idx * 70)
                offset_y = 0
            elif num_jobs == 3:
                offset_x = -50 + (idx * 50)
                offset_y = 0
            elif num_jobs == 4:
                offset_x = -60 + (idx * 40)
                offset_y = 0
            else:
                # Para mais de 4, distribui em 2 linhas
                row = idx // 3
                col = idx % 3
                offset_x = -50 + (col * 50)
                offset_y = -20 + (row * 40)

            self.job_dots[ev.job_id] = (self.stove_x + offset_x, 230 + offset_y)

            if ev.chef_id is not None:
                # Chef fica ao lado do job
                self.chefs[ev.chef_id] = (self.stove_x + offset_x - 55, 230 + offset_y)
                self.chef_states[ev.chef_id] = 'cooking'
                self.chef_jobs[ev.chef_id] = ev.job_id

        elif ev.kind == "job_finish":
            # Remove job do fogão
            if ev.job_id in self.jobs_in_stove:
                self.jobs_in_stove.remove(ev.job_id)

            # Reposiciona jobs restantes no fogão - MELHORADO
            jobs_list = sorted(list(self.jobs_in_stove))
            for i, jid in enumerate(jobs_list):
                num_jobs = len(jobs_list)
                if num_jobs == 1:
                    offset_x = 0
                    offset_y = 0
                elif num_jobs == 2:
                    offset_x = -35 + (i * 70)
                    offset_y = 0
                elif num_jobs == 3:
                    offset_x = -50 + (i * 50)
                    offset_y = 0
                elif num_jobs == 4:
                    offset_x = -60 + (i * 40)
                    offset_y = 0
                else:
                    row = i // 3
                    col = i % 3
                    offset_x = -50 + (col * 50)
                    offset_y = -20 + (row * 40)
                self.job_dots[jid] = (self.stove_x + offset_x, 230 + offset_y)

            # Calcula posição no balcão
            done_count = len(self.done_jobs_positions)
            row = done_count // 3
            col = done_count % 3

            done_x = self.done_x - 60 + (col * 45)
            done_y = 100 + (row * 45)

            self.job_dots[ev.job_id] = (done_x, done_y)
            self.done_jobs_positions[ev.job_id] = (done_x, done_y)

            if ev.chef_id is not None:
                self.chefs[ev.chef_id] = self.chef_init_positions[ev.chef_id]
                self.chef_states[ev.chef_id] = 'idle'
                self.chef_jobs[ev.chef_id] = None

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            # Scroll na tela de resultados
            if self.show_results_screen and event.type == pygame.MOUSEWHEEL:
                self.table_scroll = max(0, self.table_scroll - event.y * 20)

            # Eventos da tela de resultados
            if self.show_results_screen:
                if self.btn_back.handle_event(event):
                    self.show_results_screen = False
                elif self.btn_sort_id.handle_event(event):
                    self._set_sort("id")
                elif self.btn_sort_start.handle_event(event):
                    self._set_sort("start")
            else:
                # Eventos da tela principal
                if self.btn_start.handle_event(event):
                    if not self.running:
                        self._generate_simulation_data()

                elif self.btn_reset.handle_event(event):
                    self.running = False
                    self.simulation_finished = False
                    self.show_results_screen = False
                    self.collisions_count = 0
                    self.job_dots.clear()
                    self.jobs_info.clear()
                    self.done_jobs_positions.clear()
                    self.jobs_in_stove.clear()
                    self.btn_results.enabled = False
                    for i in range(4):
                        self.chefs[i] = self.chef_init_positions[i]
                        self.chef_states[i] = 'idle'
                        self.chef_jobs[i] = None

                elif self.btn_algo.handle_event(event):
                    self.algorithm = "fcfs" if self.algorithm == "sjf" else "sjf"
                    self.btn_algo.text = f"Algoritmo: {self.algorithm.upper()}"

                elif self.btn_sem.handle_event(event):
                    self.use_semaphore = not self.use_semaphore
                    self.btn_sem.text = f"Semáforo: {'ON' if self.use_semaphore else 'OFF'}"

                elif self.btn_speed_down.handle_event(event):
                    self.speed = max(0.1, self.speed - 0.2)

                elif self.btn_speed_up.handle_event(event):
                    self.speed = min(10.0, self.speed + 0.2)

                elif self.btn_results.handle_event(event):
                    if self.simulation_finished:
                        self.show_results_screen = True
                        self.table_scroll = 0

        return True

    def _set_sort(self, key: str):
        if self.sort_key == key:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_key = key
            self.sort_desc = False

    def _draw_background(self):
        self.screen.fill(COLORS['background'])

        if not self.show_results_screen:
            pygame.draw.rect(self.screen, COLORS['panel_bg'], CONTROL_AREA, border_radius=8)
            pygame.draw.rect(self.screen, COLORS['panel_border'], CONTROL_AREA, 1, border_radius=8)

            pygame.draw.rect(self.screen, COLORS['panel_bg'], KITCHEN_AREA, border_radius=8)
            pygame.draw.rect(self.screen, COLORS['panel_border'], KITCHEN_AREA, 1, border_radius=8)

            pygame.draw.rect(self.screen, COLORS['panel_bg'], STATUS_AREA, border_radius=8)
            pygame.draw.rect(self.screen, COLORS['panel_border'], STATUS_AREA, 1, border_radius=8)
        else:
            pygame.draw.rect(self.screen, COLORS['panel_bg'], RESULTS_AREA, border_radius=8)
            pygame.draw.rect(self.screen, COLORS['panel_border'], RESULTS_AREA, 1, border_radius=8)

    def _draw_kitchen_layout(self):
        base_x = KITCHEN_AREA.left + 20
        base_y = KITCHEN_AREA.top + 20

        def draw_station(x: int, y: int, w: int, h: int, label: str):
            station_rect = Rect(base_x + x, base_y + y, w, h)
            pygame.draw.rect(self.screen, COLORS['counter'], station_rect, border_radius=6)
            pygame.draw.rect(self.screen, COLORS['panel_border'], station_rect, 1, border_radius=6)

            text_surface, text_rect = self.font_small.render(label, COLORS['text'])
            text_rect.centerx = station_rect.centerx
            text_rect.y = station_rect.top + 8
            self.screen.blit(text_surface, text_rect)

        # Fila de pedidos
        draw_station(self.queue_x - 80, 50, 160, self.height - 100, "FILA DE PEDIDOS")

        # Fogão (seção crítica) - MELHORADO PARA COLISÕES
        stove_area_rect = Rect(base_x + self.stove_x - 100, base_y + 140, 200, 180)

        # Cor muda se há colisão
        num_jobs_in_stove = len(self.jobs_in_stove)
        if num_jobs_in_stove > 1:
            bg_color = COLORS['stove_collision']
            border_width = 5
            border_color = (200, 0, 0)  # Vermelho intenso
        elif num_jobs_in_stove == 1:
            bg_color = COLORS['stove_busy']
            border_width = 3
            border_color = (255, 140, 0)  # Laranja
        else:
            bg_color = COLORS['metric_bg']
            border_width = 2
            border_color = COLORS['stove_border']

        # Desenha fundo com borda destacada
        pygame.draw.rect(self.screen, bg_color, stove_area_rect, border_radius=10)
        pygame.draw.rect(self.screen, border_color, stove_area_rect, border_width, border_radius=10)

        # Se há colisão, adiciona efeito visual piscante
        if num_jobs_in_stove > 1:
            # Borda interna pulsante
            import math
            pulse = int(abs(math.sin(time.time() * 5)) * 10)
            inner_rect = Rect(
                stove_area_rect.left + 8,
                stove_area_rect.top + 8,
                stove_area_rect.width - 16,
                stove_area_rect.height - 16
            )
            pygame.draw.rect(self.screen, (255, 100, 100), inner_rect, 3 + pulse, border_radius=8)

        title_surface, title_rect = self.font_large.render("FOGÃO", COLORS['text'])
        title_rect.centerx = stove_area_rect.centerx
        title_rect.y = stove_area_rect.top + 12
        self.screen.blit(title_surface, title_rect)

        subtitle_surface, subtitle_rect = self.font_tiny.render("(Seção Crítica)", COLORS['text_light'])
        subtitle_rect.centerx = stove_area_rect.centerx
        subtitle_rect.y = stove_area_rect.top + 38
        self.screen.blit(subtitle_surface, subtitle_rect)

        # Status do fogão - ABAIXO DO FOGÃO PARA MELHOR VISIBILIDADE
        if num_jobs_in_stove > 1:
            status = f"COLISÃO!"
            status2 = f"{num_jobs_in_stove} PRATOS NO FOGÃO"
            status_color = (255, 255, 255)

            # Fundo vermelho para destaque - POSICIONADO ABAIXO DO FOGÃO
            status_bg = Rect(
                stove_area_rect.centerx - 90,
                stove_area_rect.bottom + 10,
                180,
                50
            )
            pygame.draw.rect(self.screen, (200, 0, 0), status_bg, border_radius=8)
            pygame.draw.rect(self.screen, (255, 255, 255), status_bg, 3, border_radius=8)

            status_surface, status_rect = self.font_medium.render(status, status_color)
            status_rect.centerx = stove_area_rect.centerx
            status_rect.y = stove_area_rect.bottom + 16
            self.screen.blit(status_surface, status_rect)

            status2_surface, status2_rect = self.font_small.render(status2, status_color)
            status2_rect.centerx = stove_area_rect.centerx
            status2_rect.y = stove_area_rect.bottom + 36
            self.screen.blit(status2_surface, status2_rect)
        elif num_jobs_in_stove == 1:
            status = "OCUPADO"
            status_color = COLORS['text']
            status_surface, status_rect = self.font_medium.render(status, status_color)
            status_rect.centerx = stove_area_rect.centerx
            status_rect.y = stove_area_rect.bottom + 10
            self.screen.blit(status_surface, status_rect)
        else:
            status = "LIVRE"
            status_color = COLORS['text_light']
            status_surface, status_rect = self.font_medium.render(status, status_color)
            status_rect.centerx = stove_area_rect.centerx
            status_rect.y = stove_area_rect.bottom + 10
            self.screen.blit(status_surface, status_rect)

        # Balcão de pratos prontos
        done_area_rect = Rect(base_x + self.done_x - 140, base_y + 50, 260, self.height - 100)
        pygame.draw.rect(self.screen, COLORS['counter'], done_area_rect, border_radius=6)
        pygame.draw.rect(self.screen, COLORS['panel_border'], done_area_rect, 1, border_radius=6)

        done_text_surface, done_text_rect = self.font_small.render("BALCÃO DE PRONTOS", COLORS['text'])
        done_text_rect.centerx = done_area_rect.centerx
        done_text_rect.y = done_area_rect.top + 8
        self.screen.blit(done_text_surface, done_text_rect)

        # Grid visual no balcão
        for row in range(5):
            for col in range(3):
                grid_x = base_x + self.done_x - 60 + (col * 45)
                grid_y = base_y + 100 + (row * 45)
                grid_rect = Rect(grid_x - 15, grid_y - 15, 30, 30)
                pygame.draw.rect(self.screen, COLORS['metric_border'], grid_rect, 1, border_radius=3)

    def _draw_jobs(self):
        base_x = KITCHEN_AREA.left + 20
        base_y = KITCHEN_AREA.top + 20

        for job_id, (x, y) in self.job_dots.items():
            if x < self.queue_x + 50:
                color = COLORS['job_waiting']
            elif job_id in self.done_jobs_positions:
                color = COLORS['job_done']
            else:
                color = COLORS['job_cooking']

            job_center = (base_x + x, base_y + y)

            pygame.draw.circle(self.screen, COLORS['panel_bg'], job_center, JOB_SIZE // 2 + 2)
            pygame.draw.circle(self.screen, color, job_center, JOB_SIZE // 2)
            pygame.draw.circle(self.screen, COLORS['text'], job_center, JOB_SIZE // 2, 2)

            text_surface, text_rect = self.font_tiny.render(str(job_id), COLORS['text'])
            text_rect.center = job_center
            self.screen.blit(text_surface, text_rect)

    def _draw_chefs(self):
        """Desenha os 4 chefs com melhor visualização"""
        base_x = KITCHEN_AREA.left + 20
        base_y = KITCHEN_AREA.top + 20

        for chef_id in range(4):  # Garante desenhar os 4 chefs
            if chef_id not in self.chefs:
                continue

            x, y = self.chefs[chef_id]
            state = self.chef_states.get(chef_id, 'idle')

            if state == 'idle':
                color = COLORS['chef_idle']
            else:
                color = COLORS['chef_cooking']

            chef_pos = (base_x + x, base_y + y)

            # Círculo externo maior para destaque
            pygame.draw.circle(self.screen, COLORS['panel_border'], chef_pos, CHEF_SIZE // 2 + 2)
            pygame.draw.circle(self.screen, color, chef_pos, CHEF_SIZE // 2)
            pygame.draw.circle(self.screen, COLORS['text'], chef_pos, CHEF_SIZE // 2, 2)

            # Número do chef
            text_surface, text_rect = self.font_small.render(str(chef_id + 1), COLORS['text_white'])
            text_rect.center = chef_pos
            self.screen.blit(text_surface, text_rect)

            # Label do estado abaixo do chef
            state_labels = {'idle': 'LIVRE', 'cooking': 'COZINHANDO'}
            state_text = state_labels.get(state, 'LIVRE')
            state_surface, state_rect = self.font_tiny.render(state_text, COLORS['text_light'])
            state_rect.centerx = chef_pos[0]
            state_rect.y = chef_pos[1] + CHEF_SIZE // 2 + 5
            self.screen.blit(state_surface, state_rect)

    def _draw_controls(self):
        for button in self.buttons:
            button.draw(self.screen)

        info_x = CONTROL_AREA.right - 250
        info_y = CONTROL_AREA.centery - 8

        speed_text = f"Velocidade: {self.speed:.1f}x"
        text_surface, text_rect = self.font_small.render(speed_text, COLORS['text'])
        text_rect.topleft = (info_x, info_y)
        self.screen.blit(text_surface, text_rect)

    def _draw_status(self):
        y = STATUS_AREA.centery - 8
        x = STATUS_AREA.left + 20

        status = "EXECUTANDO" if self.running else ("FINALIZADO" if self.simulation_finished else "PRONTO")
        color = COLORS['button_success'] if self.running else COLORS['text']

        status_surface, status_rect = self.font_medium.render(status, color)
        status_rect.topleft = (x, y)
        self.screen.blit(status_surface, status_rect)

        # Removido contador de tempo

        # Status detalhado dos 4 chefs
        idle_count = sum(1 for state in self.chef_states.values() if state == 'idle')
        cooking_count = sum(1 for state in self.chef_states.values() if state == 'cooking')

        chefs_text = f"Chefs: Livres={idle_count} | Cozinhando={cooking_count}"
        chefs_surface, chefs_rect = self.font_small.render(chefs_text, COLORS['text'])
        chefs_rect.topleft = (x + 200, y + 2)
        self.screen.blit(chefs_surface, chefs_rect)

        if self.collisions_count > 0:
            collision_text = f"Colisões: {self.collisions_count}"
            collision_surface, collision_rect = self.font_small.render(collision_text, COLORS['button_danger'])
            collision_rect.topleft = (x + 700, y + 2)
            self.screen.blit(collision_surface, collision_rect)

    def _draw_results_screen(self):
        """Desenha a tela completa de resultados com tabela detalhada"""
        # Botão voltar
        self.btn_back.draw(self.screen)

        # Título
        title_surface, title_rect = self.font_large.render("RESULTADOS DA SIMULAÇÃO", COLORS['text'])
        title_rect.centerx = RESULTS_AREA.centerx
        title_rect.y = RESULTS_AREA.top + 20
        self.screen.blit(title_surface, title_rect)

        # Configuração
        config_text = f"Algoritmo: {self.algorithm.upper()} | Semáforo: {'ON' if self.use_semaphore else 'OFF'} | Workers: 4 | Colisões: {self.collisions_count}"
        config_surface, config_rect = self.font_small.render(config_text, COLORS['text_light'])
        config_rect.centerx = RESULTS_AREA.centerx
        config_rect.y = RESULTS_AREA.top + 50
        self.screen.blit(config_surface, config_rect)

        # Botões de ordenação
        for btn in self.results_buttons[1:]:  # Pula o botão voltar
            btn.draw(self.screen)

        # Indicador de ordenação atual
        sort_names = {'id': 'ID', 'start': 'Execucao'}
        sort_text = f"Ordenado por: {sort_names[self.sort_key]}"
        sort_surface, sort_rect = self.font_tiny.render(sort_text, COLORS['text_light'])
        sort_rect.topleft = (RESULTS_AREA.left + 270, RESULTS_AREA.top + 126)
        self.screen.blit(sort_surface, sort_rect)

        # Preparar dados
        jobs = []
        for jid, info in self.jobs_info.items():
            if jid <= 0:
                continue
            arrival = info.get("arrival")
            ready = info.get("ready", arrival)
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

        # Compute orders
        by_ready = sorted(jobs, key=lambda x: (float('inf') if x["ready"] is None else x["ready"], x["jid"]))
        ready_rank = {row["jid"]: i+1 for i, row in enumerate(by_ready)}

        by_start = sorted(jobs, key=lambda x: (float('inf') if x["start"] is None else x["start"], x["jid"]))
        start_rank = {row["jid"]: i+1 for i, row in enumerate(by_start)}

        # Sort table view (apenas id e start)
        keymap = {
            "id": lambda x: (x["jid"]),
            "start": lambda x: (float('inf') if x["start"] is None else x["start"], x["jid"]),
        }
        sorted_jobs = sorted(jobs, key=keymap.get(self.sort_key, keymap["id"]), reverse=self.sort_desc)

        # Cabeçalho da tabela
        header_y = RESULTS_AREA.top + 160
        header_x = RESULTS_AREA.left + 30

        headers = ["Ordem Fila", "Ordem Exec.", "ID", "Chegada", "Pronto", "Início", "Fim", "Espera", "Turnaround", "Cozimento"]
        col_widths = [100, 110, 60, 90, 90, 90, 90, 90, 100, 90]

        # Desenha cabeçalho
        for i, (header, width) in enumerate(zip(headers, col_widths)):
            col_x = header_x + sum(col_widths[:i])
            header_rect = Rect(col_x, header_y, width - 5, 30)
            pygame.draw.rect(self.screen, COLORS['table_header'], header_rect, border_radius=4)
            pygame.draw.rect(self.screen, COLORS['metric_border'], header_rect, 1, border_radius=4)

            text_surface, text_rect = self.font_small.render(header, COLORS['text'])
            text_rect.center = header_rect.center
            self.screen.blit(text_surface, text_rect)

        # Linhas da tabela (ajustado para o novo tamanho de estatísticas)
        row_height = 32
        start_y = header_y + 35
        visible_rows = (RESULTS_AREA.height - 290) // row_height

        for i, r in enumerate(sorted_jobs):
            if i < self.table_scroll // row_height:
                continue
            if i >= self.table_scroll // row_height + visible_rows:
                break

            row_y = start_y + (i - self.table_scroll // row_height) * row_height

            # Fundo alternado
            if i % 2 == 1:
                row_bg_rect = Rect(header_x, row_y, sum(col_widths) - 5, row_height)
                pygame.draw.rect(self.screen, COLORS['table_row_alt'], row_bg_rect, border_radius=3)

            # Valores
            values = [
                str(ready_rank.get(r["jid"], "-")),
                str(start_rank.get(r["jid"], "-")),
                str(r["jid"]),
                f"{r['arrival']:.2f}" if r['arrival'] is not None else "-",
                f"{r['ready']:.2f}" if r['ready'] is not None else "-",
                f"{r['start']:.2f}" if r['start'] is not None else "-",
                f"{r['finish']:.2f}" if r['finish'] is not None else "-",
                f"{r['wait']:.2f}" if r['wait'] is not None else "-",
                f"{r['turn']:.2f}" if r['turn'] is not None else "-",
                f"{r['cook']:.2f}" if r['cook'] is not None else "-"
            ]

            for j, (value, width) in enumerate(zip(values, col_widths)):
                col_x = header_x + sum(col_widths[:j])
                cell_rect = Rect(col_x, row_y, width - 5, row_height)

                # Borda sutil
                pygame.draw.rect(self.screen, COLORS['metric_border'], cell_rect, 1, border_radius=3)

                text_surface, text_rect = self.font_small.render(value, COLORS['text'])
                text_rect.center = cell_rect.center
                self.screen.blit(text_surface, text_rect)

        # Resumo estatístico na parte inferior (maior)
        summary_y = RESULTS_AREA.bottom - 160
        summary_rect = Rect(RESULTS_AREA.left + 30, summary_y, RESULTS_AREA.width - 60, 140)
        pygame.draw.rect(self.screen, COLORS['metric_bg'], summary_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLORS['metric_border'], summary_rect, 3, border_radius=8)

        summary_title_surface, summary_title_rect = self.font_large.render("ESTATISTICAS GERAIS", COLORS['text'])
        summary_title_rect.centerx = summary_rect.centerx
        summary_title_rect.y = summary_rect.top + 15
        self.screen.blit(summary_title_surface, summary_title_rect)

        # Calcula estatísticas
        all_waits = [j['wait'] for j in jobs if j['wait'] is not None]
        all_turns = [j['turn'] for j in jobs if j['turn'] is not None]

        avg_wait = sum(all_waits) / len(all_waits) if all_waits else 0
        max_wait = max(all_waits) if all_waits else 0
        avg_turn = sum(all_turns) / len(all_turns) if all_turns else 0
        max_turn = max(all_turns) if all_turns else 0

        # Estatísticas em grid 2x4 (com fonte maior)
        stats = [
            ("Jobs Processados", f"{len(jobs)}"),
            ("Colisoes", f"{self.collisions_count}"),
            ("Throughput", f"{len(jobs)/self.makespan:.2f} jobs/s"),
            ("Tempo Medio Espera", f"{avg_wait:.2f}s"),
            ("Tempo Maximo Espera", f"{max_wait:.2f}s"),
            ("Tempo Medio Total", f"{avg_turn:.2f}s"),
            ("Tempo Maximo Total", f"{max_turn:.2f}s"),
        ]

        stat_w = (summary_rect.width - 60) // 4
        stat_y = summary_rect.top + 55

        for i, (label, value) in enumerate(stats):
            col = i % 4
            row = i // 4

            stat_x = summary_rect.left + 30 + col * stat_w
            stat_y_pos = stat_y + row * 38

            label_surface, label_rect = self.font_small.render(label, COLORS['text_light'])
            label_rect.topleft = (stat_x, stat_y_pos)
            self.screen.blit(label_surface, label_rect)

            value_surface, value_rect = self.font_medium.render(value, COLORS['text'])
            value_rect.topleft = (stat_x, stat_y_pos + 18)
            self.screen.blit(value_surface, value_rect)

    def run(self):
        """Loop principal da aplicação"""
        running = True

        while running:
            running = self._handle_events()

            if not self.show_results_screen:
                self._update_simulation()

            self._draw_background()

            if self.show_results_screen:
                self._draw_results_screen()
            else:
                self._draw_kitchen_layout()
                self._draw_jobs()
                self._draw_chefs()
                self._draw_controls()
                self._draw_status()

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()


def main():
    """Função principal"""
    app = KitchenSimulationPygame()
    app.run()


if __name__ == "__main__":
    main()