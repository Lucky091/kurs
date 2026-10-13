"""Вращающиеся метеориты и разделение с сохранением импульса."""

from __future__ import annotations

import math
import random

import pygame

from settings import HEIGHT, WIDTH
from systems.assets import AssetManager


class Meteor(pygame.sprite.Sprite):
    PARAMETERS = {
        "large": {"hp": 54, "mass": 9.0, "score": 90, "credits": 14},
        "medium": {"hp": 28, "mass": 3.0, "score": 45, "credits": 8},
        "small": {"hp": 12, "mass": 1.0, "score": 20, "credits": 4},
    }

    def __init__(self, size: str = "large", position=(640, -60),
                 velocity=(0, 90), *, mass: float | None = None):
        super().__init__()
        if size not in self.PARAMETERS:
            raise ValueError(f"Неизвестный размер метеорита: {size}")
        self.size = size
        parameters = self.PARAMETERS[size]
        self.hp = float(parameters["hp"])
        self.max_hp = self.hp
        self.mass = float(parameters["mass"] if mass is None else mass)
        self.score_value = parameters["score"]
        self.credit_value = parameters["credits"]
        self.position = pygame.Vector2(position)
        self.velocity = pygame.Vector2(velocity)
        self.escaped = False
        self.rotation = random.uniform(0, 360)
        self.rotation_speed = random.uniform(-42, 42)
        self.original_image = AssetManager().image(f"meteor_{size}")
        self.image = pygame.transform.rotate(self.original_image, self.rotation)
        self.rect = self.image.get_rect(center=self.position)
        self.mask = pygame.mask.from_surface(self.image)
        self._draw_angle = round(self.rotation / 3) * 3
        self._split_done = False

    @property
    def radius(self) -> float:
        return self.original_image.get_width() * 0.46

    def update(self, dt: float) -> None:
        self.position += self.velocity * dt
        self.rotation = (self.rotation + self.rotation_speed * dt) % 360
        draw_angle = round(self.rotation / 3) * 3
        # Квантование угла уменьшает число дорогих пересчётов изображения/маски.
        if draw_angle != self._draw_angle:
            self.image = pygame.transform.rotate(self.original_image, draw_angle)
            self.mask = pygame.mask.from_surface(self.image)
            self.rect = self.image.get_rect(center=self.position)
            self._draw_angle = draw_angle
        else:
            self.rect.center = (round(self.position.x), round(self.position.y))
        if (self.position.y > HEIGHT + 100
                or (self.position.y < -160 and self.velocity.y < 0)
                or self.position.x < -140
                or self.position.x > WIDTH + 140):
            self.escaped = True
            self.kill()

    def take_damage(self, amount: float) -> bool:
        self.hp = max(0.0, self.hp - max(0.0, amount))
        return self.hp <= 0

    def split(self) -> list[Meteor]:
        if self.size == "small" or self._split_done:
            return []
        self._split_done = True
        child_size = "medium" if self.size == "large" else "small"
        count = random.choice((2, 3))
        phase = random.uniform(0, math.tau)
        spread_speed = 52 if self.size == "large" else 68
        separation = 35 if child_size == "medium" else 19
        children = []
        # Равные массы и симметричные радиальные векторы дают Σ m·Δv = 0.
        # Поэтому суммарный импульс детей совпадает с импульсом родителя,
        # даже при двух фрагментах (их масса отличается от типовой).
        for index in range(count):
            angle = phase + index * math.tau / count
            direction = pygame.Vector2(math.cos(angle), math.sin(angle))
            children.append(Meteor(
                child_size, self.position + direction * separation,
                self.velocity + direction * spread_speed,
                mass=self.mass / count,
            ))
        return children
