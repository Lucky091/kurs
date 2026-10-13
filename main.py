"""Точка входа; параметры headless/frames полезны для проверки в CI."""
import argparse
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Звёздный рубеж — космический шутер")
    parser.add_argument("--headless", action="store_true", help="SDL без графического дисплея")
    parser.add_argument("--frames", type=int, default=0, help="Завершить после N кадров (0 — без лимита)")
    parser.add_argument("--screenshot", type=Path, help="Сохранить последний логический кадр в PNG")
    args = parser.parse_args()
    if args.headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    from game import Game
    Game().run(max_frames=max(0, args.frames), screenshot=args.screenshot)


if __name__ == "__main__":
    main()
