"""Проверки движения, оружия, повреждений, ИИ и физики осколков."""

import random
import unittest
from unittest.mock import patch

import pygame

from entities.meteors import Meteor
from entities.projectiles import Laser, Plasma, Rocket
from entities.ships import Boss, Enemy, Player
from settings import PLAY_BOUNDS
from systems.progression import RunProgress


class PlayerTests(unittest.TestCase):
    def test_diagonal_is_normalized_and_bounds_are_enforced(self):
        straight = Player(RunProgress())
        diagonal = Player(RunProgress())
        origin = straight.position.copy()
        straight.update(.1, (1, 0))
        diagonal.update(.1, (1, -1))
        self.assertAlmostEqual(straight.position.distance_to(origin),
                               diagonal.position.distance_to(origin))
        straight.update(100, (1, -1))
        self.assertTrue(PLAY_BOUNDS.contains(straight.rect))
        self.assertEqual(straight.rect.top, PLAY_BOUNDS.top)
        self.assertEqual(straight.rect.right, PLAY_BOUNDS.right)

    def test_weapons_unlock_and_share_cooldown(self):
        progress = RunProgress()
        player = Player(progress)
        self.assertFalse(player.select_weapon(2))
        laser = player.try_shoot()[0]
        self.assertIsInstance(laser, Laser)
        self.assertEqual(player.try_shoot(), [])
        progress.weapons.add("rocket")
        self.assertTrue(player.select_weapon(2))
        self.assertEqual(player.try_shoot(), [])
        player.update(.2)
        rocket = player.try_shoot()[0]
        self.assertIsInstance(rocket, Rocket)
        self.assertGreater(rocket.damage, laser.damage)
        player.update(1)
        progress.weapons.add("plasma")
        player.select_weapon(3)
        plasma = player.try_shoot()[0]
        self.assertIsInstance(plasma, Plasma)
        self.assertEqual(plasma.remaining_pierces, 3)
        self.assertGreater(player.fire_interval, Player.BASE_INTERVALS["laser"])

    def test_shield_invulnerability_and_delayed_recharge(self):
        progress = RunProgress(shield=20, max_shield=40)
        player = Player(progress)
        self.assertFalse(player.take_damage(30))
        self.assertEqual(progress.shield, 0)
        self.assertEqual(progress.health, 90)
        player.take_damage(1000)
        self.assertEqual(progress.health, 90)
        player.update(1)
        self.assertEqual(progress.shield, 0)
        player.update(3)
        self.assertGreater(progress.shield, 0)
        self.assertEqual(progress.health, 90)
        self.assertTrue(player.take_damage(1000))


class MeteorTests(unittest.TestCase):
    def test_fragment_mass_momentum_size_and_separation(self):
        for size, child_size in (("large", "medium"), ("medium", "small")):
            for count in (2, 3):
                with self.subTest(size=size, count=count):
                    meteor = Meteor(size, (420, 320), (31, 79))
                    with patch("entities.meteors.random.choice", return_value=count):
                        fragments = meteor.split()
                    self.assertEqual(len(fragments), count)
                    self.assertEqual({child.size for child in fragments}, {child_size})
                    self.assertAlmostEqual(sum(child.mass for child in fragments), meteor.mass)
                    original_momentum = meteor.velocity * meteor.mass
                    new_momentum = sum((child.velocity * child.mass for child in fragments),
                                       pygame.Vector2())
                    self.assertLess(original_momentum.distance_to(new_momentum), 1e-8)
                    for first in fragments:
                        self.assertGreater(first.position.distance_to(meteor.position), 0)
                        for second in fragments:
                            if first is not second:
                                self.assertGreater(first.position.distance_to(second.position), 25)
                    self.assertEqual(meteor.split(), [])
        self.assertEqual(Meteor("small", (10, 10)).split(), [])

    def test_rotated_masks_and_reverse_fragment_escape(self):
        meteor = Meteor("small", (640, 320), (0, 80))
        meteor.rotation_speed = 100
        meteor.update(.2)
        self.assertEqual(meteor.mask.get_size(), meteor.image.get_size())
        self.assertEqual(meteor.rect.size, meteor.image.get_size())
        reverse = Meteor("small", (640, -155), (0, -60))
        group = pygame.sprite.Group(reverse)
        reverse.update(.2)
        self.assertTrue(reverse.escaped)
        self.assertEqual(len(group), 0)


class EnemyTests(unittest.TestCase):
    def test_interceptor_reacts_to_future_intersection_not_receding_shots(self):
        random.seed(4)
        enemy = Enemy("interceptor", (640, 250), 3)
        approaching = Laser((640, 600), (0, -850), 11)
        enemy._consider_dodge([approaching])
        self.assertGreater(abs(enemy._dodge_velocity), 0)
        self.assertLessEqual(abs(enemy._dodge_velocity), 190)
        enemy._dodge_velocity = 0
        receding = Laser((640, 50), (0, -850), 11)
        enemy._consider_dodge([receding])
        self.assertEqual(enemy._dodge_velocity, 0)

    def test_enemy_warns_before_first_shot_and_escapes(self):
        enemy = Enemy("gunner", (640, -55))
        initial_cooldown = enemy.cooldown
        enemy.update(.5, (640, 620))
        self.assertEqual(enemy.cooldown, initial_cooldown)
        self.assertFalse(enemy.escaped)
        self.assertEqual(enemy.try_shoot(), [])
        enemy.position.y = 180
        enemy.cooldown = .3
        enemy.update(.1, (640, 620))
        self.assertGreater(enemy.warning_timer, 0)
        self.assertEqual(enemy.try_shoot(), [])
        enemy.update(.3, (640, 620))
        shot = enemy.try_shoot()[0]
        self.assertEqual(shot.owner, "enemy")
        self.assertGreater(shot.velocity.y, 0)
        enemy.position.y = 900
        group = pygame.sprite.Group(enemy)
        enemy.update(.1, (640, 620))
        self.assertTrue(enemy.escaped)
        self.assertFalse(group)

    def test_boss_has_two_phases_and_sparse_attack_corridors(self):
        boss = Boss((640, 165), 5)
        self.assertEqual(boss.phase, 1)
        boss.take_damage(boss.max_hp * .6)
        self.assertEqual(boss.phase, 2)
        boss.attack_index = 2
        boss.cooldown = .3
        boss.update(.1, (640, 620))
        self.assertGreater(boss.warning_timer, 0)
        boss.update(.3, (640, 620))
        shots = boss.try_shoot()
        self.assertEqual(len(shots), 8)
        self.assertTrue(all(abs(shot.position.x - 640) >= 120 for shot in shots))
        self.assertFalse(boss.escaped)


if __name__ == "__main__":
    unittest.main()
