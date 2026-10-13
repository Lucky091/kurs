"""Реальный бой с боссом: расписание → маски → награда → магазин → волна 6.

Это проверка переходов и интеграции, а не доказательство игрового баланса:
игроку в фикстуре дана длинная неуязвимость, а настоящие лазеры помещаются
в точку столкновения. ИИ, урон, маски, награды и расписание не подменяются.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import tempfile
import unittest

import pygame

from entities.projectiles import Laser
from entities.ships import Boss
from game import Game
from states.menus import UpgradeShop


class BossFlowIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.game = Game(data_dir=self.folder.name)
        self.game.new_run()
        self.state = self.game.gameplay
        # Пропускаем только предшествующие волны при подготовке фикстуры.
        # Саму пятую создаёт обычный метод продолжения забега.
        self.state.progress.wave = 4
        self.state.next_wave()
        self.state.player.invulnerability = 1000.0
        self.state.player.position.update(55, 650)
        self.state.player.sync_image()

    def tearDown(self):
        self.game.close()
        self.folder.cleanup()

    def _hit_with_real_laser(self, boss):
        projectile = Laser(boss.position, (0, -850), 11)
        self.assertIsNotNone(pygame.sprite.collide_mask(projectile, boss))
        before = boss.hp
        self.state.player_projectiles.add(projectile)
        self.state.resolve_collisions()
        self.assertAlmostEqual(boss.hp, max(0, before - projectile.damage))
        self.assertFalse(projectile.alive())
        return projectile

    def test_finite_wave_boss_phases_reward_once_and_continuation(self):
        state = self.state
        self.assertEqual(state.progress.wave, 5)
        self.assertEqual(state.wave_manager.wave, 5)
        self.assertEqual(state.wave_manager.remaining, 6)
        seen_enemies, seen_medium_meteors = set(), set()
        boss = None

        # Обычные враги и метеориты уходят через настоящие update.
        # Ограничение кадров превращает зависшее расписание в явную ошибку.
        for _ in range(2000):
            self.game.update(.05)
            self.assertIs(self.game.state, state)
            seen_enemies.update(state.enemies)
            seen_medium_meteors.update(m for m in state.meteors if m.size == "medium")
            boss = next((enemy for enemy in state.enemies if isinstance(enemy, Boss)), boss)
            if (state.wave_manager.remaining == 0 and boss is not None
                    and len(state.enemies) == 1 and len(state.meteors) == 0):
                break
        else:
            self.fail("За 100 секунд эскорт/метеориты не покинули конечную волну")

        self.assertEqual(len(seen_enemies), 5)
        self.assertEqual(sum(isinstance(enemy, Boss) for enemy in seen_enemies), 1)
        self.assertEqual({enemy.kind for enemy in seen_enemies}, {"boss", "scout", "gunner"})
        self.assertEqual(len(seen_medium_meteors), 1)
        self.assertEqual(state.wave_manager.remaining, 0)
        self.assertFalse(state.wave_manager.finished(state.enemies, state.meteors))
        self.assertEqual(boss.phase, 1)
        self.assertEqual(state.progress.health, state.progress.max_health)

        # Штатные 11 единиц урона за лазерный выстрел, без установки hp.
        phase_one_hits = 0
        while boss.phase == 1 and phase_one_hits < 100:
            self._hit_with_real_laser(boss)
            phase_one_hits += 1
        self.assertEqual(boss.phase, 2)
        self.assertGreater(boss.hp, 0)
        self.assertGreater(phase_one_hits, 1)

        score_before, credits_before = state.progress.score, state.progress.credits
        phase_two_hits = 0
        while boss.alive() and phase_two_hits < 100:
            self._hit_with_real_laser(boss)
            phase_two_hits += 1
        self.assertFalse(boss.alive())
        self.assertEqual(boss.hp, 0)
        self.assertEqual(state.progress.score, score_before + boss.score_value)
        self.assertEqual(state.progress.credits, credits_before + boss.credit_value)
        self.assertTrue(state.wave_manager.finished(state.enemies, state.meteors))

        # Повторная обработка и новый снаряд в бывшем месте босса не дают
        # второй награды: уничтоженный спрайт уже исключён из группы целей.
        duplicate = Laser(boss.position, (0, -850), 11)
        state.player_projectiles.add(duplicate)
        for _ in range(3):
            state.resolve_collisions()
        self.assertEqual(state.progress.score, score_before + boss.score_value)
        self.assertEqual(state.progress.credits, credits_before + boss.credit_value)

        for _ in range(30):
            self.game.update(.05)
            if isinstance(self.game.state, UpgradeShop):
                break
        self.assertIsInstance(self.game.state, UpgradeShop)
        self.assertEqual(state.progress.score, score_before + boss.score_value + 500)
        self.assertEqual(state.progress.credits, credits_before + boss.credit_value + 75)
        self.assertEqual(len(state.enemy_projectiles), 0)
        self.assertEqual(len(state.player_projectiles), 0)
        score, credits = state.progress.score, state.progress.credits
        for _ in range(30):
            self.game.update(.05)
        self.assertEqual((state.progress.score, state.progress.credits), (score, credits))

        # Тот же ввод Enter, что работает в магазине у игрока.
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertIs(self.game.state, state)
        self.assertEqual(state.progress.wave, 6)
        self.assertEqual(state.wave_manager.wave, 6)
        self.assertGreater(state.wave_manager.remaining, 0)
        self.assertEqual((state.progress.score, state.progress.credits), (score, credits))
        for _ in range(32):
            self.game.update(.05)
        self.assertTrue(state.enemies)
        self.assertTrue(all(not isinstance(enemy, Boss) for enemy in state.enemies))
        self.assertIs(self.game.state, state)


if __name__ == "__main__":
    unittest.main()
