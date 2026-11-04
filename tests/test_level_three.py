import os,sys,unittest
from pathlib import Path
from types import SimpleNamespace
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame
from level_three import ISLANDS,MOTIONS,MovingIslands,LevelThreeStory,valid_motion_save
from level_two import LevelTwoCombat
from health_healing import HealingOrb,Health
from menu_ui import valid_save


class LevelThreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init();pygame.font.init();pygame.display.set_mode((960,540))
    @classmethod
    def tearDownClass(cls):pygame.quit()
    def setUp(self):
        self.islands=[pygame.Rect(v) for v in ISLANDS]
        self.motion=MovingIslands(self.islands)
        self.player=pygame.Rect(0,0,40,60)
        self.combat=LevelTwoCombat(ROOT,1.7,self.islands,enemy_indices=(1,4))
        self.orb=HealingOrb(ROOT,1.7)
        self.story=LevelThreeStory()

    def test_carrier_preserves_player_and_enemy_offsets_at_reversals(self):
        island=self.islands[1];enemy=self.combat.enemies[0]
        self.player.midbottom=(island.centerx,island.top)
        player_offset=self.player.x-island.x;enemy_offset=enemy.x-island.x
        for _ in range(600):
            self.motion.update(1/60,self.player,0,self.combat.enemies,self.orb)
            self.assertEqual(self.player.x-island.x,player_offset)
            self.assertEqual(enemy.x-island.x,enemy_offset)
            self.assertTrue(360<=island.x<=470)

    def test_airborne_player_is_not_carried(self):
        self.player.midbottom=self.islands[1].midtop
        before=self.player.x
        self.motion.update(.05,self.player,-5,self.combat.enemies,self.orb)
        self.assertEqual(self.player.x,before)

    def test_crystal_and_pickup_follow_moving_platform(self):
        island=self.islands[3];health=Health()
        self.player.midbottom=(island.left+190,island.top)
        self.orb.update(1,self.player,island,False,health)
        for _ in range(60):self.orb.update(1/60,self.player,island,False,health)
        self.assertTrue(self.orb.update(.016,self.player,island,True,health))
        offset=self.orb.position.x-island.x
        for _ in range(20):self.motion.update(1/60,self.player,0,self.combat.enemies,self.orb)
        self.assertAlmostEqual(self.orb.position.x-island.x,offset)
        self.assertEqual(health.current,100)
        self.assertFalse(self.orb.update(.016,self.player,island,True,health))

    def test_save_restores_all_carriers_and_enemy_attachment(self):
        self.player.midbottom=self.islands[0].midtop
        for _ in range(150):self.motion.update(1/60,self.player,0,self.combat.enemies)
        data=self.motion.snapshot()
        other=[pygame.Rect(v) for v in ISLANDS]
        restored=MovingIslands(other)
        enemies=LevelTwoCombat(ROOT,1.7,other,enemy_indices=(1,4)).enemies
        restored.restore(data,enemies)
        self.assertEqual(restored.snapshot(),data)
        for enemy in enemies:self.assertEqual(enemy.x,enemy.island.centerx+40)

    def test_combat_reaction_queue_and_urgent_warning_stay_playable(self):
        self.story.set_phase('gameplay')
        self.story.queue('l3_two_before');self.story.update(.01,self.orb)
        self.story.queue('l3_flying',urgent=True)
        self.assertEqual(self.story.reaction.scene,'l3_flying')
        self.assertFalse(self.story.blocked)
        self.story.update(10,self.orb)
        self.assertEqual(self.story.reaction.scene,'l3_two_before')
        restored=LevelThreeStory();restored.reset(self.story.snapshot())
        self.assertEqual(restored.reaction.scene,'l3_two_before')
        self.assertIn('l3_flying',restored.completed)

    def test_heal_followup_does_not_freeze_platforming(self):
        self.story.set_phase('gameplay');self.story.on_heal()
        self.assertFalse(self.story.blocked)
        self.orb.state='gone';self.story.update(.1,self.orb)
        self.assertEqual(self.story.reaction.scene,'l3_healing_after')

    def test_final_memory_has_hook_without_new_flashback(self):
        self.story.on_memory();self.assertTrue(self.story.next_memory_pending)
        self.story.update(.3,self.orb)
        self.assertEqual(self.story.dialogue.scene,'l3_memory_after')
        self.assertTrue(self.story.blocked)
        self.story.finish_scene('l3_memory_after');self.story.update(1.5,self.orb)
        self.assertEqual(self.story.phase,'chapter')
        restored=LevelThreeStory();restored.reset(self.story.snapshot())
        self.assertTrue(restored.next_memory_pending)

    def test_save_validation_for_six_islands(self):
        data=dict(version=1,level=3,x=80,y=430,velocity_y=0,on_ground=True,facing_right=True,
                  widths=[v[2] for v in ISLANDS],islands=[0,4,2,1,4,3],moving_x=380,moving_speed=2,
                  moving_islands=self.motion.snapshot(),duels=[2,2],hp=82)
        self.assertTrue(valid_save(data))
        data['moving_islands'][1]['x']=9999
        self.assertFalse(valid_save(data));self.assertFalse(valid_motion_save(data['moving_islands']))
