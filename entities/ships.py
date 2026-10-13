"""Корабли: общая модель, управление игроком и различимый ИИ врагов."""

from __future__ import annotations

import math
import random

import pygame

from settings import HEIGHT, PLAY_BOUNDS, WIDTH
from systems.assets import AssetManager
from .projectiles import Laser, Plasma, Rocket


class SpaceShip(pygame.sprite.Sprite):
    def __init__(self, position, image_name: str, max_hp: float):
        super().__init__()
        self.position = pygame.Vector2(position)
        self.velocity = pygame.Vector2()
        self.original_image = AssetManager().image(image_name)
        self.image = self.original_image
        self.rect = self.image.get_rect(center=self.position)
        self.mask = pygame.mask.from_surface(self.image)
        self.rotation = 0.0
        self._image_rotation = 0.0
        self._hp = float(max_hp)
        self.max_hp = float(max_hp)

    @property
    def hp(self) -> float:
        return self._hp

    @hp.setter
    def hp(self, value: float) -> None:
        self._hp = value

    @property
    def radius(self) -> float:
        return min(self.original_image.get_size()) * 0.42

    def sync_image(self) -> None:
        if self._image_rotation != self.rotation:
            self.image = pygame.transform.rotate(self.original_image, self.rotation)
            self.mask = pygame.mask.from_surface(self.image)
            self.rect = self.image.get_rect(center=self.position)
            self._image_rotation = self.rotation
        else:
            self.rect.center = (round(self.position.x), round(self.position.y))

    def take_damage(self, amount: float) -> bool:
        self.hp = max(0.0, self.hp - max(0.0, amount))
        return self.hp <= 0


class Player(SpaceShip):
    WEAPON_NAMES = ("laser", "rocket", "plasma")
    BASE_INTERVALS = {"laser": 0.19, "rocket": 0.95, "plasma": 0.49}
    SHIELD_DELAY = 3.5

    def __init__(self, progress):
        self.progress = progress
        super().__init__((WIDTH / 2, HEIGHT - 100), "player", progress.max_health)
        self.cooldown = 0.0
        self.invulnerability = 0.0
        self.shield_delay = 0.0

    @property
    def hp(self) -> float:
        return self.progress.health

    @hp.setter
    def hp(self, value: float) -> None:
        self.progress.health = value

    @property
    def fire_interval(self) -> float:
        return self.BASE_INTERVALS[self.progress.weapon] / self.progress.fire_rate

    def update(self, dt: float, direction=None) -> None:
        direction = pygame.Vector2() if direction is None else pygame.Vector2(direction)
        # Единичный вектор делает скорость одинаковой по осям и по диагонали.
        if direction.length_squared() > 1:
            direction.normalize_ip()
        self.velocity = direction * self.progress.speed
        self.position += self.velocity * dt
        half_width = self.original_image.get_width() / 2
        half_height = self.original_image.get_height() / 2
        self.position.x = max(PLAY_BOUNDS.left + half_width,
                              min(PLAY_BOUNDS.right - half_width, self.position.x))
        self.position.y = max(PLAY_BOUNDS.top + half_height,
                              min(PLAY_BOUNDS.bottom - half_height, self.position.y))
        self.cooldown = max(0.0, self.cooldown - dt)
        self.invulnerability = max(0.0, self.invulnerability - dt)
        old_shield_delay = self.shield_delay
        self.shield_delay = max(0.0, self.shield_delay - dt)
        if self.progress.max_shield and self.shield_delay <= 0:
            # Если задержка закончилась внутри кадра, восстанавливаем за остаток dt.
            recharge_dt = max(0.0, dt - old_shield_delay)
            rate = 10 + self.progress.max_shield * 0.045
            self.progress.shield = min(self.progress.max_shield,
                                       self.progress.shield + rate * recharge_dt)
        self.max_hp = self.progress.max_health
        self.sync_image()

    def select_weapon(self, index: int) -> bool:
        if not 1 <= index <= len(self.WEAPON_NAMES):
            return False
        name = self.WEAPON_NAMES[index - 1]
        if name not in self.progress.weapons:
            return False
        self.progress.weapon = name
        # Общая перезарядка сохраняется: переключение не даёт лишних выстрелов.
        return True

    def try_shoot(self) -> list:
        if self.cooldown > 0 or self.hp <= 0:
            return []
        weapon = self.progress.weapon
        position = self.position + pygame.Vector2(0, -self.original_image.get_height() * 0.43)
        multiplier = self.progress.damage_multiplier
        if weapon == "rocket":
            shot = Rocket(position, (0, -490), 42 * multiplier)
        elif weapon == "plasma":
            shot = Plasma(position, (0, -430), 23 * multiplier)
        else:
            shot = Laser(position, (0, -850), 11 * multiplier)
        self.cooldown = self.fire_interval
        return [shot]

    def take_damage(self, amount: float) -> bool:
        if self.hp <= 0:
            return True
        if self.invulnerability > 0 or amount <= 0:
            return False
        self.shield_delay = self.SHIELD_DELAY
        absorbed = min(self.progress.shield, amount)
        self.progress.shield -= absorbed
        self.hp = max(0.0, self.hp - (amount - absorbed))
        self.invulnerability = 0.85
        return self.hp <= 0


class Enemy(SpaceShip):
    PARAMETERS = {
        "scout": (22, 80, 18, 104, 3.1),
        "gunner": (38, 130, 28, 68, 2.5),
        "interceptor": (32, 160, 34, 112, 2.9),
        "heavy": (98, 250, 52, 51, 3.1),
    }

    def __init__(self, kind: str = "scout", position=(640, -55), wave: int = 1):
        if kind not in self.PARAMETERS:
            raise ValueError(f"Неизвестный тип врага: {kind}")
        hp, score, credits, speed, fire_interval = self.PARAMETERS[kind]
        scale = 1 + max(0, wave - 1) * 0.055
        super().__init__(position, kind, hp * scale)
        self.kind = kind
        self.wave = wave
        self.score_value = score
        self.credit_value = credits
        self.speed = min(210, speed * (1 + (wave - 1) * 0.025))
        self.fire_interval = max(1.25, fire_interval - max(0, wave - 1) * 0.045)
        self.cooldown = random.uniform(1.2, 2.0)
        self.warning_timer = 0.0
        self.escaped = False
        self.elapsed = random.uniform(0, math.tau)
        self.base_x = self.position.x
        self.aim_direction = pygame.Vector2(0, 1)
        self._aim_locked = False
        self._reaction_timer = random.uniform(0.0, 0.3)
        self._dodge_velocity = 0.0

    def _consider_dodge(self, projectiles) -> None:
        nearest = None
        nearest_time = float("inf")
        for shot in projectiles:
            if shot.owner != "player":
                continue
            relative_position = shot.position - self.position
            relative_velocity = shot.velocity - self.velocity
            speed_squared = relative_velocity.length_squared()
            if speed_squared < 1:
                continue
            # Минимум |r + v·t|² находится при t = -r·v / |v|².
            # Враг проверяет сближение, а не просто наличие пули под собой.
            closest_time = -relative_position.dot(relative_velocity) / speed_squared
            if not 0.09 < closest_time < 0.85:
                continue
            closest_position = relative_position + relative_velocity * closest_time
            safe_distance = self.radius + shot.radius + 19
            if closest_position.length_squared() < safe_distance ** 2:
                if closest_time < nearest_time:
                    nearest_time = closest_time
                    nearest = closest_position
        if nearest is not None:
            # Ошибка оценки, задержка реакции и предел скорости оставляют шанс попасть.
            side = -1 if nearest.x + random.uniform(-16, 16) > 0 else 1
            self._dodge_velocity = side * min(190, 135 + self.wave * 4)

    def update(self, dt: float, player_position, player_projectiles=()) -> None:
        self.elapsed += dt
        old_position = self.position.copy()
        self.position.y += self.speed * dt
        if self.kind == "scout":
            self.position.x = self.base_x + math.sin(self.elapsed * 1.7) * 88
        elif self.kind == "interceptor":
            self._reaction_timer -= dt
            if self._reaction_timer <= 0:
                self._consider_dodge(player_projectiles)
                self._reaction_timer = 0.30 + random.uniform(0, 0.07)
            self.position.x += self._dodge_velocity * dt
            self._dodge_velocity *= math.exp(-dt * 2.0)
        elif self.kind == "heavy":
            self.position.x = self.base_x + math.sin(self.elapsed * 0.7) * 26
        half_width = self.original_image.get_width() / 2
        self.position.x = max(PLAY_BOUNDS.left + half_width,
                              min(PLAY_BOUNDS.right - half_width, self.position.x))
        if dt > 0:
            self.velocity = (self.position - old_position) / dt
        # Таймер первого выстрела начинается после входа в поле: иначе враг
        # с долгим подлётом мог бы выстрелить без предупреждения при появлении.
        if self.position.y > PLAY_BOUNDS.top + 12:
            self.cooldown -= dt
        if self.position.y > PLAY_BOUNDS.top + 12 and self.cooldown <= 0.38:
            if not self._aim_locked:
                direction = pygame.Vector2(player_position) - self.position
                self.aim_direction = direction.normalize() if direction.length_squared() else pygame.Vector2(0, 1)
                self._aim_locked = True
            self.warning_timer = max(0.001, self.cooldown)
        else:
            self.warning_timer = 0.0
        self.sync_image()
        if self.position.y > HEIGHT + 85:
            self.escaped = True
            self.kill()

    def try_shoot(self) -> list:
        if self.cooldown > 0 or self.position.y < PLAY_BOUNDS.top + 12 or self.escaped:
            return []
        self.cooldown = self.fire_interval
        self._aim_locked = False
        self.warning_timer = 0.0
        speed = min(455, 265 + self.wave * 7)
        muzzle = self.position + pygame.Vector2(0, self.original_image.get_height() * 0.39)
        damage = 11 if self.kind != "heavy" else 14
        if self.kind == "heavy":
            return [Laser(muzzle, self.aim_direction.rotate(angle) * speed, damage, "enemy")
                    for angle in (-32, -16, 0, 16, 32)]
        if self.kind == "scout":
            return [Laser(muzzle, (0, speed), damage, "enemy")]
        return [Laser(muzzle, self.aim_direction * speed, damage, "enemy")]

    def draw(self, surface: pygame.Surface) -> None:
        if self.warning_timer <= 0:
            return
        origin = self.position + pygame.Vector2(0, self.original_image.get_height() * 0.4)
        direction = pygame.Vector2(0, 1) if self.kind == "scout" else self.aim_direction
        angles = (-32, 0, 32) if self.kind == "heavy" else (0,)
        for angle in angles:
            end = origin + direction.rotate(angle) * 110
            pygame.draw.line(surface, (255, 125, 76), origin, end, 1)
        pygame.draw.circle(surface, (255, 181, 88), origin, 7, 2)


class Boss(Enemy):
    """Фазы меняют темп, но все шаблоны оставляют проходимые промежутки."""

    ATTACK_NAMES = ("ВЕЕР", "ПРИЦЕЛ", "КОРИДОРЫ")

    def __init__(self, position=(640, -100), wave: int = 5):
        SpaceShip.__init__(self, position, "boss", 620 + max(0, wave - 5) * 64)
        self.kind = "boss"
        self.wave = wave
        self.score_value = 2000 + wave * 80
        self.credit_value = 220 + wave * 12
        self.cooldown = 2.0
        self.warning_timer = 0.0
        self.escaped = False
        self.elapsed = 0.0
        self.attack_index = 0
        self.aim_direction = pygame.Vector2(0, 1)
        self._aim_locked = False
        self._gap_index = 4
        self._warned_lanes = []

    @property
    def phase(self) -> int:
        return 1 if self.hp > self.max_hp * 0.5 else 2

    @property
    def attack_name(self) -> str:
        return self.ATTACK_NAMES[self.attack_index % 3]

    def update(self, dt: float, player_position, player_projectiles=()) -> None:
        self.elapsed += dt
        old_position = self.position.copy()
        if self.position.y < 165:
            self.position.y = min(165, self.position.y + 110 * dt)
        else:
            self.position.x = WIDTH / 2 + math.sin(self.elapsed * 0.55) * 190
            self.position.y = 165 + math.sin(self.elapsed * 0.8) * 12
            self.cooldown -= dt
        if dt > 0:
            self.velocity = (self.position - old_position) / dt
        if self.position.y >= 153 and self.cooldown <= 0.7:
            if not self._aim_locked:
                direction = pygame.Vector2(player_position) - self.position
                self.aim_direction = direction.normalize() if direction.length_squared() else pygame.Vector2(0, 1)
                self._gap_index = max(0, min(8, round((player_position[0] - 160) / 120)))
                self._warned_lanes = [160 + index * 120 for index in range(9)
                                     if abs(index - self._gap_index) > 0]
                self._aim_locked = True
            self.warning_timer = max(0.001, self.cooldown)
        else:
            self.warning_timer = 0.0
        self.sync_image()

    def try_shoot(self) -> list:
        if self.cooldown > 0 or self.position.y < 150:
            return []
        muzzle = self.position + pygame.Vector2(0, 56)
        speed = 245 if self.phase == 1 else 285
        attack = self.attack_index % 3
        if attack == 0:
            # Между лучами на дистанции игрока остаётся 70–130 пикселей.
            angles = range(-64, 65, 16)
            shots = [Laser(muzzle, pygame.Vector2(0, speed).rotate(angle), 13, "enemy")
                     for angle in angles if angle not in (-16, 16)]
        elif attack == 1:
            shots = [Plasma(muzzle, self.aim_direction.rotate(angle) * (speed + 25), 17, "enemy")
                     for angle in (-22, 0, 22)]
        else:
            # Один коридор шириной 120 px свободен; он предупреждён заранее.
            shots = [Laser((x, self.position.y + 35), (0, speed + 15), 13, "enemy")
                     for x in self._warned_lanes]
        self.attack_index += 1
        self.cooldown = 2.1 if self.phase == 1 else 1.45
        self.warning_timer = 0.0
        self._aim_locked = False
        return shots

    def draw(self, surface: pygame.Surface) -> None:
        if self.warning_timer <= 0:
            return
        attack = self.attack_index % 3
        origin = self.position + pygame.Vector2(0, 56)
        if attack == 2:
            for x in self._warned_lanes:
                pygame.draw.line(surface, (113, 54, 57), (x, self.position.y + 40),
                                 (x, PLAY_BOUNDS.bottom), 2)
                pygame.draw.circle(surface, (255, 147, 82), (x, self.position.y + 40), 5, 1)
        else:
            # Предупреждение должно совпадать со всеми реальными лучами.
            angles = (-64, -48, -32, 0, 32, 48, 64) if attack == 0 else (-22, 0, 22)
            direction = pygame.Vector2(0, 1) if attack == 0 else self.aim_direction
            for angle in angles:
                end = origin + direction.rotate(angle) * 230
                pygame.draw.line(surface, (178, 72, 63), origin, end, 2)
        pygame.draw.circle(surface, (255, 180, 90), origin, 14, 2)
