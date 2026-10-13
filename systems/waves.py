"""Конечное расписание волны: предупреждение, появление, завершение.

Здесь нет зависимости от кадровой частоты или отрисовки игрового экрана.
Менеджер считает только время симуляции, поэтому пауза ничего не сдвигает.
"""

from dataclasses import dataclass
import random

import pygame

from entities.meteors import Meteor
from entities.ships import Boss, Enemy


@dataclass
class _Spawn:
    time: float
    kind: str
    position: pygame.Vector2
    detail: str = ""
    velocity: pygame.Vector2 | None = None
    warned: bool = False


class WaveManager:
    """Одна волна с заранее ограниченным числом опасных объектов.

    ``warnings`` содержит словари с ``position``, ``timer`` и ``kind``.
    Позиция предупреждения лежит у верхней границы игрового поля; сам объект
    появляется выше экрана и плавно входит в поле. ``remaining`` считает
    ещё не появившиеся объекты, включая метеориты и босса.
    """

    WARNING_TIME = 0.85
    ENTRY_Y = 112

    def __init__(self, wave: int, seed: int | None = None):
        self.wave = max(1, int(wave))
        self.elapsed = 0.0
        self.warnings: list[dict] = []
        self._random = random.Random(seed)
        self._schedule = self._build_schedule()
        self._next = 0

    @property
    def remaining(self) -> int:
        return len(self._schedule) - self._next

    def _build_schedule(self) -> list[_Spawn]:
        schedule: list[_Spawn] = []
        if self.wave % 5 == 0:
            schedule.append(_Spawn(2.2, "boss", pygame.Vector2(640, -100)))
            # Эскорт конечен: бесконечные подкрепления могли бы заблокировать
            # магазин даже после уничтожения босса.
            escort_count = min(8, 3 + self.wave // 5)
            for index in range(escort_count):
                kind = "scout" if index % 2 == 0 else "gunner"
                schedule.append(self._enemy(5.0 + index * 3.2, kind))
            meteor_count = 1
        else:
            enemy_count = min(26, 4 + self.wave * 2)
            kinds = ["scout"]
            if self.wave >= 2:
                kinds.append("gunner")
            if self.wave >= 3:
                kinds.append("interceptor")
            if self.wave >= 4:
                kinds.append("heavy")
            interval = max(0.95, 2.15 - (self.wave - 1) * 0.12)
            for index in range(enemy_count):
                # Первое знакомство с новым типом не происходит сразу:
                # сначала игрок успевает увидеть знакомого разведчика.
                kind = kinds[index % len(kinds)]
                schedule.append(self._enemy(1.4 + index * interval, kind))
            meteor_count = min(5, 2 + self.wave // 3)

        for index in range(meteor_count):
            size = "large" if self.wave >= 3 and self.wave % 5 != 0 and index == 0 else "medium"
            time = 5.4 + index * max(3.8, 6.0 - self.wave * 0.15)
            velocity = pygame.Vector2(
                self._random.uniform(-22, 22),
                self._random.uniform(55, 76) + min(self.wave, 20) * 2,
            )
            schedule.append(_Spawn(time, "meteor", self._position(-65), size, velocity))
        return sorted(schedule, key=lambda item: item.time)

    def _position(self, y: float) -> pygame.Vector2:
        return pygame.Vector2(self._random.uniform(115, 1165), y)

    def _enemy(self, time: float, kind: str) -> _Spawn:
        return _Spawn(time, "enemy", self._position(-55), kind)

    def _safe_entry(self, event: _Spawn, player: pygame.Vector2) -> None:
        # При движении вдоль верхней границы входящий объект должен быть
        # виден сбоку. Выбранное место затем сохраняется до появления,
        # чтобы предупреждение действительно указывало направление входа.
        if player.y < 245 and abs(event.position.x - player.x) < 190:
            safe_x = [x for x in (150, 350, 640, 930, 1130) if abs(x - player.x) >= 190]
            event.position.x = self._random.choice(safe_x)
        event.warned = True

    def update(
        self,
        dt: float,
        enemies: pygame.sprite.Group,
        meteors: pygame.sprite.Group,
        player_position: pygame.Vector2,
    ) -> None:
        if dt <= 0:
            return
        self.elapsed += dt
        player = pygame.Vector2(player_position)

        for event in self._schedule[self._next:]:
            if event.time > self.elapsed + self.WARNING_TIME:
                break
            if not event.warned:
                self._safe_entry(event, player)

        while self._next < len(self._schedule):
            event = self._schedule[self._next]
            if event.time > self.elapsed:
                break
            if event.kind == "enemy":
                enemies.add(Enemy(kind=event.detail, position=event.position.copy(), wave=self.wave))
            elif event.kind == "boss":
                enemies.add(Boss(position=event.position.copy(), wave=self.wave))
            else:
                meteors.add(Meteor(size=event.detail, position=event.position.copy(), velocity=event.velocity.copy()))
            self._next += 1

        self.warnings = [
            {
                "position": pygame.Vector2(event.position.x, self.ENTRY_Y),
                "timer": max(0.0, event.time - self.elapsed),
                "kind": event.detail if event.kind == "enemy" else event.kind,
            }
            for event in self._schedule[self._next:]
            if event.warned
        ]

    def finished(self, enemies: pygame.sprite.Group, meteors: pygame.sprite.Group) -> bool:
        """Пустой экран между появлениями не означает конец волны.

        Удаление улетевших объектов выполняет Gameplay. Группы при этом
        содержат только активные объекты, включая фрагменты метеоритов.
        """
        return self.remaining == 0 and len(enemies) == 0 and len(meteors) == 0

    def draw_warnings(self, surface: pygame.Surface) -> None:
        for warning in self.warnings:
            x, y = warning["position"]
            intensity = 130 + int(110 * (1 - warning["timer"] / self.WARNING_TIME))
            color = (255, max(85, intensity), 90)
            pygame.draw.polygon(surface, color, [(x - 8, y - 8), (x + 8, y - 8), (x, y + 6)], 2)
            pygame.draw.line(surface, color, (x, y + 12), (x, y + 23), 2)
