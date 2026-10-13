"""Проверки реальных ресурсов и жизненного цикла SDL без окна/устройства."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import unittest
import pygame

from systems.assets import AssetManager
from systems.particles import ParticleSystem


class ResourceTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((100, 100))
        self.assets = AssetManager()
        self.assets.clear_runtime_cache()

    def tearDown(self):
        self.assets.clear_runtime_cache()
        pygame.quit()

    def test_singleton_caches_images_and_cyrillic_fonts(self):
        self.assertIs(self.assets, AssetManager())
        self.assertIs(self.assets.image("player"), self.assets.image("player"))
        self.assertIs(self.assets.font(24), self.assets.font(24))
        rendered = self.assets.font(24).render("Звёздный рубеж", True, (255, 255, 255))
        self.assertGreater(rendered.get_width(), 100)
        for name in ("player", "scout", "gunner", "interceptor", "heavy", "boss",
                     "meteor_large", "meteor_medium", "meteor_small", "laser", "rocket", "plasma"):
            self.assertGreater(pygame.mask.from_surface(self.assets.image(name)).count(), 0)

    def test_runtime_cache_can_restart_after_pygame_quit(self):
        first_font = self.assets.font(18)
        pygame.mixer.init()
        first_sound = self.assets.sound("laser")
        self.assertIsNotNone(first_sound)
        self.assets.clear_runtime_cache()
        pygame.quit()
        pygame.font.init()
        pygame.mixer.init()
        new_font = self.assets.font(18)
        new_sound = self.assets.sound("laser")
        self.assertIsNot(new_font, first_font)
        self.assertIsNot(new_sound, first_sound)
        self.assertGreater(new_font.render("Пилот", True, (255, 255, 255)).get_width(), 0)
        self.assertGreater(new_sound.get_length(), 0)

    def test_particles_are_visible_on_transparent_world_layer(self):
        particles = ParticleSystem()
        particles.emit((50, 50), (90, 220, 255), count=1)
        world = pygame.Surface((100, 100), pygame.SRCALPHA)
        particles.draw(world)
        self.assertGreater(world.get_at((50, 50)).a, 0)
        background = pygame.Surface((100, 100))
        background.fill((5, 10, 20))
        background.blit(world, (0, 0))
        self.assertGreater(background.get_at((50, 50)).b, 20)

    def test_particle_limit_lifetime_and_zero_quality(self):
        particles = ParticleSystem()
        particles.emit((50, 50), (90, 220, 255), count=10000)
        self.assertEqual(len(particles.particles), particles.MAX_PARTICLES)
        particles.update(10)
        self.assertEqual(len(particles.particles), 0)
        particles.amount = 0
        particles.emit((50, 50), (90, 220, 255), count=20)
        self.assertEqual(len(particles.particles), 0)


if __name__ == "__main__":
    unittest.main()
