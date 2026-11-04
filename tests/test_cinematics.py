import os,sys,unittest
from pathlib import Path
from types import SimpleNamespace
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame
from narrative import ScreenFade,LevelOneNarrative
from level_two import LevelTwoStory,LevelTwoCombat,ISLANDS,MOVING
from health_healing import Health


class CinematicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init();pygame.font.init();pygame.display.set_mode((960,540))
    @classmethod
    def tearDownClass(cls):pygame.quit()

    def test_fade_has_black_endpoints_and_halfway_alpha(self):
        fade=ScreenFade();screen=pygame.display.get_surface()
        for time,expected in [(0,255),(1.5,128),(3,0)]:
            fade.draw(screen,time,3,fade_in=True)
            self.assertAlmostEqual(fade.surface.get_alpha(),expected,delta=1)

    def test_flashback_and_pause_restore_without_replaying_opening(self):
        story=LevelOneNarrative();story.completed.add('opening')
        story.dialogue.start('flashback',3);story.set_phase('flashback_gap')
        restored=LevelOneNarrative();restored.reset(story.snapshot(),memory=True)
        self.assertEqual(restored.phase,'flashback_gap')
        self.assertEqual(restored.dialogue.index,3)
        self.assertIn('opening',restored.completed)
        restored.update(.7,SimpleNamespace(state='gone'))
        self.assertEqual(restored.phase,'flashback')

    def test_pre_fight_dialogue_gates_combat(self):
        islands=[pygame.Rect(v) for v in ISLANDS]+[pygame.Rect(MOVING)]
        combat=LevelTwoCombat(ROOT,1.7,islands)
        story=LevelTwoStory();story.set_phase('gameplay')
        player=pygame.Rect(0,0,40,60);player.midbottom=islands[1].midtop
        health=Health();shadow=SimpleNamespace(state='idle',hit_notice=0)
        obj=SimpleNamespace(near=False,collected=False)
        for _ in range(120):combat.update(1/60,player,True,False,health,enabled=(False,False))
        self.assertEqual(combat.enemies[0].state,'idle');self.assertEqual(health.current,75)
        story.poll(player,islands,obj,obj,shadow,combat)
        self.assertEqual(story.dialogue.scene,'l2_duel_before');self.assertTrue(story.blocked)

    def test_flying_reaction_never_blocks_active_encounter(self):
        islands=[pygame.Rect(v) for v in ISLANDS]+[pygame.Rect(MOVING)]
        combat=LevelTwoCombat(ROOT,1.7,islands)
        story=LevelTwoStory();story.set_phase('gameplay')
        player=pygame.Rect(0,0,40,60);player.midbottom=islands[2].midtop
        obj=SimpleNamespace(near=False,collected=False)
        story.poll(player,islands,obj,obj,SimpleNamespace(state='fly'),combat)
        self.assertEqual(story.reaction.scene,'l2_flying');self.assertFalse(story.blocked)

    def test_second_memory_prompt_waits_for_its_dialogue(self):
        story=LevelTwoStory()
        self.assertNotIn('memory_intro',story.completed)
        story.finish_scene('l2_memory_intro')
        self.assertIn('memory_intro',story.completed)
