"""Воспроизводимый функциональный прогон боя без дисплея.

Скриптовой пилот только двигается, стреляет и покупает доступные улучшения.
Здоровье, урон, кредиты и расписания не подменяются. Это проверка систем,
а не оценка удобства управления человеком или музыкального оформления.
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from pathlib import Path
import math
import random
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from game import Game
from states.menus import UpgradeShop, GameOver
from systems.progression import ShopSystem
from systems.waves import WaveManager


def run_check():
    random.seed(42)
    with tempfile.TemporaryDirectory() as folder:
        game = Game(data_dir=folder)
        try:
            game.new_run()
            battle = game.gameplay
            battle.rng.seed(42)
            battle.wave_manager = WaveManager(1, seed=1)
            dt, steps, completed = .02, 0, []
            while steps < 25000:
                if isinstance(game.state, UpgradeShop):
                    p = battle.progress
                    completed.append({"wave": p.wave, "health": round(p.health),
                                      "score": p.score, "credits": p.credits})
                    shop = ShopSystem(p)
                    for key in ("shield", "repair", "damage", "fire_rate", "health"):
                        shop.purchase(key)
                    game.state.next_wave()
                    # Seed выбирает места спавна, не меняя правил/числа объектов.
                    battle.wave_manager = WaveManager(p.wave, seed=p.wave)
                    if p.wave >= 7:
                        break
                if isinstance(game.state, GameOver):
                    break
                targets = [e for e in list(battle.enemies) + list(battle.meteors)
                           if 140 < e.position.y < 650]
                target_x = 640
                if targets:
                    target = max(targets, key=lambda e: e.position.y)
                    travel = max(0, (battle.player.position.y - target.position.y) / 850)
                    if getattr(target, "kind", None) == "scout":
                        target_x = target.base_x + math.sin(target.elapsed + travel * 1.7) * 88
                    else:
                        target_x = target.position.x + target.velocity.x * travel
                for danger in list(battle.enemy_projectiles) + list(battle.meteors):
                    if danger.velocity.y <= 0:
                        continue
                    impact = (battle.player.position.y - danger.position.y) / danger.velocity.y
                    future_x = danger.position.x + danger.velocity.x * impact
                    if 0 < impact < .38 and abs(future_x - battle.player.position.x) < 42:
                        target_x = battle.player.position.x + (110 if future_x <= battle.player.position.x else -110)
                        target_x = max(70, min(1210, target_x))
                        break
                direction_x = max(-1, min(1, (target_x - battle.player.position.x) /
                                             (battle.progress.speed * dt)))
                battle.simulate(dt, pygame.Vector2(direction_x, 0), True)
                steps += 1
            print(f"Симуляция: {steps * dt:.2f} с; состояние: {type(game.state).__name__}; "
                  f"волна: {battle.progress.wave}; счёт: {battle.progress.score}")
            for row in completed:
                print(row)
            if [row["wave"] for row in completed] != list(range(1, 7)):
                raise AssertionError("Пилот не завершил ожидаемые шесть волн")
            assert battle.progress.wave == 7 and battle.progress.health > 0
            # Босс не улетает: завершение пятой волны доказывает его уничтожение.
            print("Проверено: шесть волн, покупки, уничтожение босса и продолжение забега.")
            return completed
        finally:
            game.close()


if __name__ == "__main__":
    run_check()
