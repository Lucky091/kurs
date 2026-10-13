"""Расписание проверяется без отрисовки и без зависимостей от ресурсов."""

import unittest
from unittest.mock import patch

import pygame

from systems.waves import WaveManager


class _Enemy(pygame.sprite.Sprite):
    def __init__(self, kind="scout", position=None, wave=1):
        super().__init__()
        self.kind = kind
        self.position = pygame.Vector2(position)
        self.wave = wave


class _Boss(_Enemy):
    def __init__(self, position=None, wave=5):
        super().__init__("boss", position, wave)


class _Meteor(pygame.sprite.Sprite):
    def __init__(self, size, position, velocity):
        super().__init__()
        self.size = size
        self.position = pygame.Vector2(position)
        self.velocity = pygame.Vector2(velocity)


class WaveTests(unittest.TestCase):
    def setUp(self):
        self.patches = [
            patch("systems.waves.Enemy", _Enemy),
            patch("systems.waves.Boss", _Boss),
            patch("systems.waves.Meteor", _Meteor),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)
        self.enemies = pygame.sprite.Group()
        self.meteors = pygame.sprite.Group()
        self.player = pygame.Vector2(640, 550)

    def test_empty_gap_and_pending_objects_do_not_finish_wave(self):
        manager = WaveManager(1, seed=8)
        self.assertFalse(manager.finished(self.enemies, self.meteors))
        manager.update(0.6, self.enemies, self.meteors, self.player)
        self.assertEqual(len(self.enemies), 0)
        self.assertTrue(manager.warnings)
        manager.update(0.9, self.enemies, self.meteors, self.player)
        self.assertEqual(len(self.enemies), 1)
        self.enemies.empty()  # Первый враг уничтожен; расписание ещё идёт.
        self.assertFalse(manager.finished(self.enemies, self.meteors))

    def test_first_wave_exact_plan_and_only_clear_groups_finish(self):
        manager = WaveManager(1, seed=8)
        self.assertEqual(manager.remaining, 8)
        manager.update(60, self.enemies, self.meteors, self.player)
        self.assertEqual(manager.remaining, 0)
        self.assertEqual(len(self.enemies), 6)
        self.assertEqual(len(self.meteors), 2)
        self.assertEqual({enemy.kind for enemy in self.enemies}, {"scout"})
        self.assertFalse(manager.finished(self.enemies, self.meteors))
        self.enemies.empty()  # Gameplay удаляет также ушедших за экран.
        self.assertFalse(manager.finished(self.enemies, self.meteors))
        self.meteors.empty()
        self.assertTrue(manager.finished(self.enemies, self.meteors))
        manager.update(60, self.enemies, self.meteors, self.player)
        self.assertEqual(len(self.enemies) + len(self.meteors), 0)

    def test_new_types_enter_in_their_wave_and_boss_replaces_large_army(self):
        expected = {
            1: {"scout"},
            2: {"scout", "gunner"},
            3: {"scout", "gunner", "interceptor"},
            4: {"scout", "gunner", "interceptor", "heavy"},
        }
        for wave, kinds in expected.items():
            with self.subTest(wave=wave):
                self.enemies.empty()
                self.meteors.empty()
                WaveManager(wave, seed=10).update(100, self.enemies, self.meteors, self.player)
                self.assertEqual({enemy.kind for enemy in self.enemies}, kinds)
        self.enemies.empty()
        self.meteors.empty()
        WaveManager(5, seed=10).update(100, self.enemies, self.meteors, self.player)
        self.assertEqual(sum(enemy.kind == "boss" for enemy in self.enemies), 1)
        self.assertLessEqual(len(self.enemies), 9)

    def test_zero_delta_freezes_warning_and_spawn_timers(self):
        manager = WaveManager(1, seed=8)
        manager.update(0.6, self.enemies, self.meteors, self.player)
        time = manager.elapsed
        warning_time = manager.warnings[0]["timer"]
        remaining = manager.remaining
        for _ in range(100):
            manager.update(0, self.enemies, self.meteors, self.player)
        self.assertEqual(manager.elapsed, time)
        self.assertEqual(manager.remaining, remaining)
        self.assertEqual(manager.warnings[0]["timer"], warning_time)

    def test_safe_entry_and_warning_agree_near_top(self):
        manager = WaveManager(1, seed=8)
        planned_x = manager._schedule[0].position.x
        player = pygame.Vector2(planned_x, 125)
        manager.update(0.6, self.enemies, self.meteors, player)
        warning_x = manager.warnings[0]["position"].x
        self.assertGreaterEqual(abs(warning_x - player.x), 190)
        manager.update(0.9, self.enemies, self.meteors, player)
        enemy = self.enemies.sprites()[0]
        self.assertEqual(enemy.position.x, warning_x)
        self.assertLess(enemy.position.y, 92)

    def test_long_run_plan_remains_bounded(self):
        manager = WaveManager(101, seed=10)
        manager.update(100, self.enemies, self.meteors, self.player)
        self.assertLessEqual(len(self.enemies), 26)
        self.assertLessEqual(len(self.meteors), 5)


if __name__ == "__main__":
    unittest.main()
