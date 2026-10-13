"""Объекты игрового мира: корабли, оружие, метеориты и бонусы."""

from .ships import Boss, Enemy, Player, SpaceShip
from .projectiles import Laser, Plasma, Projectile, Rocket
from .meteors import Meteor
from .pickups import Bonus

__all__ = [
    "SpaceShip", "Player", "Enemy", "Boss", "Projectile", "Laser",
    "Rocket", "Plasma", "Meteor", "Bonus",
]
