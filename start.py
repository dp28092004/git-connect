import random
import sys
from dataclasses import dataclass

import pygame

from logic import GameLogic, DeleteZone


WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 700
FPS = 60


@dataclass
class Palette:
    """Неоклассическая цветовая палитра."""

    background: tuple[int, int, int] = (18, 22, 30)  # глубокий темно‑синий
    frame_outer: tuple[int, int, int] = (210, 210, 215)  # светлый «мрамор»
    frame_inner: tuple[int, int, int] = (32, 38, 50)
    accent_gold: tuple[int, int, int] = (212, 175, 55)
    accent_blue: tuple[int, int, int] = (120, 160, 220)
    inventory_bg: tuple[int, int, int] = (24, 27, 35)
    inventory_border: tuple[int, int, int] = (160, 160, 170)
    delete_bg: tuple[int, int, int] = (80, 28, 40)
    delete_border: tuple[int, int, int] = (160, 70, 95)
    text_main: tuple[int, int, int] = (235, 235, 240)
    text_muted: tuple[int, int, int] = (180, 180, 190)


class GameUI:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("NeoClassic Balls")

        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.palette = Palette()

        inventory_panel_width = 260

        # Геометрия рамки и внутреннего поля, чтобы
        # логические координаты совпадали с "миром" без учёта панелей
        frame_rect = pygame.Rect(20, 20, WINDOW_WIDTH - 40, WINDOW_HEIGHT - 40)
        inner_rect = frame_rect.inflate(-16, -16)
        self.inner_rect = inner_rect

        # Область мира (в логических координатах 0..world_width / 0..world_height)
        world_rect = pygame.Rect(
            inner_rect.left + 12,
            inner_rect.top + 56,
            inner_rect.width - inventory_panel_width - 24,
            inner_rect.height - 96,
        )
        self.world_rect = world_rect
        world_width = world_rect.width
        world_height = world_rect.height

        # Зона удаления — элегантная «чаша» внизу
        delete_zone_height = 90
        self.delete_zone = DeleteZone(
            x1=40,
            y1=world_height - delete_zone_height - 20,
            x2=world_width - 40,
            y2=world_height - 20,
        )

        self.logic = GameLogic(
            width=world_width,
            height=world_height,
            delete_zone=self.delete_zone,
        )

        # Шрифты
        self.font_title = pygame.font.SysFont("Georgia", 32, bold=True)
        self.font_small = pygame.font.SysFont("Georgia", 16)
        self.font_medium = pygame.font.SysFont("Georgia", 20)

        self.inventory_panel_rect = pygame.Rect(
            world_rect.right,
            0,
            inventory_panel_width,
            WINDOW_HEIGHT,
        )

        self.running = True

    # ---------- Основной цикл ----------
    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self._handle_events(dt)
            self.logic.update(dt)
            self._draw()

        pygame.quit()
        sys.exit(0)

    # ---------- Обработка событий ----------
    def _handle_events(self, dt: float) -> None:  # noqa: ARG002
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    self._spawn_random_ball()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    # ЛКМ — выплюнуть шарик из инвентаря
                    mouse_pos_window = pygame.mouse.get_pos()
                    mouse_pos = (
                        mouse_pos_window[0] - self.world_rect.left,
                        mouse_pos_window[1] - self.world_rect.top,
                    )
                    # Стреляем немного вверх и в сторону центра
                    direction = (-0.1, -1.0)  # лёгкий наклон влево, как из арки
                    self.logic.spit_ball_from_inventory(
                        mouse_pos=mouse_pos, direction=direction
                    )

        # Удержание ПКМ — «всасывание» шариков в инвентарь
        buttons = pygame.mouse.get_pressed(3)
        if buttons[2]:
            mouse_pos_window = pygame.mouse.get_pos()
            mouse_pos = (
                mouse_pos_window[0] - self.world_rect.left,
                mouse_pos_window[1] - self.world_rect.top,
            )
            self.logic.suck_balls_with_mouse(mouse_pos=mouse_pos)

    # ---------- Логика спавна ----------
    def _spawn_random_ball(self) -> None:
        # Небольшая область в центре — «зона создания»
        spawn_x = random.randint(80, WINDOW_WIDTH // 2)
        spawn_y = random.randint(80, WINDOW_HEIGHT // 2)

        speed = random.randint(60, 160)
        angle = random.random() * 3.1415 * 2
        vel = pygame.Vector2(speed, 0).rotate_rad(angle)

        radius = random.randint(14, 26)

        # Умеренная палитра, как у пастельных шариков
        base_colors = [
            (196, 189, 151),
            (175, 196, 211),
            (205, 173, 176),
            (183, 205, 186),
            (211, 199, 173),
        ]
        color = random.choice(base_colors)

        self.logic.create_ball(
            position=(spawn_x, spawn_y),
            velocity=(vel.x, vel.y),
            radius=radius,
            color=color,
        )

    # ---------- Отрисовка ----------
    def _draw(self) -> None:
        self.screen.fill(self.palette.background)

        # Внешняя рамка в неоклассическом стиле
        frame_rect = pygame.Rect(20, 20, WINDOW_WIDTH - 40, WINDOW_HEIGHT - 40)
        pygame.draw.rect(self.screen, self.palette.frame_outer, frame_rect, border_radius=12)

        inner_rect = self.inner_rect
        pygame.draw.rect(self.screen, self.palette.frame_inner, inner_rect, border_radius=10)

        # Разделительная линия между миром и инвентарём
        pygame.draw.line(
            self.screen,
            self.palette.accent_gold,
            (inner_rect.right - self.inventory_panel_rect.width, inner_rect.top),
            (inner_rect.right - self.inventory_panel_rect.width, inner_rect.bottom),
            2,
        )

        # Мир
        self._draw_world()

        # Инвентарь
        self._draw_inventory_panel()

        pygame.display.flip()

    def _draw_world(self) -> None:
        inner_rect = self.inner_rect
        world_rect = self.world_rect

        # Подложка мира
        pygame.draw.rect(
            self.screen,
            (26, 32, 44),
            world_rect,
            border_radius=16,
        )

        # Заголовок
        title_surface = self.font_title.render("NeoClassic Orbs", True, self.palette.text_main)
        self.screen.blit(
            title_surface, (world_rect.left, inner_rect.top + 16)
        )

        # Зона удаления — «чаша»
        dz = self.delete_zone
        delete_rect = pygame.Rect(
            self.world_rect.left + dz.x1,
            self.world_rect.top + dz.y1,
            dz.x2 - dz.x1,
            dz.y2 - dz.y1,
        )

        pygame.draw.rect(
            self.screen,
            self.palette.delete_bg,
            delete_rect,
            border_radius=30,
        )
        pygame.draw.rect(
            self.screen,
            self.palette.delete_border,
            delete_rect,
            width=2,
            border_radius=30,
        )

        delete_text = self.font_small.render("DELETE ZONE", True, self.palette.text_main)
        text_rect = delete_text.get_rect(center=delete_rect.center)
        self.screen.blit(delete_text, text_rect)

        # Шарики
        for ball in self.logic.balls:
            if getattr(ball, "in_inventory", False):
                continue
            pygame.draw.circle(
                self.screen,
                ball.color,
                (
                    int(self.world_rect.left + ball.position[0]),
                    int(self.world_rect.top + ball.position[1]),
                ),
                int(ball.radius),
            )

    def _draw_inventory_panel(self) -> None:
        inner_rect = self.inner_rect
        panel_rect = pygame.Rect(
            inner_rect.right - self.inventory_panel_rect.width + 12,
            inner_rect.top + 32,
            self.inventory_panel_rect.width - 24,
            inner_rect.height - 64,
        )

        pygame.draw.rect(
            self.screen,
            self.palette.inventory_bg,
            panel_rect,
            border_radius=14,
        )
        pygame.draw.rect(
            self.screen,
            self.palette.inventory_border,
            panel_rect,
            width=2,
            border_radius=14,
        )

        title = self.font_medium.render("Inventory", True, self.palette.text_main)
        self.screen.blit(title, (panel_rect.left + 16, panel_rect.top + 12))

        help_lines = [
            "SPACE  — создать шар",
            "ПКМ    — затянуть в инвентарь",
            "ЛКМ    — выпустить шар",
            "ESC    — выход",
        ]
        y = panel_rect.top + 44
        for line in help_lines:
            text = self.font_small.render(line, True, self.palette.text_muted)
            self.screen.blit(text, (panel_rect.left + 16, y))
            y += 20

        # Иконки шариков в инвентаре
        y += 16
        x = panel_rect.left + 32
        max_per_row = 4
        spacing = 34

        for idx, ball in enumerate(self.logic.inventory.balls):
            row = idx // max_per_row
            col = idx % max_per_row
            bx = x + col * spacing
            by = y + row * spacing

            pygame.draw.circle(
                self.screen,
                ball.color,
                (bx, by),
                10,
            )


if __name__ == "__main__":
    GameUI().run()
