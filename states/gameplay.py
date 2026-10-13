"""Боевой экран объединяет независимые системы, но не содержит меню.

Взрыв ракеты обрабатывается здесь: общий список целей исключает повторный
урон. Плазма хранит уже задетые объекты, а столкновения проверяют маски.
"""
import math
import random
import pygame
from settings import WIDTH, HEIGHT, CYAN, ORANGE, RED, GREEN, TEXT, MUTED, PANEL
from states.base import State
from systems.progression import RunProgress
from systems.waves import WaveManager
from systems.particles import ParticleSystem
from entities.ships import Player, Boss
from entities.projectiles import Rocket, Plasma
from entities.meteors import Meteor
from entities.pickups import Bonus


WEAPON_NAMES = {"laser": "ЛАЗЕР", "rocket": "РАКЕТЫ", "plasma": "ПЛАЗМА"}
WEAPON_COLORS = {"laser": CYAN, "rocket": ORANGE, "plasma": (186, 125, 255)}


class Gameplay(State):
    def __init__(self, game):
        super().__init__(game)
        self.progress = RunProgress()
        self.player = Player(self.progress)
        self.enemies = pygame.sprite.Group()
        self.meteors = pygame.sprite.Group()
        self.player_projectiles = pygame.sprite.Group()
        self.enemy_projectiles = pygame.sprite.Group()
        self.pickups = pygame.sprite.Group()
        self.wave_manager = WaveManager(1)
        self.particles = ParticleSystem(game.preferences["particles"])
        self.elapsed = 0.0
        self.wave_banner = 3.0
        self.clear_timer = 0.0
        self.mouse_fire = False
        self.shake = 0.0
        self.engine_timer = 0.0
        self.rng = random.Random()
        self.world = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.flash = 0.0

    def handle_event(self, event):
        from states.menus import PauseMenu
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.mouse_fire = False
                self.game.change_state(PauseMenu(self.game, self))
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self.player.select_weapon(event.key - pygame.K_0)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.mouse_fire = True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.mouse_fire = False

    def update(self, dt):
        keys = pygame.key.get_pressed()
        direction = pygame.Vector2(
            int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(keys[pygame.K_a] or keys[pygame.K_LEFT]),
            int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(keys[pygame.K_w] or keys[pygame.K_UP]),
        )
        self.simulate(dt, direction, bool(keys[pygame.K_SPACE] or self.mouse_fire))

    def simulate(self, dt, direction=pygame.Vector2(), shooting=False):
        """Явный ввод позволяет проверять бой без физической клавиатуры."""
        if dt <= 0:
            return
        self.elapsed += dt
        self.wave_banner = max(0.0, self.wave_banner - dt)
        self.shake = max(0.0, self.shake - dt * 18)
        self.flash = max(0.0, self.flash - dt * 3)
        self.particles.amount = self.game.preferences["particles"]
        self.player.update(dt, direction)
        self.wave_manager.update(dt, self.enemies, self.meteors, self.player.position)
        self.engine_timer -= dt
        if self.engine_timer <= 0:
            self.engine_timer = .035
            self.particles.emit(self.player.position + pygame.Vector2(0, 32), CYAN,
                                count=2, speed=35, lifetime=.25)
        if shooting:
            shots = self.player.try_shoot()
            if shots:
                self.player_projectiles.add(*shots)
                self.game.audio.play(self.progress.weapon)
                self.particles.emit(self.player.position + pygame.Vector2(0, -35),
                                    WEAPON_COLORS[self.progress.weapon], count=6, speed=70, lifetime=.13)
        self.player_projectiles.update(dt)
        for enemy in list(self.enemies):
            enemy.update(dt, self.player.position, self.player_projectiles)
            if enemy.escaped:
                enemy.kill()
                continue
            shots = enemy.try_shoot()
            if shots:
                self.enemy_projectiles.add(*shots)
                self.particles.emit(enemy.position + pygame.Vector2(0, 25), ORANGE,
                                    count=4, speed=40, lifetime=.13)
        self.meteors.update(dt)
        for meteor in list(self.meteors):
            if meteor.escaped:
                meteor.kill()
        self.enemy_projectiles.update(dt)
        self.pickups.update(dt)
        self.resolve_collisions()
        self.particles.update(dt)
        if self.progress.health <= 0:
            from states.menus import GameOver
            self.mouse_fire = False
            self.game.change_state(GameOver(self.game, self))
            return
        if self.wave_manager.finished(self.enemies, self.meteors):
            self.clear_timer += dt
            if self.clear_timer >= 1.0:
                self.progress.award(100 * self.progress.wave, 50 + 5 * self.progress.wave)
                # Осколки учтены в завершении волны; оставшиеся пули не идут в магазин.
                self.enemy_projectiles.empty()
                self.player_projectiles.empty()
                self.mouse_fire = False
                from states.menus import UpgradeShop
                self.game.change_state(UpgradeShop(self.game, self))
        else:
            self.clear_timer = 0.0

    def next_wave(self):
        self.progress.wave += 1
        self.wave_manager = WaveManager(self.progress.wave)
        self.clear_timer = 0.0
        self.wave_banner = 3.0
        self.pickups.empty()
        self.player_projectiles.empty()
        self.enemy_projectiles.empty()
        self.mouse_fire = False
        self.player.invulnerability = max(self.player.invulnerability, 1.0)

    def _destroy(self, target, award=True):
        if not target.alive():
            return
        if award:
            self.progress.award(target.score_value, target.credit_value)
        position = target.position.copy()
        color = (171, 159, 138) if isinstance(target, Meteor) else ORANGE
        self.particles.emit(position, color, count=32 if isinstance(target, Boss) else 18,
                            speed=180, lifetime=.7)
        self.game.audio.play("explosion")
        self.shake = max(self.shake, 12 if isinstance(target, Boss) else 4)
        if isinstance(target, Meteor):
            self.meteors.add(*target.split())
        elif award and self.rng.random() < .16:
            kind = "health" if self.progress.health < self.progress.max_health * .65 else "credits"
            self.pickups.add(Bonus(kind, position))
        target.kill()

    def _damage_target(self, target, damage):
        if not target.alive():
            return
        dead = target.take_damage(damage)
        self.particles.emit(target.position, CYAN, count=5, speed=85, lifetime=.22)
        if dead:
            self._destroy(target)
        else:
            self.game.audio.play("hit")

    def explode_rocket(self, projectile, primary):
        center = projectile.position
        radius = projectile.explosion_radius
        self.particles.emit(center, ORANGE, count=30, speed=220, lifetime=.55)
        self.shake = max(self.shake, 5)
        # snapshot нужен: взрыв может породить новые осколки, которые не
        # должны мгновенно пострадать от того же уже завершённого события.
        for target in list(self.enemies) + list(self.meteors):
            distance = center.distance_to(target.position)
            if target is primary or distance <= radius:
                factor = 1.0 if target is primary else .5 + .5 * (1 - distance / radius)
                self._damage_target(target, projectile.damage * factor)
        projectile.kill()

    def _hurt_player(self, damage):
        before = self.progress.health + self.progress.shield
        self.player.take_damage(damage)
        if self.progress.health + self.progress.shield < before:
            self.flash = .35
            self.shake = max(self.shake, 5)
            self.game.audio.play("hit")
            self.particles.emit(self.player.position, RED, count=12, speed=140, lifetime=.4)

    def resolve_collisions(self):
        targets = list(self.enemies) + list(self.meteors)
        for projectile in list(self.player_projectiles):
            for target in targets:
                if (not projectile.alive() or not target.alive()
                        or target in projectile.hit_targets):
                    continue
                if not pygame.sprite.collide_mask(projectile, target):
                    continue
                if isinstance(projectile, Rocket):
                    self.explode_rocket(projectile, target)
                    break
                self._damage_target(target, projectile.damage)
                projectile.hit_targets.add(target)
                projectile.remaining_pierces -= 1
                if projectile.remaining_pierces <= 0:
                    projectile.kill()
                    break
        for projectile in pygame.sprite.spritecollide(
                self.player, self.enemy_projectiles, True, pygame.sprite.collide_mask):
            self._hurt_player(projectile.damage)
        for target in pygame.sprite.spritecollide(
                self.player, self.enemies, False, pygame.sprite.collide_mask):
            self._hurt_player(45 if isinstance(target, Boss) else 24)
            if not isinstance(target, Boss):
                self._destroy(target, award=False)
        for meteor in pygame.sprite.spritecollide(
                self.player, self.meteors, False, pygame.sprite.collide_mask):
            self._hurt_player({"large": 32, "medium": 20, "small": 12}[meteor.size])
            self._destroy(meteor, award=False)
        for bonus in pygame.sprite.spritecollide(
                self.player, self.pickups, True, pygame.sprite.collide_mask):
            if bonus.kind == "health":
                self.progress.health = min(self.progress.max_health, self.progress.health + bonus.value)
            elif bonus.kind == "shield":
                self.progress.shield = min(self.progress.max_shield, self.progress.shield + bonus.value)
            else:
                self.progress.credits += bonus.value
            self.game.audio.play("purchase")
            self.particles.emit(self.player.position, GREEN, count=12)

    def _text(self, surface, text, position, size=20, color=TEXT, bold=False):
        image = self.game.assets.font(size, bold).render(str(text), True, color)
        surface.blit(image, position)
        return image.get_width()

    def _bar(self, surface, rect, value, maximum, color):
        pygame.draw.rect(surface, (33, 46, 64), rect, border_radius=4)
        if maximum > 0 and value > 0:
            fill = rect.copy()
            fill.width = max(1, round(rect.width * min(1, value / maximum)))
            pygame.draw.rect(surface, color, fill, border_radius=4)

    def draw(self, surface):
        self.game.background.draw(surface)
        self.world.fill((0, 0, 0, 0))
        self.wave_manager.draw_warnings(self.world)
        for enemy in self.enemies:
            if hasattr(enemy, "draw"):
                enemy.draw(self.world)
        self.meteors.draw(self.world)
        self.enemies.draw(self.world)
        self.pickups.draw(self.world)
        self.player_projectiles.draw(self.world)
        self.enemy_projectiles.draw(self.world)
        self.particles.draw(self.world)
        if self.player.invulnerability <= 0 or int(self.elapsed * 18) % 2 == 0:
            self.world.blit(self.player.image, self.player.rect)
        if self.progress.shield > 0:
            pygame.draw.circle(self.world, (65, 147, 195, 120), self.player.rect.center, 43, 1)
        shake = self.shake if self.game.preferences["camera_shake"] else 0
        offset = (round(math.sin(self.elapsed * 83) * shake), round(math.cos(self.elapsed * 71) * shake * .5))
        surface.blit(self.world, offset)
        pygame.draw.rect(surface, (16, 31, 48), (24, 92, 1232, 600), 1, border_radius=8)
        if self.flash > 0:
            pygame.draw.rect(surface, RED, (25, 93, 1230, 598), max(1, int(self.flash * 10)), border_radius=8)
        self.draw_hud(surface)
        if self.wave_banner > 0:
            subtitle = {1: "Разведчики • удерживайте Space для огня",
                        2: "Стрелки • следите за оранжевым прицелом",
                        3: "Перехватчики • меняйте направление атаки",
                        4: "Тяжёлые корабли • ищите промежутки в веере"}.get(
                self.progress.wave, "Босс • предупреждения оставляют время для манёвра"
                if self.progress.wave % 5 == 0 else "Глубокий космос • сложность растёт")
            banner = pygame.Surface((720, 100), pygame.SRCALPHA)
            pygame.draw.rect(banner, (12, 22, 38, 200), banner.get_rect(), border_radius=12)
            self._text(banner, f"ВОЛНА {self.progress.wave:02}", (24, 10), 30, CYAN, True)
            self._text(banner, subtitle, (24, 56), 19, MUTED)
            banner.set_alpha(min(255, int(self.wave_banner * 220)))
            surface.blit(banner, (280, 170))
        if self.clear_timer > 0:
            self._text(surface, "СЕКТОР ОЧИЩЕН", (493, 330), 28, GREEN, True)

    def draw_hud(self, surface):
        p = self.progress
        pygame.draw.rect(surface, PANEL, (0, 0, WIDTH, 82))
        pygame.draw.line(surface, (37, 72, 91), (0, 82), (WIDTH, 82))
        self._text(surface, "КОРПУС", (26, 10), 14, MUTED, True)
        self._text(surface, f"{p.health:.0f} / {p.max_health:.0f}", (147, 10), 15)
        self._bar(surface, pygame.Rect(26, 34, 222, 10), p.health, p.max_health, GREEN if p.health > 30 else RED)
        self._text(surface, "ЩИТ", (26, 52), 14, MUTED)
        self._text(surface, f"{p.shield:.0f} / {p.max_shield:.0f}" if p.max_shield else "не установлен", (83, 52), 15, CYAN)
        self._text(surface, "ОЧКИ", (299, 10), 14, MUTED, True)
        self._text(surface, f"{p.score:06}", (299, 33), 29, TEXT, True)
        self._text(surface, "КРЕДИТЫ", (474, 10), 14, MUTED, True)
        self._text(surface, str(p.credits), (474, 33), 29, ORANGE, True)
        self._text(surface, "ВОЛНА", (644, 10), 14, MUTED, True)
        self._text(surface, f"{p.wave:02}", (644, 33), 29, CYAN, True)
        self._text(surface, "1 / 2 / 3  •  " + WEAPON_NAMES[p.weapon], (776, 10), 16, WEAPON_COLORS[p.weapon], True)
        cooldown = max(0, self.player.cooldown)
        interval = max(.01, self.player.fire_interval)
        self._bar(surface, pygame.Rect(776, 41, 235, 7), interval - cooldown, interval, WEAPON_COLORS[p.weapon])
        self._text(surface, "ГОТОВО" if cooldown <= 0 else f"зарядка {cooldown:.1f} с", (776, 55), 14, MUTED)
        self._text(surface, "ESC  ПАУЗА", (1088, 17), 15, MUTED)
        self._text(surface, "F11  ЭКРАН", (1088, 47), 15, MUTED)
        boss = next((e for e in self.enemies if isinstance(e, Boss)), None)
        if boss:
            self._bar(surface, pygame.Rect(380, 102, 520, 12), boss.hp, boss.max_hp, RED)
            self._text(surface, f"СТРАЖ РУБЕЖА  •  ФАЗА {boss.phase}", (485, 121), 15, RED, True)
