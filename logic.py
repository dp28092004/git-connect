from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Iterable
import math
import itertools


Color = Tuple[int, int, int]  # (R, G, B) in [0, 255]
Vec2 = Tuple[float, float]


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def mix_colors_rgb(c1: Color, c2: Color) -> Color:
    """
    Математическое смешивание двух цветов в RGB-модели.

    Новый цвет = поканальное среднее между двумя цветами.
    Используем "правильное" округление, чтобы результат был детерминированным и без смещения.
    """

    def avg(a: int, b: int) -> int:
        return int(round((a + b) / 2.0))

    r = avg(c1[0], c2[0])
    g = avg(c1[1], c2[1])
    b = avg(c1[2], c2[2])
    return int(clamp(r, 0, 255)), int(clamp(g, 0, 255)), int(clamp(b, 0, 255))


@dataclass
class Ball:
    """
    Игровой шарик.

    Только логика: координаты, скорость, цвет, радиус.
    Никакой отрисовки.
    """

    id: int
    position: Vec2
    velocity: Vec2
    radius: float
    color: Color

    # Флаг, что шарик находится в инвентаре, а не в мире
    in_inventory: bool = False

    def move(self, dt: float) -> None:
        """ Простое равномерное движение без ускорения. """
        if self.in_inventory:
            return
        x, y = self.position
        vx, vy = self.velocity
        self.position = (x + vx * dt, y + vy * dt)


@dataclass
class Inventory:
    """
    Логический инвентарь игрока для хранения шариков.
    """

    balls: List[Ball] = field(default_factory=list)

    def add_ball(self, ball: Ball) -> None:
        ball.in_inventory = True
        self.balls.append(ball)

    def remove_ball(self, ball: Ball) -> None:
        self.balls.remove(ball)
        ball.in_inventory = False

    def pop_last(self) -> Optional[Ball]:
        if not self.balls:
            return None
        ball = self.balls.pop()
        ball.in_inventory = False
        return ball

    def __len__(self) -> int:
        return len(self.balls)


@dataclass
class DeleteZone:
    """
    Зона удаления шариков.

    Сейчас реализована как прямоугольник по координатам экрана.
    Можно расширить до произвольной формы при необходимости.
    """

    x1: float
    y1: float
    x2: float
    y2: float

    def contains(self, position: Vec2) -> bool:
        x, y = position
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2


@dataclass
class GameLogic:
    """
    Основной класс, отвечающий за игровую логику шариков.

    НЕ занимается отрисовкой или обработкой событий ОС/фреймворка.
    Предполагается, что внешний интерфейс будет вызывать методы:
      - update() для шага симуляции,
      - suck_balls_with_mouse() для "всасывания" шариков,
      - spit_ball_from_inventory() для "выплёвывания",
      - а также читать состояние списка шариков.
    """

    width: float
    height: float
    delete_zone: DeleteZone

    balls: List[Ball] = field(default_factory=list)
    inventory: Inventory = field(default_factory=Inventory)

    # Параметры логики
    mouse_suck_radius: float = 80.0
    default_spit_speed: float = 300.0

    # Вспомогательный счётчик для уникальных id
    _next_ball_id: int = 1

    def create_ball(
        self,
        position: Vec2,
        velocity: Vec2,
        radius: float,
        color: Color,
    ) -> Ball:
        """ Создать шарик и поместить его в мир. """
        ball = Ball(
            id=self._next_ball_id,
            position=position,
            velocity=velocity,
            radius=radius,
            color=color,
        )
        self._next_ball_id += 1
        self.balls.append(ball)
        return ball

    # ---------------------------
    # Основной шаг симуляции
    # ---------------------------

    def update(self, dt: float) -> None:
        """
        Выполнить один шаг симуляции:
        - движение шариков,
        - обработка столкновений (смешивание цветов),
        - удаление шариков в зоне удаления,
        - удержание шариков в пределах экрана.
        """
        # 1. Движение
        for ball in list(self.balls):
            ball.move(dt)
            self._keep_ball_inside_bounds(ball)

        # 2. Смешивание цветов при соприкосновении
        self._mix_colors_on_collisions()

        # 3. Удаление шариков, попавших в зону удаления
        self._remove_balls_in_delete_zone()

    # ---------------------------
    # Взаимодействие с мышью
    # ---------------------------

    def suck_balls_with_mouse(
        self,
        mouse_pos: Vec2,
        radius: Optional[float] = None,
        max_count: Optional[int] = None,
    ) -> List[Ball]:
        """
        "Всосать" шарики мышкой в инвентарь.

        :param mouse_pos: позиция мыши в координатах мира.
        :param radius: радиус действия "пылесоса"; если None — используется mouse_suck_radius.
        :param max_count: максимум шариков, которые можно затянуть за один вызов;
                          если None — без ограничения.
        :return: список шариков, которые были перемещены в инвентарь.
        """
        if radius is None:
            radius = self.mouse_suck_radius

        moved: List[Ball] = []
        radius_sq = radius * radius

        # Копируем список, чтобы безопасно модифицировать self.balls
        for ball in list(self.balls):
            if max_count is not None and len(moved) >= max_count:
                break
            if self._distance_sq(ball.position, mouse_pos) <= radius_sq:
                self.balls.remove(ball)
                self.inventory.add_ball(ball)
                moved.append(ball)

        return moved

    def spit_ball_from_inventory(
        self,
        mouse_pos: Vec2,
        direction: Optional[Vec2] = None,
        speed: Optional[float] = None,
        ball: Optional[Ball] = None,
    ) -> Optional[Ball]:
        """
        "Выплюнуть" шарик из инвентаря обратно в мир.

        :param mouse_pos: позиция, откуда шарик появится (обычно под мышью).
        :param direction: направление начальной скорости (вектор, необязательно нормированный).
        :param speed: модуль скорости; если None — используется default_spit_speed.
        :param ball: конкретный шарик из инвентаря; если None — берётся последний добавленный.
        :return: шарик, который был выплюнут, либо None, если инвентарь пуст.
        """
        if ball is not None:
            if ball not in self.inventory.balls:
                return None
            self.inventory.remove_ball(ball)
        else:
            ball = self.inventory.pop_last()
            if ball is None:
                return None

        # Устанавливаем позицию и скорость
        ball.position = mouse_pos
        if speed is None:
            speed = self.default_spit_speed

        if direction is None:
            # Если направление не задано — стреляем вверх
            vx, vy = 0.0, -1.0
        else:
            vx, vy = direction
            length = math.hypot(vx, vy)
            if length == 0:
                vx, vy = 0.0, -1.0
            else:
                vx /= length
                vy /= length

        ball.velocity = (vx * speed, vy * speed)
        ball.in_inventory = False
        self.balls.append(ball)
        return ball

    # ---------------------------
    # Вспомогательная логика
    # ---------------------------

    def _keep_ball_inside_bounds(self, ball: Ball) -> None:
        """
        Держим шарики в пределах экрана.
        Здесь нет "отталкивания" между шариками, только взаимодействие со стенками.

        Реализуем простое отражение от границ.
        """
        x, y = ball.position
        vx, vy = ball.velocity

        # Левая/правая граница
        if x - ball.radius < 0:
            x = ball.radius
            vx = abs(vx)
        elif x + ball.radius > self.width:
            x = self.width - ball.radius
            vx = -abs(vx)

        # Верхняя/нижняя граница
        if y - ball.radius < 0:
            y = ball.radius
            vy = abs(vy)
        elif y + ball.radius > self.height:
            y = self.height - ball.radius
            vy = -abs(vy)

        ball.position = (x, y)
        ball.velocity = (vx, vy)

    def _mix_colors_on_collisions(self) -> None:
        """
        Смешивание цветов шариков при соприкосновении.

        - Шарики НЕ отталкиваются и НЕ сливаются, меняется только их цвет.
        - Для каждой пары, которая пересеклась, вычисляем новый цвет
          как среднее двух исходных цветов в RGB.
        - Оба шарика получают один и тот же новый цвет.
        """
        for b1, b2 in itertools.combinations(self.balls, 2):
            if b1.in_inventory or b2.in_inventory:
                continue

            # Проверка соприкосновения
            min_dist = b1.radius + b2.radius
            if self._distance_sq(b1.position, b2.position) <= min_dist * min_dist:
                mixed = mix_colors_rgb(b1.color, b2.color)
                b1.color = mixed
                b2.color = mixed

    def _remove_balls_in_delete_zone(self) -> None:
        """ Удалить все шарики, которые попали в зону удаления. """
        self.balls = [
            ball
            for ball in self.balls
            if not self.delete_zone.contains(ball.position)
        ]

    @staticmethod
    def _distance_sq(a: Vec2, b: Vec2) -> float:
        ax, ay = a
        bx, by = b
        dx = ax - bx
        dy = ay - by
        return dx * dx + dy * dy


# ---------------------------
# Пример использования без UI
# ---------------------------

if __name__ == "__main__":
    # Небольшая демонстрация "в лоб", без визуализации.
    logic = GameLogic(
        width=800,
        height=600,
        delete_zone=DeleteZone(x1=0, y1=560, x2=200, y2=600),  # Прямоугольник снизу слева
    )

    # Создаём пару шариков
    logic.create_ball(position=(100, 100), velocity=(50, 0), radius=20, color=(255, 0, 0))
    logic.create_ball(position=(200, 100), velocity=(-50, 0), radius=20, color=(0, 0, 255))

    # Двигаем систему несколькими шагами
    for i in range(60):
        logic.update(1 / 60.0)

    # Имитация "всасывания" шариков мышью
    sucked = logic.suck_balls_with_mouse(mouse_pos=(150, 100))
    print(f"Всосано шариков: {len(sucked)}")

    # И "выплёвывания" одного шарика
    if sucked:
        spat = logic.spit_ball_from_inventory(
            mouse_pos=(400, 300),
            direction=(1, 0),
        )
        print(f"Выплюнут шарик id={spat.id if spat else None}, цвет={spat.color if spat else None}")


