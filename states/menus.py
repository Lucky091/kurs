"""Экраны приложения. Каждый экран сам отвечает за свои кнопки и переходы."""

from __future__ import annotations

import math
import sqlite3
import pygame

from states.base import State
from systems.progression import ShopSystem
from ui.widgets import Button, Slider, COLORS, bar, label, panel


def _button(game, rect, text, callback, enabled=True, primary=False, size=21):
    return Button(rect, text, callback, enabled, assets=game.assets, primary=primary,
                  font_size=size, sound=game.audio.play)


def _dispatch(buttons, event):
    # Копия списка нужна: обработчик покупки может обновить все кнопки магазина.
    for button in list(buttons):
        if button.handle_event(event):
            break


def _draw_buttons(game, surface, buttons):
    for button in buttons:
        button.draw(surface, game.mouse_position)


def _dim(surface, alpha=190):
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    overlay.fill((5, 10, 22, alpha))
    surface.blit(overlay, (0, 0))


def _fade(surface, elapsed):
    if elapsed < .25:
        _dim(surface, round(100 * (1 - elapsed / .25)))


def _wrapped(surface, text, pos, assets, width, size=17, color=None, line_height=24):
    font = assets.font(size)
    lines, line = [], ""
    for word in str(text).split():
        candidate = (line + " " + word).strip()
        if line and font.size(candidate)[0] > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    for index, item in enumerate(lines):
        label(surface, item, (pos[0], pos[1] + index * line_height), assets,
              size, color or COLORS["muted"])
    return len(lines) * line_height


class MainMenu(State):
    def __init__(self, game):
        super().__init__(game)
        self.hero = pygame.transform.smoothscale(game.assets.image("ship_player"), (210, 246))
        self.buttons = [
            _button(game, (94, 340, 330, 60), "НОВЫЙ ВЫЛЕТ", game.new_run, primary=True),
            _button(game, (94, 414, 330, 54), "Таблица рекордов", lambda: game.change_state(Leaderboard(game))),
            _button(game, (94, 482, 330, 54), "Настройки", lambda: game.change_state(Settings(game, self))),
            _button(game, (94, 550, 330, 54), "Выход", game.quit),
        ]

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.game.new_run()
            return
        _dispatch(self.buttons, event)

    def draw(self, surface):
        g = self.game
        g.background.draw(surface)
        # Простая орбитальная композиция подчёркивает силуэт собственного корабля.
        orbit = pygame.Surface((620, 620), pygame.SRCALPHA)
        pygame.draw.circle(orbit, (34, 99, 127, 35), (310, 310), 276, 1)
        pygame.draw.circle(orbit, (38, 116, 142, 40), (310, 310), 216, 1)
        pygame.draw.circle(orbit, (27, 95, 124, 20), (310, 310), 152)
        surface.blit(orbit, (580, 20))
        label(surface, "ОДИН КОРАБЛЬ. БЕСКОНЕЧНЫЙ КОСМОС.", (98, 88), g.assets,
              15, COLORS["cyan"], bold=True)
        label(surface, "ЗВЁЗДНЫЙ", (90, 119), g.assets, 62, bold=True)
        label(surface, "РУБЕЖ", (92, 188), g.assets, 78, COLORS["cyan"], bold=True)
        label(surface, "Выдержи волну. Улучши корабль. Иди дальше.", (97, 288), g.assets,
              18, COLORS["muted"])
        bob = math.sin(self.elapsed * 1.6) * 9
        glow = pygame.Surface((180, 220), pygame.SRCALPHA)
        for i in range(10, 0, -1):
            pygame.draw.ellipse(glow, (32, 181, 214, 3 + i), (90 - i * 6, 20, i * 12, 190))
        surface.blit(glow, (827, 323 + bob))
        surface.blit(self.hero, (815, 217 + bob))
        label(surface, "SF–01 / ПЕРЕХВАТЧИК", (918, 499), g.assets, 16,
              COLORS["cyan"], align="center")
        label(surface, "Каждая пятая волна — бой с боссом", (918, 533), g.assets,
              17, COLORS["muted"], align="center")
        _draw_buttons(g, surface, self.buttons)
        panel(surface, (94, 637, 1092, 47), (11, 22, 38))
        label(surface, "WASD / стрелки — движение     SPACE / ЛКМ — огонь     1–3 — оружие     ESC — пауза     F11 — экран",
              (113, 651), g.assets, 15, COLORS["muted"])
        _fade(surface, self.elapsed)


class PauseMenu(State):
    def __init__(self, game, gameplay, return_state=None):
        super().__init__(game)
        self.gameplay = gameplay
        self.return_state = return_state or gameplay
        # Отпускание мыши в меню не попадёт в Gameplay: сбрасываем удержание здесь.
        self.gameplay.mouse_fire = False
        self.buttons = [
            _button(game, (470, 306, 340, 60), "ПРОДОЛЖИТЬ", self.resume, primary=True),
            _button(game, (470, 382, 340, 56), "Настройки", lambda: game.change_state(Settings(game, self))),
            _button(game, (470, 454, 340, 56), "В главное меню", lambda: game.change_state(MainMenu(game))),
        ]

    def resume(self):
        self.game.change_state(self.return_state)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.resume()
            return
        _dispatch(self.buttons, event)

    def draw(self, surface):
        self.gameplay.draw(surface)
        _dim(surface)
        panel(surface, (406, 159, 468, 428), (12, 24, 41))
        label(surface, "ПАУЗА", (640, 218), self.game.assets, 45, bold=True, align="center")
        label(surface, "Симуляция и боевые таймеры остановлены", (640, 271), self.game.assets,
              16, COLORS["muted"], align="center")
        _draw_buttons(self.game, surface, self.buttons)
        label(surface, "ESC — вернуться в бой", (640, 545), self.game.assets, 16,
              COLORS["muted"], align="center")
        _fade(surface, self.elapsed)


class UpgradeShop(State):
    def __init__(self, game, gameplay):
        super().__init__(game)
        self.gameplay = gameplay
        self.progress = gameplay.progress
        self.shop = ShopSystem(self.progress)
        self.notification = ""
        self.notification_time = 0.0
        self._rebuild()

    def _rebuild(self):
        self.offers = self.shop.offers()
        self.buttons = []
        self.card_rects = []
        for index, offer in enumerate(self.offers):
            rect = pygame.Rect(52 + (index % 4) * 298, 196 + (index // 4) * 198, 282, 182)
            self.card_rects.append(rect)
            if offer["level"] >= offer["max_level"]:
                text = "Установлено" if offer["id"] in ("rocket", "plasma") else "Максимум"
            elif offer["id"] == "repair" and self.progress.health >= self.progress.max_health:
                text = "Корпус исправен"
            else:
                text = f"Купить · {offer['price']} кр."
            self.buttons.append(_button(self.game, (rect.x + 16, rect.y + 128, 250, 38), text,
                                        lambda key=offer["id"]: self.buy(key), offer["enabled"], size=17))
        self.buttons.append(_button(self.game, (916, 628, 312, 54), "СЛЕДУЮЩАЯ ВОЛНА →",
                                    self.next_wave, primary=True, size=20))

    def buy(self, key):
        if self.shop.purchase(key):
            self.game.audio.play("purchase")
            self.notification = "Улучшение установлено"
            self.notification_time = 2.0
            self._rebuild()

    def next_wave(self):
        self.gameplay.next_wave()
        self.game.change_state(self.gameplay)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.next_wave()
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.change_state(PauseMenu(self.game, self.gameplay, self))
            return
        _dispatch(self.buttons, event)

    def update(self, dt):
        super().update(dt)
        self.notification_time = max(0, self.notification_time - dt)

    def draw(self, surface):
        g, p = self.game, self.progress
        g.background.draw(surface)
        label(surface, f"ВОЛНА {p.wave} ЗАВЕРШЕНА", (54, 38), g.assets, 15, COLORS["cyan"], bold=True)
        label(surface, "Орбитальная мастерская", (50, 64), g.assets, 36, bold=True)
        label(surface, "Покупки расходуют кредиты; итоговый счёт сохраняется.", (54, 112), g.assets,
              17, COLORS["muted"])
        label(surface, f"{p.credits} КРЕДИТОВ", (1226, 55), g.assets, 29,
              COLORS["orange"], bold=True, align="right")
        label(surface, f"Счёт: {p.score}", (1226, 99), g.assets, 18, COLORS["muted"], align="right")
        label(surface, f"Корпус {p.health:.0f}/{p.max_health:.0f}", (54, 151), g.assets, 18)
        bar(surface, (253, 157, 212, 11), p.health, p.max_health, COLORS["green"])
        label(surface, f"Щит {p.shield:.0f}/{p.max_shield:.0f}", (526, 151), g.assets, 18)
        bar(surface, (677, 157, 184, 11), p.shield, p.max_shield, COLORS["cyan"])
        for offer, rect in zip(self.offers, self.card_rects):
            panel(surface, rect, border=(54, 96, 111) if offer["enabled"] else COLORS["border"])
            label(surface, offer["title"], (rect.x + 16, rect.y + 14), g.assets,
                  18, COLORS["text"], bold=True)
            _wrapped(surface, offer["detail"], (rect.x + 16, rect.y + 49), g.assets, 247,
                     size=15, line_height=21)
            if offer["id"] in p.levels:
                for level in range(offer["max_level"]):
                    color = COLORS["cyan"] if level < offer["level"] else (40, 58, 75)
                    pygame.draw.rect(surface, color, (rect.x + 17 + level * 23, rect.y + 109, 17, 4),
                                     border_radius=2)
                label(surface, f"Ур. {offer['level']}/{offer['max_level']}",
                      (rect.right - 17, rect.y + 102), g.assets, 13, COLORS["muted"], align="right")
        _draw_buttons(g, surface, self.buttons)
        if self.notification_time > 0:
            label(surface, self.notification, (54, 637), g.assets, 20, COLORS["green"])
        else:
            label(surface, "Здоровье, оружие и улучшения сохранятся.", (54, 630), g.assets, 18, COLORS["muted"])
            label(surface, "ENTER — следующий вылет  ·  ESC — пауза", (54, 658), g.assets, 15, COLORS["muted"])
        _fade(surface, self.elapsed)


class GameOver(State):
    def __init__(self, game, gameplay):
        super().__init__(game)
        self.gameplay = gameplay
        self.progress = gameplay.progress
        self.name = ""
        self.saved = False
        self.input_active = True
        self.input_rect = pygame.Rect(420, 369, 440, 57)
        self.notice = ""
        self.buttons = [
            _button(game, (420, 451, 440, 52), "Сохранить рекорд", self.save_result, primary=True),
            _button(game, (420, 521, 210, 52), "Ещё раз", self.replay, size=20),
            _button(game, (650, 521, 210, 52), "В меню", self.menu, size=20),
        ]

    def enter(self):
        if not self.saved:
            pygame.key.start_text_input()
            pygame.key.set_text_input_rect(self.input_rect)

    def save_result(self):
        if self.saved:
            return
        try:
            self.game.leaderboard.save_score(self.progress.run_id, self.name or "Пилот",
                                            self.progress.score, self.progress.wave)
        except (OSError, sqlite3.Error):
            # SQLITE_FULL/readonly — пользователь видит ошибку и может повторить запись.
            self.notice = "Не удалось записать рекорд. Проверьте папку сохранений."
            return
        self.saved = True
        self.input_active = False
        self.buttons[0].enabled = False
        self.buttons[0].text = "Рекорд сохранён"
        self.notice = "Результат добавлен в таблицу рекордов"
        pygame.key.stop_text_input()
        self.game.audio.play("purchase")

    def replay(self):
        self.save_result()
        pygame.key.stop_text_input()
        self.game.new_run()

    def menu(self):
        self.save_result()
        pygame.key.stop_text_input()
        self.game.change_state(MainMenu(self.game))

    def handle_event(self, event):
        if event.type == pygame.TEXTINPUT and self.input_active and not self.saved:
            self.name = (self.name + "".join(c for c in event.text if c.isprintable()))[:20]
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.menu()
                return
            if event.key == pygame.K_BACKSPACE and self.input_active and not self.saved:
                self.name = self.name[:-1]
            elif event.key == pygame.K_RETURN:
                self.save_result()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.input_active = self.input_rect.collidepoint(event.pos) and not self.saved
            if self.input_active:
                pygame.key.start_text_input()
            else:
                pygame.key.stop_text_input()
        _dispatch(self.buttons, event)

    def draw(self, surface):
        self.gameplay.draw(surface)
        _dim(surface, 210)
        panel(surface, (344, 112, 592, 525), (12, 24, 41))
        g, p = self.game, self.progress
        label(surface, "СВЯЗЬ С КОРАБЛЁМ ПОТЕРЯНА", (640, 156), g.assets, 14,
              COLORS["red"], bold=True, align="center")
        label(surface, "Вылет завершён", (640, 205), g.assets, 40, bold=True, align="center")
        label(surface, str(p.score), (640, 270), g.assets, 47, COLORS["cyan"], bold=True, align="center")
        label(surface, f"ОЧКОВ  ·  ДОСТИГНУТА ВОЛНА {p.wave}", (640, 314), g.assets, 15,
              COLORS["muted"], align="center")
        label(surface, "Имя пилота", (422, 343), g.assets, 16, COLORS["muted"])
        panel(surface, self.input_rect, (8, 18, 32), COLORS["cyan"] if self.input_active else COLORS["border"], 9)
        text = self.name or "Пилот"
        rendered = g.assets.font(23).render(text, True,
                    COLORS["text"] if self.name else COLORS["muted"])
        # Длинное имя прокручивается внутри поля, а не рисуется поверх рамки.
        viewport = pygame.Rect(max(0, rendered.get_width() - 403), 0, 403, rendered.get_height())
        surface.blit(rendered, (438, 383), viewport)
        if self.input_active and not self.saved and int(self.elapsed * 2) % 2 == 0:
            offset = min(403, g.assets.font(23).size(self.name)[0])
            pygame.draw.line(surface, COLORS["cyan"], (438 + offset + 3, 382), (438 + offset + 3, 409), 2)
        _draw_buttons(g, surface, self.buttons)
        if self.notice:
            _wrapped(surface, self.notice, (420, 592), g.assets, 440, 13,
                     COLORS["green"] if self.saved else COLORS["red"], line_height=18)
        else:
            label(surface, "Результат сохранится и при выходе в меню", (640, 605), g.assets,
                  14, COLORS["muted"], align="center")
        _fade(surface, self.elapsed)


class Leaderboard(State):
    def __init__(self, game):
        super().__init__(game)
        self.rows = game.leaderboard.top_scores()
        self.buttons = [_button(game, (64, 627, 240, 54), "← Главное меню", self.back, size=19)]

    def back(self):
        self.game.change_state(MainMenu(self.game))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.back()
            return
        _dispatch(self.buttons, event)

    def draw(self, surface):
        g = self.game
        g.background.draw(surface)
        label(surface, "ЛУЧШИЕ ПИЛОТЫ", (65, 48), g.assets, 15, COLORS["cyan"], bold=True)
        label(surface, "Таблица рекордов", (61, 77), g.assets, 41, bold=True)
        panel(surface, (64, 154, 1152, 443))
        for text, x in (("МЕСТО", 86), ("ПИЛОТ", 181), ("ОЧКИ", 686), ("ВОЛНА", 881), ("ДАТА", 1013)):
            label(surface, text, (x, 174), g.assets, 14, COLORS["muted"], bold=True)
        pygame.draw.line(surface, COLORS["border"], (84, 204), (1196, 204))
        if not self.rows:
            label(surface, "Здесь начинается история лучших пилотов", (640, 346), g.assets,
                  26, align="center")
            label(surface, "Завершите первый вылет, чтобы сохранить результат.", (640, 393),
                  g.assets, 19, COLORS["muted"], align="center")
        for index, row in enumerate(self.rows[:10]):
            y = 217 + index * 36
            if index % 2 == 0:
                pygame.draw.rect(surface, (18, 31, 48), (79, y - 4, 1123, 35), border_radius=5)
            color = COLORS["orange"] if index == 0 else COLORS["text"]
            label(surface, f"{index + 1:02}", (99, y), g.assets, 19, color, bold=index == 0)
            label(surface, row["name"], (181, y), g.assets, 19, color)
            label(surface, str(row["score"]), (686, y), g.assets, 19, COLORS["cyan"])
            label(surface, str(row["wave"]), (907, y), g.assets, 19)
            date = str(row["played_at"])[:10]
            label(surface, date, (1013, y + 1), g.assets, 17, COLORS["muted"])
        _draw_buttons(g, surface, self.buttons)
        label(surface, "Показаны десять лучших результатов", (1216, 646), g.assets,
              15, COLORS["muted"], align="right")
        _fade(surface, self.elapsed)


class Settings(State):
    def __init__(self, game, return_state=None):
        super().__init__(game)
        self.return_state = return_state
        self.sliders = [
            Slider((662, 215, 270, 29), game.preferences["music_volume"],
                   lambda value: self.set_volume("music_volume", value), assets=game.assets),
            Slider((662, 295, 270, 29), game.preferences["effects_volume"],
                   lambda value: self.set_volume("effects_volume", value), assets=game.assets),
        ]
        self.buttons = [
            _button(game, (662, 365, 327, 45), "", self.toggle_shake, size=19),
            _button(game, (662, 445, 327, 45), "", self.cycle_particles, size=19),
            _button(game, (662, 525, 327, 45), "", self.toggle_fullscreen, size=19),
            _button(game, (270, 622, 307, 54), "← Сохранить и вернуться", self.back, primary=True, size=18),
        ]
        self.notice = ""
        self._sync_labels()

    def _sync_labels(self):
        p = self.game.preferences
        self.buttons[0].text = "Включено" if p["camera_shake"] else "Выключено"
        quantity = p["particles"]
        self.buttons[1].text = "Полное" if quantity >= .75 else ("Умеренное" if quantity > 0 else "Без частиц")
        self.buttons[2].text = "Полный экран" if p["fullscreen"] else "Оконный режим"

    def set_volume(self, key, value):
        self.game.preferences[key] = value
        self.game.audio.apply_settings(self.game.preferences)

    def toggle_shake(self):
        self.game.preferences["camera_shake"] = not self.game.preferences["camera_shake"]
        self._sync_labels()

    def cycle_particles(self):
        current = self.game.preferences["particles"]
        self.game.preferences["particles"] = .5 if current <= 0 else (1.0 if current < .75 else 0.0)
        self._sync_labels()

    def toggle_fullscreen(self):
        self.game.toggle_fullscreen()
        self._sync_labels()

    def back(self):
        try:
            self.game.settings_store.save(self.game.preferences)
        except OSError:
            self.notice = "Не удалось сохранить настройки: проверьте папку сохранений."
            return
        self.game.change_state(self.return_state or MainMenu(self.game))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.back()
            return
        for slider in self.sliders:
            if slider.handle_event(event):
                return
        _dispatch(self.buttons, event)

    def draw(self, surface):
        g = self.game
        if isinstance(self.return_state, PauseMenu):
            self.return_state.gameplay.draw(surface)
            _dim(surface, 220)
        else:
            g.background.draw(surface)
        panel(surface, (228, 52, 824, 548), (12, 24, 41))
        label(surface, "ПАРАМЕТРЫ ПОЛЁТА", (270, 79), g.assets, 14, COLORS["cyan"], bold=True)
        label(surface, "Настройки", (267, 108), g.assets, 39, bold=True)
        rows = [
            ("Громкость музыки", "Спокойный космический фон", 205),
            ("Громкость эффектов", "Выстрелы, попадания и интерфейс", 285),
            ("Дрожание камеры", "Сильные попадания и взрывы", 365),
            ("Количество частиц", "След двигателя, искры и обломки", 445),
            ("Режим экрана", "F11 переключает режим в любой момент", 525),
        ]
        for title, detail, y in rows:
            label(surface, title, (270, y), g.assets, 21)
            label(surface, detail, (270, y + 32), g.assets, 14, COLORS["muted"])
        self._sync_labels()
        for slider in self.sliders:
            slider.draw(surface, g.mouse_position)
        _draw_buttons(g, surface, self.buttons)
        if self.notice:
            label(surface, self.notice, (596, 640), g.assets, 14, COLORS["red"])
        else:
            label(surface, "Изменения применяются сразу и сохраняются при выходе.", (606, 642),
                  g.assets, 14, COLORS["muted"])
        _fade(surface, self.elapsed)
