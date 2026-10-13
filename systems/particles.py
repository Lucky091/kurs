"""Лёгкие частицы; вся симуляция зависит от dt и замирает вместе с боем."""
from dataclasses import dataclass
import random
import pygame


@dataclass
class Particle:
    position: pygame.Vector2
    velocity: pygame.Vector2
    color: tuple
    lifetime: float
    age: float = 0.0
    radius: float = 2.0


class ParticleSystem:
    MAX_PARTICLES = 1000

    def __init__(self, amount=1.0):
        self.amount = float(amount)
        self.particles = []
        self._layer = None

    def emit(self, position, color, count=12, speed=120, lifetime=.5):
        available = self.MAX_PARTICLES - len(self.particles)
        count = min(available, max(0, int(count * self.amount)))
        for _ in range(count):
            velocity = pygame.Vector2(1, 0).rotate(random.uniform(0, 360))
            velocity *= speed * random.uniform(.22, 1.0)
            self.particles.append(Particle(
                pygame.Vector2(position), velocity, tuple(color)[:3],
                max(.05, lifetime * random.uniform(.65, 1.25)), radius=random.uniform(1.3, 3.2),
            ))

    def update(self, dt):
        for particle in self.particles:
            particle.age += dt
            particle.position += particle.velocity * dt
            particle.velocity *= max(0, 1 - 1.6 * dt)
        self.particles = [p for p in self.particles if p.age < p.lifetime]

    def draw(self, surface):
        if not self.particles:
            return
        if self._layer is None or self._layer.get_size() != surface.get_size():
            self._layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        self._layer.fill((0, 0, 0, 0))
        for particle in self.particles:
            fade = max(0.0, 1 - particle.age / particle.lifetime)
            color = (*particle.color, round(255 * fade))
            end = particle.position - particle.velocity * .035
            pygame.draw.line(self._layer, color, particle.position, end, max(1, int(particle.radius * fade)))
            pygame.draw.circle(self._layer, color, particle.position, max(1, int(particle.radius * fade)))
        # Обычный alpha-blit виден и на прозрачном слое игрового мира.
        # BLEND_RGB_ADD оставил бы его alpha равной нулю: частицы исчезли бы.
        surface.blit(self._layer, (0, 0))
