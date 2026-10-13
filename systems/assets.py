"""Единственное место загрузки ресурсов: каждый файл читается только один раз."""
from pathlib import Path
import pygame


ASSET_ROOT = Path(__file__).resolve().parents[1] / "assets"


class AssetManager:
    """Singleton: все игровые объекты используют один общий кеш."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._images = {}
            cls._instance._fonts = {}
            cls._instance._sounds = {}
        return cls._instance

    def image(self, name: str) -> pygame.Surface:
        name = str(name).removesuffix(".png")
        if name not in self._images:
            path = ASSET_ROOT / "images" / f"{name}.png"
            loaded = pygame.image.load(str(path))
            # convert_alpha требует видеорежим; тесты сущностей могут идти без окна.
            if pygame.display.get_surface() is not None:
                loaded = loaded.convert_alpha()
            self._images[name] = loaded
        return self._images[name]

    def font(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = (max(8, int(size)), bool(bold))
        if key not in self._fonts:
            if not pygame.font.get_init():
                pygame.font.init()
            filename = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
            self._fonts[key] = pygame.font.Font(str(ASSET_ROOT / "fonts" / filename), key[0])
        return self._fonts[key]

    def sound(self, name: str):
        if pygame.mixer.get_init() is None:
            return None
        name = str(name).removesuffix(".wav")
        if name not in self._sounds:
            try:
                self._sounds[name] = pygame.mixer.Sound(str(ASSET_ROOT / "audio" / f"{name}.wav"))
            except (pygame.error, FileNotFoundError):
                self._sounds[name] = None
        return self._sounds[name]

    def clear_runtime_cache(self):
        """SDL-объекты шрифта/звука живут только до pygame.quit().

        Это позволяет повторно создать Game в том же процессе (например,
        в интеграционных тестах). Изображения не зависят от SDL-подсистем.
        """
        self._fonts.clear()
        self._sounds.clear()
