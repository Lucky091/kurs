import unittest

from systems.progression import RunProgress, ShopSystem


class ProgressionTests(unittest.TestCase):
    def setUp(self):
        self.progress = RunProgress()
        self.shop = ShopSystem(self.progress)

    def test_purchase_spends_exact_price_and_preserves_score(self):
        self.progress.award(750, 500)
        offer = next(o for o in self.shop.offers() if o["id"] == "speed")
        self.assertTrue(self.shop.purchase("speed"))
        self.assertEqual(self.progress.credits, 500 - offer["price"])
        self.assertEqual(self.progress.score, 750)
        self.assertEqual(self.progress.speed, 372)
        self.assertEqual(self.progress.levels["speed"], 1)
        next_offer = next(o for o in self.shop.offers() if o["id"] == "speed")
        self.assertGreater(next_offer["price"], offer["price"])

    def test_insufficient_balance_and_unknown_offer_are_noops(self):
        self.assertFalse(self.shop.purchase("speed"))
        self.assertFalse(self.shop.purchase("missing"))
        self.assertEqual(self.progress.credits, 0)
        self.assertEqual(self.progress.speed, 340)

    def test_every_upgrade_reaches_cap_without_further_debit(self):
        self.progress.credits = 100000
        for upgrade in ShopSystem.BASE_PRICES:
            for _ in range(ShopSystem.UPGRADE_LIMIT):
                self.assertTrue(self.shop.purchase(upgrade))
            balance = self.progress.credits
            self.assertFalse(self.shop.purchase(upgrade))
            self.assertEqual(self.progress.credits, balance)
            self.assertEqual(self.progress.levels[upgrade], 5)
        self.assertEqual(self.progress.max_health, 225)
        self.assertEqual(self.progress.max_shield, 140)

    def test_weapon_unlock_can_only_be_charged_once(self):
        self.progress.credits = 1000
        for weapon in ("rocket", "plasma"):
            self.assertTrue(self.shop.purchase(weapon))
            balance = self.progress.credits
            self.assertIn(weapon, self.progress.weapons)
            self.assertFalse(self.shop.purchase(weapon))
            self.assertEqual(self.progress.credits, balance)

    def test_repair_is_disabled_when_full_and_restores_health(self):
        self.progress.credits = 500
        self.assertFalse(self.shop.purchase("repair"))
        self.progress.health = 17
        price = next(o["price"] for o in self.shop.offers() if o["id"] == "repair")
        self.assertTrue(self.shop.purchase("repair"))
        self.assertEqual(self.progress.health, self.progress.max_health)
        self.assertEqual(self.progress.credits, 500 - price)
        self.assertFalse(self.shop.purchase("repair"))

    def test_new_run_has_independent_inventory_and_levels(self):
        self.progress.credits = 1000
        self.shop.purchase("rocket")
        self.shop.purchase("shield")
        fresh = RunProgress()
        self.assertNotEqual(fresh.run_id, self.progress.run_id)
        self.assertEqual(fresh.weapons, {"laser"})
        self.assertEqual(fresh.levels["shield"], 0)
        self.assertEqual(fresh.health, 100)
        self.assertEqual(fresh.credits, 0)


if __name__ == "__main__":
    unittest.main()
