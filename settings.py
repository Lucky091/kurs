"""Размер игрового мира не зависит от реального размера окна."""
from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parent
WIDTH, HEIGHT = 1280, 720
FPS = 60
MAX_DT = 0.05
PLAY_BOUNDS = pygame.Rect(24, 92, 1232, 600)
TITLE = "Звёздный рубеж"
BG = (7, 12, 25)
PANEL = (15, 25, 43)
TEXT = (229, 240, 249)
MUTED = (131, 155, 178)
CYAN = (64, 226, 237)
ORANGE = (255, 170, 83)
RED = (255, 89, 108)
GREEN = (117, 236, 169)
