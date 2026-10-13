"""Три вида снарядов с общей логикой движения и временем жизни."""

from __future__ import annotations

import math

import pygame

from settings import HEIGHT, WIDTH
from systems.assets import AssetManager


class Projectile(pygame.sprite.Sprite):
    """Снаряд хранит позицию с дробной частью, rect нужен для столкновений."""

    asset_name = "laser"
    collision_radius = 4
    lifetime = 5.0

    def __init__(self, position, velocity, damage: float, owner: str = "player"):
        super().__init__()
        self.position = pygame.Vector2(position)
        self.velocity = pygame.Vector2(velocity)
        self.damage = float(damage)
        self.owner = owner
        self.age = 0.0
        self.expired = False
        self.hit_targets: set[object] = set()
        self.remaining_pierces = 1
        image_name = self.asset_name
        if owner == "enemy":
            image_name = "enemy_plasma" if image_name == "plasma" else "enemy_laser"
        original = AssetManager().image(image_name)
        # Рисунок снаряда смотрит вверх; угол берём из вектора его скорости.
        angle = math.degrees(math.atan2(-self.velocity.x, -self.velocity.y))
        self.image = pygame.transform.rotate(original, angle)
        self.rect = self.image.get_rect(center=self.position)
        self.mask = pygame.mask.from_surface(self.image)

    @property
    def radius(self) -> float:
        return self.collision_radius

    def update(self, dt: float) -> None:
        self.position += self.velocity * dt
        self.age += dt
        self.rect.center = (round(self.position.x), round(self.position.y))
        if (self.age > self.lifetime or self.position.y < -100
                or self.position.y > HEIGHT + 100 or self.position.x < -100
                or self.position.x > WIDTH + 100):
            self.expired = True
            self.kill()


class Laser(Projectile):
    """Быстрый точный выстрел с короткой перезарядкой."""

    asset_name = "laser"
    collision_radius = 4


class Rocket(Projectile):
    """Взрыв наносится игровой системой один раз в ограниченном радиусе."""

    asset_name = "rocket"
    collision_radius = 8
    explosion_radius = 82


class Plasma(Projectile):
    """Каждая цель учитывается единожды; после трёх целей снаряд исчезает."""

    asset_name = "plasma"
    collision_radius = 11

    def __init__(self, position, velocity, damage: float, owner: str = "player"):
        super().__init__(position, velocity, damage, owner)
        self.remaining_pierces = 3 if owner == "player" else 1
