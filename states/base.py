"""Единый интерфейс состояний приложения (State Pattern)."""


class State:
    def __init__(self, game):
        self.game = game
        self.elapsed = 0.0

    def enter(self):
        pass

    def handle_event(self, event):
        pass

    def update(self, dt):
        self.elapsed += dt

    def draw(self, surface):
        raise NotImplementedError
