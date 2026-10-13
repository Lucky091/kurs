"""Звук необязателен: отсутствие аудиоустройства не мешает играть."""
import pygame
from systems.assets import AssetManager, ASSET_ROOT


class AudioManager:
    def __init__(self, settings: dict):
        self.enabled = False
        self.effects_volume = 0.65
        self.music_volume = 0.3
        self._music_started = False
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            # Верхняя граница исключает десятки одновременных взрывов.
            pygame.mixer.set_num_channels(12)
            self.enabled = True
        except pygame.error:
            pass
        self.apply_settings(settings)

    def apply_settings(self, settings: dict):
        self.effects_volume = max(0.0, min(1.0, float(settings.get("effects_volume", 0.65))))
        self.music_volume = max(0.0, min(1.0, float(settings.get("music_volume", 0.3))))
        if self.enabled:
            pygame.mixer.music.set_volume(self.music_volume)
            # Уже воспроизводимые эффекты тоже сразу реагируют на настройки.
            for index in range(pygame.mixer.get_num_channels()):
                pygame.mixer.Channel(index).set_volume(self.effects_volume)

    def play(self, name: str):
        if not self.enabled or self.effects_volume <= 0:
            return
        sound = AssetManager().sound(name)
        if sound is None:
            return
        # Если каналы заняты, новый эффект пропускается, а не обрывает другие.
        channel = pygame.mixer.find_channel(False)
        if channel is not None:
            channel.set_volume(self.effects_volume)
            channel.play(sound)

    def start_music(self):
        if not self.enabled or self._music_started:
            return
        try:
            pygame.mixer.music.load(str(ASSET_ROOT / "audio" / "music.wav"))
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(-1, fade_ms=1600)
            self._music_started = True
        except (pygame.error, FileNotFoundError):
            # Повреждённый/отсутствующий необязательный звук не прерывает игру.
            pass
