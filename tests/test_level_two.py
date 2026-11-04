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

    def test_attacks_connect_outside_active_lunge_and_obey_direction(self):
        self.enemy.state='windup'
        self.assertTrue(self.enemy.receive_attack(self.player,True))
        self.assertEqual(self.enemy.hp,1)
        self.assertEqual(self.enemy.state,'windup')
        self.enemy.state='strike'
        self.assertFalse(self.enemy.receive_attack(self.player,True))
        self.enemy.state='recovery'
        self.assertFalse(self.enemy.receive_attack(self.player,False))
        self.assertTrue(self.enemy.receive_attack(self.player,True))
        self.assertTrue(self.enemy.defeated)

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

    def test_level_two_fade_arrival_and_pending_memory(self):
        story=LevelTwoStory()
        self.assertEqual(story.phase,'opening_fade')
        story.update(2.99,None);self.assertTrue(story.blocked)
        story.update(.02,None);self.assertEqual(story.dialogue.scene,'l2_arrival')
        self.assertTrue(story.blocked)
        story.on_memory();story.update(.7,None)
        self.assertEqual(story.phase,'dialogue');self.assertTrue(story.second_memory_pending)
        self.assertEqual(story.dialogue.scene,'l2_memory_before')
        restored=LevelTwoStory();restored.reset(story.snapshot())
        self.assertEqual(restored.dialogue.scene,'l2_memory_before');self.assertTrue(restored.second_memory_pending)

    def test_level_two_save_validation_and_legacy_rejection(self):
        data=dict(version=1,level=2,x=1700,y=175,velocity_y=0,on_ground=True,
                  facing_right=True,widths=[300,270,280,290,210],islands=[0,4,4,1,3],
                  moving_x=780,moving_speed=2,duels=[0,1],hp=80)
        self.assertTrue(valid_save(data))
        data['level']=1;self.assertFalse(valid_save(data))
        data['level']=2;data['duels']=[-1,0];self.assertFalse(valid_save(data))


if __name__=='__main__':
    unittest.main()
