"""Многослойный параллакс и неподвижная туманность, рассчитанная один раз."""
import math
import random
import pygame


class Starfield:
    def __init__(self, seed=42, width=1280, height=720):
        self.width, self.height = width, height
        self.time = 0.0
        rng = random.Random(seed)
        self.layers = []
        for count, speed, radius, brightness in ((115, 12, 1, 65), (70, 30, 1, 115), (32, 62, 2, 190)):
            self.layers.append((speed, radius, brightness, [
                [rng.uniform(0, width), rng.uniform(0, height), rng.uniform(0, math.tau)]
                for _ in range(count)
            ]))
        self.backdrop = pygame.Surface((width, height))
        for y in range(height):
            v = y / height
            pygame.draw.line(self.backdrop, (5 + int(2*v), 9 + int(3*v), 20 + int(7*v)), (0, y), (width, y))
        # Низкое разрешение размывает границы и экономит память и время генерации.
        nebula = pygame.Surface((320, 180))
        for cx, cy, radius, base in ((78, 30, 96, (8, 18, 30)), (270, 135, 90, (17, 9, 27)), (187, 56, 60, (4, 12, 22))):
            cloud = pygame.Surface(nebula.get_size())
            for r in range(radius, 0, -2):
                strength = (1 - r / radius) ** 2
                color = tuple(int(channel * strength) for channel in base)
                pygame.draw.circle(cloud, color, (cx, cy), r)
            nebula.blit(cloud, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        self.backdrop.blit(pygame.transform.smoothscale(nebula, (width, height)), (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def update(self, dt):
        self.time += dt
        for speed, _, _, stars in self.layers:
            for star in stars:
                star[1] = (star[1] + speed * dt) % self.height

    def draw(self, surface):
        surface.blit(self.backdrop, (0, 0))
        for _, radius, brightness, stars in self.layers:
            for x, y, phase in stars:
                level = int(brightness * (.85 + .15 * math.sin(self.time * .8 + phase)))
                color = (level, min(255, level + 10), min(255, level + 28))
                point = (int(x), int(y))
                if radius == 2:
                    pygame.draw.circle(surface, (level//6, level//5, level//3), point, 4)
                pygame.draw.circle(surface, color, point, radius)
