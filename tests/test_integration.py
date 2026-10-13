"""Проверки настоящего приложения: события, столкновения и переходы.

SDL dummy заменяет окно/звуковую карту, а не игровые алгоритмы.
Запуски CLI используют другую рабочую папку и отдельные сохранения.
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import pygame
from game import Game
from states.menus import MainMenu, PauseMenu, UpgradeShop, GameOver, Settings, Leaderboard
from entities.ships import Enemy
from entities.projectiles import Laser, Rocket, Plasma
from systems.persistence import SettingsStore

ROOT = Path(__file__).resolve().parents[1]


class AppIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.game = Game(data_dir=self.folder.name)

    def tearDown(self):
        self.game.close()
        self.folder.cleanup()

    def click(self, logical_position):
        viewport = self.game.viewport
        point = (viewport.x + logical_position[0] * viewport.width / 1280,
                 viewport.y + logical_position[1] * viewport.height / 720)
        for event_type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self.game.handle_event(pygame.event.Event(event_type, pos=point, button=1))

    def test_scaled_mouse_click_letterbox_and_fullscreen(self):
        self.game.display = pygame.display.set_mode((1000, 700), pygame.RESIZABLE)
        self.game.resize_viewport((1000, 700))
        self.assertGreater(self.game.viewport.y, 0)
        self.assertEqual(self.game.window_to_logical((10, 5)), (-100, -100))
        self.click(self.game.state.buttons[0].rect.center)
        self.assertIs(self.game.state, self.game.gameplay)
        self.game.change_state(MainMenu(self.game))
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F11))
        self.assertTrue(self.game.fullscreen)
        self.assertTrue(SettingsStore(Path(self.folder.name) / "settings.json").load()["fullscreen"])
        self.click(self.game.state.buttons[0].rect.center)
        self.assertIs(self.game.state, self.game.gameplay)
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F11))
        self.assertFalse(self.game.fullscreen)

    def test_movement_shooting_and_real_mask_collision(self):
        self.game.new_run()
        state = self.game.gameplay
        before = state.player.position.copy()
        state.simulate(.02, pygame.Vector2(1, -1), True)
        self.assertAlmostEqual(state.player.position.distance_to(before), state.progress.speed * .02, places=5)
        self.assertEqual(len(state.player_projectiles), 1)
        shot = next(iter(state.player_projectiles))
        self.assertLess(shot.position.y, state.player.position.y)
        state.player_projectiles.empty()
        enemy = Enemy("scout", (640, 350))
        state.enemies.add(enemy)
        shot = Laser(enemy.position, (0, -850), 100)
        state.player_projectiles.add(shot)
        self.assertIsNotNone(pygame.sprite.collide_mask(shot, enemy))
        state.resolve_collisions()
        self.assertFalse(enemy.alive())
        self.assertFalse(shot.alive())
        self.assertEqual(state.progress.score, enemy.score_value)
        self.assertEqual(state.progress.credits, enemy.credit_value)

    def test_player_hit_invulnerability_blocks_repeated_bullets(self):
        self.game.new_run()
        state = self.game.gameplay
        state.enemy_projectiles.add(Laser(state.player.position, (0, 200), 17, "enemy"))
        state.resolve_collisions()
        self.assertEqual(state.progress.health, 83)
        state.enemy_projectiles.add(Laser(state.player.position, (0, 200), 17, "enemy"))
        state.resolve_collisions()
        self.assertEqual(state.progress.health, 83)
        state.player.update(.9)
        state.enemy_projectiles.add(Laser(state.player.position, (0, 200), 17, "enemy"))
        state.resolve_collisions()
        self.assertEqual(state.progress.health, 66)

    def test_rocket_blast_limited_and_applied_once(self):
        self.game.new_run()
        state = self.game.gameplay
        targets = [Enemy("heavy", position) for position in ((500, 340), (560, 340), (750, 340))]
        state.enemies.add(*targets)
        hp = [t.hp for t in targets]
        rocket = Rocket((500, 340), (0, -490), 42)
        state.player_projectiles.add(rocket)
        state.resolve_collisions()
        self.assertFalse(rocket.alive())
        self.assertAlmostEqual(targets[0].hp, hp[0] - 42)
        self.assertLess(targets[1].hp, hp[1])
        self.assertEqual(targets[2].hp, hp[2])
        after = [t.hp for t in targets]
        state.resolve_collisions()
        self.assertEqual([t.hp for t in targets], after)

    def test_plasma_hits_three_distinct_targets_only(self):
        self.game.new_run()
        state = self.game.gameplay
        targets = [Enemy("heavy", (500, 340)) for _ in range(2)]
        state.enemies.add(*targets)
        plasma = Plasma((500, 340), (0, -430), 23)
        state.player_projectiles.add(plasma)
        state.resolve_collisions()
        self.assertEqual(plasma.remaining_pierces, 1)
        hp = [t.hp for t in targets]
        state.resolve_collisions()
        self.assertEqual([t.hp for t in targets], hp)
        third = Enemy("heavy", (500, 340))
        initial = third.hp
        state.enemies.add(third)
        state.resolve_collisions()
        self.assertEqual(third.hp, initial - 23)
        self.assertFalse(plasma.alive())

    def test_focus_pause_freezes_all_gameplay_timers_and_resume(self):
        self.game.new_run()
        state = self.game.gameplay
        state.simulate(.02, shooting=True)
        state.mouse_fire = True
        snapshots = (state.elapsed, state.wave_manager.elapsed, state.player.cooldown,
                     [(p.position.copy(), p.age) for p in state.particles.particles])
        self.game.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        pause = self.game.state
        self.assertIsInstance(pause, PauseMenu)
        self.assertFalse(state.mouse_fire)
        for _ in range(30):
            self.game.update(.05)
        self.game.change_state(Settings(self.game, pause))
        for _ in range(30):
            self.game.update(.05)
        self.assertEqual((state.elapsed, state.wave_manager.elapsed, state.player.cooldown,
                          [(p.position.copy(), p.age) for p in state.particles.particles]), snapshots)
        self.game.state.back()
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertIs(self.game.state, state)
        self.game.update(.05)
        self.assertGreater(state.elapsed, snapshots[0])

    def test_delta_time_is_capped(self):
        self.game.new_run()
        state = self.game.gameplay
        self.game.update(12.0)
        self.assertEqual(state.elapsed, .05)
        self.assertEqual(state.wave_manager.elapsed, .05)

    def test_complete_scheduled_wave_shop_and_persistent_upgrades(self):
        self.game.new_run()
        state = self.game.gameplay
        # Удаляем активные объекты, но оставляем настоящее расписание:
        # пустое поле не должно разрешать магазин до последнего спавна.
        for _ in range(500):
            state.enemies.empty()
            state.meteors.empty()
            self.game.update(.05)
            if self.game.state is not state:
                break
        self.assertIsInstance(self.game.state, UpgradeShop)
        self.assertEqual(state.wave_manager.remaining, 0)
        self.assertEqual(state.progress.score, 100)
        self.assertEqual(state.progress.credits, 55)
        shop = self.game.state
        state.progress.credits = 1000
        state.progress.health = 62
        state.progress.weapons.add("rocket")
        state.progress.weapon = "rocket"
        shop._rebuild()
        speed = state.progress.speed
        self.click(shop.buttons[0].rect.center)
        self.assertEqual(state.progress.speed, speed + 32)
        self.assertEqual(state.progress.credits, 935)
        self.assertEqual(state.progress.score, 100)
        self.game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(190, 340), button=1))
        self.assertEqual(state.progress.credits, 935)
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertIsInstance(self.game.state, PauseMenu)
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertIs(self.game.state, shop)
        self.click(shop.buttons[-1].rect.center)
        self.assertIs(self.game.state, state)
        self.assertEqual(state.progress.wave, 2)
        self.assertEqual(state.progress.health, 62)
        self.assertEqual(state.progress.weapon, "rocket")
        self.assertEqual(state.progress.credits, 935)

    def test_settings_widgets_apply_and_persist(self):
        menu = self.game.state
        state = Settings(self.game, menu)
        self.game.change_state(state)
        self.click((state.sliders[0].rect.left + state.sliders[0].rect.width / 4,
                    state.sliders[0].rect.centery))
        self.assertAlmostEqual(self.game.preferences["music_volume"], .25)
        self.assertAlmostEqual(pygame.mixer.music.get_volume(), .25, delta=.01)
        self.click(state.buttons[0].rect.center)
        self.assertFalse(self.game.preferences["camera_shake"])
        self.click(state.buttons[1].rect.center)
        self.assertEqual(self.game.preferences["particles"], 0)
        self.click(state.buttons[-1].rect.center)
        saved = self.game.settings_store.load()
        self.assertEqual(saved, self.game.preferences)
        self.assertIs(self.game.state, menu)
        self.game.new_run()
        self.game.gameplay.simulate(.02, shooting=True)
        self.assertEqual(self.game.gameplay.particles.particles, [])

    def test_game_over_cyrillic_save_once_and_new_run(self):
        self.game.new_run()
        old = self.game.gameplay
        old.progress.score = 1234
        old.progress.health = 0
        self.game.update(.02)
        self.assertIsInstance(self.game.state, GameOver)
        screen = self.game.state
        self.game.handle_event(pygame.event.Event(pygame.TEXTINPUT, text="Анна"))
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE))
        self.game.handle_event(pygame.event.Event(pygame.TEXTINPUT, text="а"))
        self.click(screen.buttons[0].rect.center)
        screen.save_result()
        rows = self.game.leaderboard.top_scores()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Анна")
        self.assertEqual(rows[0]["score"], 1234)
        self.click(screen.buttons[1].rect.center)
        self.assertIs(self.game.state, self.game.gameplay)
        self.assertNotEqual(self.game.gameplay.progress.run_id, old.progress.run_id)
        self.assertEqual(self.game.gameplay.progress.health, 100)
        self.assertEqual(self.game.gameplay.progress.score, 0)
        self.assertEqual(self.game.gameplay.progress.weapons, {"laser"})
        self.assertEqual(len(self.game.leaderboard.top_scores()), 1)

    def test_all_screens_draw_and_leaderboard_empty_then_filled(self):
        leaderboard = Leaderboard(self.game)
        self.assertEqual(leaderboard.rows, [])
        self.game.new_run()
        playing = self.game.gameplay
        playing.simulate(.05, shooting=True)
        self.game.leaderboard.save_score("test", "Пилот", 200, 2)
        filled = Leaderboard(self.game)
        self.assertEqual(len(filled.rows), 1)
        states = [MainMenu(self.game), playing, PauseMenu(self.game, playing),
                  UpgradeShop(self.game, playing), GameOver(self.game, playing),
                  leaderboard, filled, Settings(self.game)]
        for state in states:
            with self.subTest(state=type(state).__name__):
                state.elapsed = .5
                state.draw(self.game.screen)
                self.assertNotEqual(self.game.screen.get_at((640, 360)), (0, 0, 0, 255))


class StartupTests(unittest.TestCase):
    def test_entry_point_from_other_directory_without_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            env = os.environ.copy()
            env.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="unavailable",
                       STAR_FRONTIER_DATA_DIR=folder)
            screenshot = Path(folder) / "frame.png"
            result = subprocess.run([sys.executable, str(ROOT / "main.py"), "--headless",
                                     "--frames", "4", "--screenshot", str(screenshot)],
                                    cwd=folder, env=env, text=True, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(screenshot.is_file())
            self.assertTrue((Path(folder) / "leaderboard.sqlite3").is_file())
            self.assertTrue((Path(folder) / "settings.json").is_file())

    def test_audio_unavailable_still_supports_combat(self):
        with tempfile.TemporaryDirectory() as folder:
            env = os.environ.copy()
            env.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="unavailable",
                       STAR_FRONTIER_DATA_DIR=folder, PYTHONPATH=str(ROOT))
            code = "from game import Game; g=Game(); assert not g.audio.enabled; g.new_run(); g.gameplay.simulate(.03,shooting=True); g.draw(); assert len(g.gameplay.player_projectiles)==1; g.close()"
            result = subprocess.run([sys.executable, "-c", code], cwd=folder, env=env,
                                    text=True, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
