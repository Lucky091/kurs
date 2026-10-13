"""Характеристики забега и покупки: логика не зависит от интерфейса Pygame."""

from dataclasses import dataclass, field
from math import ceil
from uuid import uuid4


@dataclass
class RunProgress:
    """Один объект живёт от начала забега до сохранения его результата."""

    run_id: str = field(default_factory=lambda: str(uuid4()))
    score: int = 0
    credits: int = 0
    wave: int = 1
    health: float = 100.0
    max_health: float = 100.0
    shield: float = 0.0
    max_shield: float = 0.0
    speed: float = 340.0
    fire_rate: float = 1.0
    damage_multiplier: float = 1.0
    weapon: str = "laser"
    weapons: set[str] = field(default_factory=lambda: {"laser"})
    levels: dict[str, int] = field(default_factory=lambda: {
        "speed": 0, "fire_rate": 0, "damage": 0, "health": 0, "shield": 0,
    })

    def award(self, score: int, credits: int) -> None:
        """Боевые награды независимы: покупки никогда не уменьшают счёт."""
        self.score += max(0, int(score))
        self.credits += max(0, int(credits))


class ShopSystem:
    """Проверяет покупки повторно в момент клика, а не только при отрисовке."""

    # Максимумы ограничивают рост характеристик и сохраняют различия оружия.
    UPGRADE_LIMIT = 5
    BASE_PRICES = {"speed": 65, "fire_rate": 80, "damage": 100,
                   "health": 90, "shield": 110}
    TITLES = {"speed": "Двигатель", "fire_rate": "Скорострельность",
              "damage": "Урон оружия", "health": "Усиление корпуса",
              "shield": "Энергетический щит", "repair": "Ремонт корпуса",
              "rocket": "Ракетная установка", "plasma": "Плазменная пушка"}

    def __init__(self, progress: RunProgress):
        self.progress = progress

    def _upgrade_detail(self, upgrade: str) -> str:
        p = self.progress
        if upgrade == "speed":
            return f"Скорость: {p.speed:.0f} → {p.speed + 32:.0f}"
        if upgrade == "fire_rate":
            return f"Частота огня: ×{p.fire_rate:.2f} → ×{p.fire_rate + .16:.2f}"
        if upgrade == "damage":
            return f"Урон: ×{p.damage_multiplier:.2f} → ×{p.damage_multiplier + .2:.2f}"
        if upgrade == "health":
            return f"Прочность: {p.max_health:.0f} → {p.max_health + 25:.0f} (+25 здоровья)"
        target = 40 if p.max_shield == 0 else p.max_shield + 25
        return f"Щит: {p.max_shield:.0f} → {target:.0f}; заряд восстанавливается"

    def offers(self) -> list[dict]:
        p = self.progress
        result = []
        for upgrade, base_price in self.BASE_PRICES.items():
            level = p.levels[upgrade]
            price = int(ceil(base_price * 1.5 ** level / 5) * 5)
            at_limit = level >= self.UPGRADE_LIMIT
            result.append({"id": upgrade, "title": self.TITLES[upgrade],
                           "detail": "Достигнут максимальный уровень" if at_limit
                           else self._upgrade_detail(upgrade),
                           "price": price, "level": level,
                           "max_level": self.UPGRADE_LIMIT,
                           "enabled": not at_limit and p.credits >= price})
        missing_health = max(0.0, p.max_health - p.health)
        repair_price = 35 + int(ceil(missing_health * .25 / 5) * 5)
        result.append({"id": "repair", "title": self.TITLES["repair"],
                       "detail": f"Здоровье: {p.health:.0f} → {p.max_health:.0f}",
                       "price": repair_price, "level": 0, "max_level": 1,
                       "enabled": missing_health > 0 and p.credits >= repair_price})
        for weapon, price, detail in (
            ("rocket", 160, "Высокий урон и взрыв; перезарядка 0,95 с"),
            ("plasma", 200, "Мощный заряд пробивает до трёх целей"),
        ):
            unlocked = weapon in p.weapons
            result.append({"id": weapon, "title": self.TITLES[weapon],
                           "detail": "Оружие уже открыто" if unlocked else detail,
                           "price": price, "level": int(unlocked), "max_level": 1,
                           "enabled": not unlocked and p.credits >= price})
        return result

    def purchase(self, offer_id: str) -> bool:
        """Одна успешная покупка списывает стоимость один раз и применяет эффект."""
        offer = next((item for item in self.offers() if item["id"] == offer_id), None)
        if offer is None or not offer["enabled"]:
            return False
        p = self.progress
        if offer_id == "speed":
            p.speed += 32
        elif offer_id == "fire_rate":
            p.fire_rate += .16
        elif offer_id == "damage":
            p.damage_multiplier += .2
        elif offer_id == "health":
            p.max_health += 25
            p.health = min(p.max_health, p.health + 25)
        elif offer_id == "shield":
            p.max_shield = 40 if p.max_shield == 0 else p.max_shield + 25
            p.shield = p.max_shield
        elif offer_id == "repair":
            p.health = p.max_health
        else:
            p.weapons.add(offer_id)
        if offer_id in p.levels:
            p.levels[offer_id] += 1
        p.credits -= offer["price"]
        return True
