"""Приложение: события → текущее состояние → логический кадр → окно.

Letterboxing сохраняет пропорции. Одна обратная математика применяется
ко всем мышиным событиям, поэтому интерфейс работает при любом размере.
"""
from pathlib import Path
import pygame
from settings import WIDTH, HEIGHT, FPS, MAX_DT, TITLE
from systems.assets import AssetManager
from systems.audio import AudioManager
from systems.background import Starfield
from systems.persistence import SettingsStore, LeaderboardDB
from states.menus import MainMenu, PauseMenu


class Game:
    width, height = WIDTH, HEIGHT

    def __init__(self, data_dir=None):
        pygame.display.init()
        pygame.font.init()
        if data_dir is not None:
            data_dir = Path(data_dir)
        self.settings_store = SettingsStore(data_dir / "settings.json" if data_dir else None)
        self.preferences = self.settings_store.load()
        self.leaderboard = LeaderboardDB(data_dir / "scores.sqlite3" if data_dir else None)
        self.screen = pygame.Surface((WIDTH, HEIGHT))
        self.window_size = (WIDTH, HEIGHT)
        self.display = None
        self.viewport = pygame.Rect(0, 0, WIDTH, HEIGHT)
        self.fullscreen = bool(self.preferences["fullscreen"])
        self.set_display()
        pygame.display.set_caption(TITLE)
        self.assets = AssetManager()
        pygame.display.set_icon(self.assets.image("ship_player"))
        self.audio = AudioManager(self.preferences)
        self.audio.start_music()
        self.background = Starfield()
        self.running = True
        self.gameplay = None
        self.state = None
        self.mouse_position = (-100, -100)
        self.clock = pygame.time.Clock()
        self.change_state(MainMenu(self))

    def set_display(self):
        if self.fullscreen:
            self.display = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.display = pygame.display.set_mode(self.window_size, pygame.RESIZABLE)
        self.resize_viewport(self.display.get_size())

    def resize_viewport(self, size):
        w, h = size
        scale = min(w / WIDTH, h / HEIGHT)
        scaled = (max(1, round(WIDTH * scale)), max(1, round(HEIGHT * scale)))
        self.viewport = pygame.Rect((w - scaled[0]) // 2, (h - scaled[1]) // 2, *scaled)

    def window_to_logical(self, position):
        if not self.viewport.collidepoint(position):
            return (-100, -100)
        return ((position[0] - self.viewport.x) * WIDTH / self.viewport.width,
                (position[1] - self.viewport.y) * HEIGHT / self.viewport.height)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.preferences["fullscreen"] = self.fullscreen
        self.set_display()
        self.settings_store.save(self.preferences)

    def change_state(self, state):
        if self.state is self.gameplay and self.gameplay is not None and state is not self.gameplay:
            self.gameplay.mouse_fire = False
        if self.state is not None:
            callback = getattr(self.state, "exit", None)
            if callback:
                callback()
        self.state = state
        callback = getattr(state, "enter", None)
        if callback:
            callback()

    def new_run(self):
        from states.gameplay import Gameplay
        self.gameplay = Gameplay(self)
        self.change_state(self.gameplay)

    def quit(self):
        self.running = False

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            # Закрытие окна на экране результата также сохраняет забег.
            if hasattr(self.state, "save_result"):
                self.state.save_result()
            self.quit()
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            self.toggle_fullscreen()
            return
        lost_focus = event.type == pygame.WINDOWFOCUSLOST
        if event.type == pygame.ACTIVEEVENT:
            lost_focus = not event.gain and bool(event.state & 6)
        if lost_focus and self.state is self.gameplay:
            self.change_state(PauseMenu(self, self.gameplay))
            return
        if event.type == pygame.VIDEORESIZE and not self.fullscreen:
            self.window_size = (max(480, event.w), max(270, event.h))
            self.set_display()
        if event.type == pygame.WINDOWSIZECHANGED:
            self.resize_viewport(self.display.get_size())
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            attributes = event.dict.copy()
            attributes["pos"] = self.window_to_logical(event.pos)
            self.mouse_position = attributes["pos"]
            event = pygame.event.Event(event.type, attributes)
        self.state.handle_event(event)

    def update(self, dt):
        dt = min(MAX_DT, max(0.0, dt))
        # Пауза и её настройки не двигают даже фон: ни один боевой таймер
        # не получает delta time, пока Gameplay не станет текущим состоянием.
        from states.menus import Settings
        frozen = isinstance(self.state, PauseMenu) or (
            isinstance(self.state, Settings) and isinstance(self.state.return_state, PauseMenu))
        if not frozen:
            self.background.update(dt)
        self.state.update(dt)

    def draw(self):
        self.state.draw(self.screen)
        self.display.fill((0, 0, 0))
        scaled = pygame.transform.smoothscale(self.screen, self.viewport.size)
        self.display.blit(scaled, self.viewport)
        pygame.display.flip()

    def run(self, max_frames=0, screenshot=None):
        frames = 0
        try:
            while self.running:
                dt = min(self.clock.tick(FPS) / 1000.0, MAX_DT)
                self.mouse_position = self.window_to_logical(pygame.mouse.get_pos())
                for event in pygame.event.get():
                    self.handle_event(event)
                self.update(dt)
                self.draw()
                frames += 1
                if max_frames and frames >= max_frames:
                    break
            if screenshot:
                screenshot = Path(screenshot)
                screenshot.parent.mkdir(parents=True, exist_ok=True)
                pygame.image.save(self.screen, screenshot)
        finally:
            self.close()

    def close(self):
        self.settings_store.save(self.preferences)
        self.leaderboard.close()
        self.assets.clear_runtime_cache()
        pygame.quit()
