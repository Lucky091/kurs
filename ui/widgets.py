"""Небольшие виджеты в логических координатах 1280 × 720."""

from __future__ import annotations

from collections.abc import Callable

import pygame


COLORS = {
    "bg": (7, 13, 27), "panel": (15, 26, 44), "panel_light": (23, 40, 61),
    "text": (225, 237, 248), "muted": (126, 151, 173), "cyan": (78, 223, 239),
    "orange": (255, 166, 81), "red": (255, 103, 113), "green": (116, 226, 172),
    "border": (44, 67, 87),
}


def label(surface, text, pos, assets, size=22, color=None, bold=False, align="left"):
    """Шрифт приходит из кеша AssetManager; здесь нет чтения файлов."""
    rendered = assets.font(size, bold=bold).render(str(text), True, color or COLORS["text"])
    rect = rendered.get_rect()
    if align == "center":
        rect.center = pos
    elif align == "right":
        rect.topright = pos
    else:
        rect.topleft = pos
    surface.blit(rendered, rect)
    return rect


def panel(surface, rect, color=None, border=None, radius=14):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, color or COLORS["panel"], rect, border_radius=radius)
    pygame.draw.rect(surface, border or COLORS["border"], rect, 1, border_radius=radius)


def bar(surface, rect, value, maximum, color, background=(29, 43, 58)):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, background, rect, border_radius=rect.height // 2)
    ratio = max(0.0, min(1.0, value / maximum)) if maximum > 0 else 0.0
    if ratio:
        fill = rect.copy()
        fill.width = max(2, round(rect.width * ratio))
        pygame.draw.rect(surface, color, fill, border_radius=rect.height // 2)


class Button:
    def __init__(self, rect, text, callback: Callable, enabled=True, *, assets=None,
                 primary=False, font_size=21, sound=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.enabled = enabled
        self.assets = assets
        self.primary = primary
        self.font_size = font_size
        self.sound = sound
        self.pressed = False
        self.hovered = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.pressed = bool(self.enabled and self.rect.collidepoint(event.pos))
            return self.pressed
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            activate = self.pressed and self.enabled and self.rect.collidepoint(event.pos)
            self.pressed = False
            if activate:
                if self.sound:
                    self.sound("click")
                self.callback()
                return True
        return False

    def draw(self, surface, mouse_position=(-100, -100)):
        self.hovered = self.rect.collidepoint(mouse_position)
        if not self.enabled:
            bg, border, fg = (16, 25, 37), (33, 45, 59), (83, 102, 119)
        elif self.pressed:
            bg, border, fg = (31, 88, 108), COLORS["cyan"], COLORS["text"]
        elif self.hovered:
            bg, border, fg = (27, 65, 83), COLORS["cyan"], COLORS["text"]
        elif self.primary:
            bg, border, fg = (25, 68, 83), (66, 176, 196), COLORS["text"]
        else:
            bg, border, fg = COLORS["panel_light"], COLORS["border"], COLORS["text"]
        panel(surface, self.rect, bg, border, 10)
        if self.enabled and self.hovered:
            pygame.draw.rect(surface, COLORS["cyan"], (self.rect.x + 4, self.rect.y + 12, 3,
                                                     self.rect.height - 24), border_radius=2)
        label(surface, self.text, self.rect.center, self.assets, self.font_size, fg,
              bold=self.primary, align="center")


class Slider:
    def __init__(self, rect, value, on_change, *, assets):
        self.rect = pygame.Rect(rect)
        self.value = max(0.0, min(1.0, float(value)))
        self.on_change = on_change
        self.assets = assets
        self.dragging = False

    def _set_from_x(self, x):
        self.value = max(0.0, min(1.0, (x - self.rect.left) / self.rect.width))
        self.on_change(self.value)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hitbox = self.rect.inflate(16, 22)
            if hitbox.collidepoint(event.pos):
                self.dragging = True
                self._set_from_x(event.pos[0])
                return True
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_x(event.pos[0])
            return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self._set_from_x(event.pos[0])
                self.dragging = False
                return True
        return False

    def draw(self, surface, mouse_position=(-100, -100)):
        track = pygame.Rect(self.rect.x, self.rect.centery - 3, self.rect.width, 6)
        bar(surface, track, self.value, 1, COLORS["cyan"])
        center = (round(self.rect.left + self.value * self.rect.width), self.rect.centery)
        pygame.draw.circle(surface, (23, 49, 68), center, 12)
        pygame.draw.circle(surface, COLORS["cyan"], center, 8)
        label(surface, f"{round(self.value * 100)}%", (self.rect.right + 23, self.rect.y - 2),
              self.assets, 21, COLORS["cyan"])
