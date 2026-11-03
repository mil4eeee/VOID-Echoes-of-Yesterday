"""Run: python -m unittest discover -s tests -v (pygame-ce required)."""
import os
import sys
import unittest
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pygame
from health_healing import Health, HealingOrb, OpeningTutorial
from menu_ui import valid_save
from shadow_encounter import ShadowEncounter, CrouchAnimation


class HealthHealingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init(); pygame.display.set_mode((960,540))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.health=Health()
        self.orb=HealingOrb(ROOT,1.7)
        self.platform=pygame.Rect(0,490,300,20)
        self.player=pygame.Rect(170,430,40,60)

    def idle_orb(self):
        for _ in range(50):
            self.orb.update(1/60,self.player,self.platform,False,self.health)
        self.assertEqual(self.orb.state,'idle')

    def test_start_cap_and_thresholds(self):
        self.assertEqual(self.health.current,75)
        self.assertEqual(self.health.heal(25),25)
        self.assertEqual(self.health.heal(25),0)
        self.assertEqual(self.health.current,100)
        self.assertEqual(self.health.color,(78,205,124))
        self.health.reset(50); self.assertEqual(self.health.color,(238,193,70))
        self.health.reset(25); self.assertEqual(self.health.color,(231,74,86))

    def test_damage_cooldown_floor_and_visual_update(self):
        self.assertTrue(self.health.damage(25))
        self.assertEqual(self.health.current,50)
        self.assertFalse(self.health.damage(25))
        self.health.update(.1)
        self.assertTrue(50<self.health.display_hp<75)
        self.health.update(1)
        self.health.damage(1000)
        self.assertEqual(self.health.current,0)

    def test_only_e_in_range_collects(self):
        self.idle_orb()
        self.assertTrue(self.orb.near)
        self.assertEqual(self.health.current,75)
        self.player.x=900
        self.assertFalse(self.orb.update(.016,self.player,self.platform,True,self.health))
        self.player.x=170
        self.assertTrue(self.orb.update(.016,self.player,self.platform,True,self.health))
        self.assertEqual(self.health.current,100)
        self.assertTrue(self.orb.collected)
        self.assertFalse(self.orb.near)

    def test_pickup_frames_finish_and_cannot_heal_twice(self):
        self.idle_orb()
        self.orb.update(.016,self.player,self.platform,True,self.health)
        self.health.damage(25)
        seen=set()
        for _ in range(60):
            if self.orb.state=='pickup':
                seen.add(min(8,int(self.orb.time*self.orb.FPS['pickup'])))
            self.assertFalse(self.orb.update(1/60,self.player,self.platform,True,self.health))
        self.assertEqual(seen,set(range(9)))
        self.assertEqual(self.orb.state,'gone')
        self.assertEqual(self.health.current,75)

    def test_partial_heal_clamps_and_loaded_consumed_orb_stays_gone(self):
        self.idle_orb();self.health.reset(90)
        self.orb.update(.016,self.player,self.platform,True,self.health)
        self.assertEqual(self.health.current,100)
        self.orb.reset(True)
        self.assertEqual(self.orb.state,'gone')
        self.assertFalse(self.orb.update(.016,self.player,self.platform,True,self.health))

    def test_tutorial_timer_and_all_asset_sequences(self):
        tutorial=OpeningTutorial()
        self.assertTrue(tutorial.active)
        tutorial.update(6);self.assertFalse(tutorial.active)
        tutorial.reset(True);self.assertFalse(tutorial.active)
        self.assertEqual({s:len(f) for s,f in self.orb.frames.items()}, {'idle':8,'pickup':9,'spawn':9})

    def test_shadow_speed_preserved_and_crouch_still_dodges(self):
        self.assertEqual(ShadowEncounter.SPEED,235)
        self.assertEqual(ShadowEncounter.WARNING_SECONDS,.65)
        island=pygame.Rect(350,410,220,20)
        for crouched in (False,True):
            enemy=ShadowEncounter(ROOT,1.7)
            posture=CrouchAnimation(ROOT,1.7)
            player=pygame.Rect(440,350,40,60)
            hits=0
            for _ in range(260):
                posture.update(1/60,crouched,True)
                hits+=enemy.update(1/60,player,posture.hurtbox(player),island)
            self.assertEqual(hits,0 if crouched else 1)

    def test_legacy_save_and_new_field_validation(self):
        data={'version':1,'x':80,'y':400,'velocity_y':0,'on_ground':False,
              'facing_right':True,'widths':[300,220,220,200,180],
              'islands':[0,1,2,3,4],'moving_x':950,'moving_speed':2}
        self.assertTrue(valid_save(data))
        data.update(hp=100,healing_collected=True,tutorial_seen=True)
        self.assertTrue(valid_save(data))
        data['hp']=101;self.assertFalse(valid_save(data))
        data['hp']=100;data['healing_collected']='yes';self.assertFalse(valid_save(data))


if __name__=='__main__':
    unittest.main()
