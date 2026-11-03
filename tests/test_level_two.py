import os
import sys
import unittest
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pygame
from level_two import LevelTwoCombat, LevelTwoStory, ISLANDS
from health_healing import Health
from menu_ui import valid_save


class LevelTwoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init();pygame.font.init();pygame.display.set_mode((960,540))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.islands=[pygame.Rect(values) for values in ISLANDS]
        self.combat=LevelTwoCombat(ROOT,1.7,self.islands)
        self.health=Health()
        self.enemy=self.combat.enemies[0]
        self.player=pygame.Rect(0,0,40,60)
        self.player.midbottom=(self.enemy.x-60,self.enemy.island.top)

    def test_strike_has_warning_and_jumping_avoids_damage(self):
        self.combat.update(.01,self.player,True,False,self.health)
        self.assertEqual(self.enemy.state,'windup')
        self.assertEqual(self.health.current,75)
        self.combat.update(.86,self.player,True,False,self.health)
        self.player.y-=80
        self.combat.update(.01,self.player,True,False,self.health)
        self.assertEqual(self.health.current,75)
        self.player.y+=80
        self.combat.update(.01,self.player,True,False,self.health)
        self.assertEqual(self.health.current,55)
        self.combat.update(.01,self.player,True,False,self.health)
        self.assertEqual(self.health.current,55)

    def test_attack_requires_recovery_range_direction_and_cooldown(self):
        self.combat.update(.01,self.player,True,True,self.health)
        self.assertEqual(self.enemy.hp,2)
        self.enemy.state='recovery'
        self.combat.update(.01,self.player,True,True,self.health)
        self.assertEqual(self.enemy.hp,2)
        self.combat.update(.41,self.player,False,True,self.health)
        self.assertEqual(self.enemy.hp,2)
        self.enemy.state='recovery';self.enemy.time=0
        self.combat.update(.41,self.player,True,True,self.health)
        self.assertEqual(self.enemy.hp,1)

    def test_combined_encounter_waits_for_flying_shadow(self):
        enemy=self.combat.enemies[1]
        self.player.midbottom=(enemy.x-50,enemy.island.top)
        for _ in range(180):
            self.combat.update(1/60,self.player,True,False,self.health,True)
        self.assertEqual(enemy.state,'idle')
        self.assertEqual(self.health.current,75)
        self.combat.update(.01,self.player,True,False,self.health,False)
        self.assertEqual(enemy.state,'windup')

    def test_defeats_persist_across_respawn_and_restore(self):
        self.combat.restore([0,1]);self.combat.respawn()
        self.assertEqual(self.combat.snapshot(),[0,1])
        self.assertFalse(self.combat.cleared)
        self.combat.restore([0,0]);self.assertTrue(self.combat.cleared)
        self.combat.restore([-1,100]);self.assertEqual(self.combat.snapshot(),[0,0])

    def test_chapter_title_fade_and_no_level_one_dialogue(self):
        story=LevelTwoStory()
        self.assertEqual(story.phase,'level2_title')
        story.update(2,None);self.assertEqual(story.phase,'opening_fade')
        story.update(1,None);self.assertFalse(story.blocked)
        self.assertIsNone(story.dialogue.scene)
        story.on_memory();story.update(.7,None)
        self.assertEqual(story.phase,'chapter')
        restored=LevelTwoStory();restored.reset(story.snapshot())
        self.assertEqual(restored.phase,'chapter')

    def test_level_two_save_validation_and_legacy_rejection(self):
        data=dict(version=1,level=2,x=1700,y=175,velocity_y=0,on_ground=True,
                  facing_right=True,widths=[300,270,280,290,210],islands=[0,4,4,1,3],
                  moving_x=780,moving_speed=2,duels=[0,1],hp=80)
        self.assertTrue(valid_save(data))
        data['level']=1;self.assertFalse(valid_save(data))
        data['level']=2;data['duels']=[-1,0];self.assertFalse(valid_save(data))


if __name__=='__main__':
    unittest.main()
