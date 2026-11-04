import os,sys,unittest
from pathlib import Path
from types import SimpleNamespace
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pygame
from meadow_combat import MeadowAttack
from level_two import LevelTwoStory,LevelTwoCombat,ISLANDS


class AttackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init();pygame.font.init();pygame.display.set_mode((960,540))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_both_attacks_hit_once_on_contact_frame_and_finish(self):
        attack=MeadowAttack(ROOT,1.7)
        for kind in ('sweep','overhead'):
            self.assertTrue(attack.start(kind,False))
            self.assertFalse(attack.start(kind,True))
            self.assertFalse(attack.facing_right)
            hits=[]
            for frame in range(32):
                if attack.update(1/60):hits.append(frame)
            self.assertEqual(len(hits),1)
            self.assertIn(hits[0],(8,9))
            self.assertFalse(attack.active)

    def test_frame_sizes_alpha_and_reset(self):
        attack=MeadowAttack(ROOT,1.7)
        sizes={frame.get_size() for frames in attack.frames.values() for frame in frames}
        self.assertEqual(len(sizes),1)
        for frames in attack.frames.values():
            self.assertEqual(len(frames),6)
            for frame in frames:
                self.assertEqual(frame.get_at((0,0)).a,0)
        attack.start('sweep',True);attack.reset()
        self.assertFalse(attack.update(1))

    def test_late_press_buffers_next_attack_and_early_press_expires(self):
        attack=MeadowAttack(ROOT,1.7)
        attack.start('sweep',True);attack.update(.24)
        attack.start('overhead',True);attack.update(.13)
        self.assertEqual(attack.kind,'overhead')
        attack.reset();attack.start('sweep',True);attack.start('overhead',True)
        attack.update(.4);self.assertFalse(attack.active)

    def test_level_two_heal_animation_returns_to_gameplay_without_dialogue(self):
        story=LevelTwoStory();story.on_heal()
        story.update(.1,SimpleNamespace(state='pickup'))
        self.assertTrue(story.blocked)
        restored=LevelTwoStory();restored.reset(story.snapshot())
        restored.update(.1,SimpleNamespace(state='gone'))
        self.assertEqual(restored.phase,'gameplay')
        self.assertIsNone(restored.dialogue.scene)

    def test_ground_creature_uses_supplied_sequences(self):
        combat=LevelTwoCombat(ROOT,1.7,[pygame.Rect(v) for v in ISLANDS])
        self.assertEqual({key:len(value) for key,value in combat.enemies[0].frames.items()},
                         {'run':8,'attack':8,'idle':4})
