"""Бонусы падают медленнее препятствий и не наносят контактного урона."""

from __future__ import annotations

import math

import pygame

from settings import HEIGHT
from systems.assets import AssetManager


class Bonus(pygame.sprite.Sprite):
    def __init__(self, kind: str, position, value: int = 15):
        super().__init__()
        if kind not in ("health", "credits", "shield"):
            raise ValueError(f"Неизвестный бонус: {kind}")
        self.kind = kind
        self.value = value
        self.position = pygame.Vector2(position)
        self.velocity = pygame.Vector2(0, 85)
        self.age = 0.0
        self.image = AssetManager().image(f"bonus_{kind}")
        self.rect = self.image.get_rect(center=self.position)
        self.mask = pygame.mask.from_surface(self.image)
        self.expired = False

    def update(self, dt: float) -> None:
        self.age += dt
        self.position += self.velocity * dt
        self.rect.center = (round(self.position.x + math.sin(self.age * 3) * 5),
                            round(self.position.y))
        if self.position.y > HEIGHT + 40:
            self.expired = True
            self.kill()
