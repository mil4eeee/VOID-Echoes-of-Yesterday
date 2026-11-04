import os,sys,unittest
from pathlib import Path
from types import SimpleNamespace
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame
from narrative import LevelOneNarrative,InputEdges,DIALOGUES
from level_two import LevelTwoStory

class NarrativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init();pygame.font.init();pygame.display.set_mode((960,540))
    @classmethod
    def tearDownClass(cls):pygame.quit()
    def setUp(self):
        self.story=LevelOneNarrative()
        self.orb=SimpleNamespace(state='idle',near=False,collected=False)
        self.memory=SimpleNamespace(near=False,collected=False)
        self.shadow=SimpleNamespace(state='idle',hit_notice=0)
        self.islands=[pygame.Rect(*v) for v in [(0,490,300,20),(350,410,220,20),(620,330,220,20),(1370,200,200,20),(950,290,180,20)]]
        self.player=pygame.Rect(80,430,40,60)
    def press(self):
        self.story.input_used=False;self.story.advance()
    def finish(self,scene):
        for _ in range(2*len(DIALOGUES[scene])):self.press()
        self.assertIn(scene,self.story.completed)
    def poll(self):self.story.poll(self.player,self.islands,self.orb,self.memory,self.shadow)
    def test_opening_typewriter_two_press_advance(self):
        self.story.update(.75,self.orb)
        self.assertEqual(self.story.phase,'opening_fade')
        self.story.update(2.99,self.orb)
        self.assertIsNone(self.story.dialogue.scene)
        self.story.update(.02,self.orb)
        self.assertTrue(self.story.blocked)
        self.press();self.assertEqual(self.story.dialogue.index,0)
        self.press();self.assertEqual(self.story.dialogue.index,1)
        self.finish('opening');self.assertFalse(self.story.blocked)
    def test_repeated_physical_e_rejected(self):
        gate=InputEdges();event=pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e)
        self.assertTrue(gate.consume(event));self.assertFalse(gate.consume(event))
        gate.consume(pygame.event.Event(pygame.KEYUP,key=pygame.K_e));self.assertTrue(gate.consume(event))
    def test_second_landing_reaction_is_playable_once(self):
        self.story.set_phase('gameplay');self.player.midbottom=self.islands[1].midtop
        self.poll();self.assertEqual(self.story.reaction.scene,'second_platform')
        self.assertFalse(self.story.blocked)
        self.story.update(10,self.orb);self.poll();self.assertIsNone(self.story.reaction.scene)
    def test_shadow_approach_live_then_safe_aftermath(self):
        self.story.set_phase('gameplay');self.player.midbottom=self.islands[2].midtop
        self.shadow.state='warning';self.poll()
        self.assertEqual(self.story.reaction.scene,'shadow_before');self.assertFalse(self.story.blocked)
        self.shadow.state='fly';self.poll();self.assertFalse(self.story.blocked)
        self.shadow.state='finished';self.poll()
        self.assertEqual(self.story.dialogue.scene,'shadow_after');self.assertTrue(self.story.blocked)
    def test_moving_platform_reaction_is_playable(self):
        self.story.set_phase('gameplay');self.story.completed.add('shadow_after')
        self.player.midbottom=(830,330);self.poll()
        self.assertEqual(self.story.reaction.scene,'moving_platforms');self.assertFalse(self.story.blocked)
    def test_healing_waits_for_pickup(self):
        self.story.on_heal();self.orb.state='pickup';self.story.update(1,self.orb)
        self.assertEqual(self.story.phase,'heal_pickup')
        self.orb.state='gone';self.story.update(.01,self.orb)
        self.assertEqual(self.story.dialogue.scene,'healing_after')
    def test_memory_flashback_and_transition(self):
        self.story.on_memory();self.story.update(.3,self.orb)
        self.assertEqual(self.story.dialogue.scene,'memory_before')
        self.finish('memory_before');self.assertEqual(self.story.phase,'memory_fade')
        self.story.update(1.2,self.orb);self.assertEqual(self.story.phase,'flashback')
        observed=set()
        for _ in range(1000):
            observed.add(self.story.phase)
            self.story.update(.05,self.orb)
            if self.story.phase=='dialogue':break
        self.assertTrue({'flashback','flashback_gap','flashback_distort','black_cut'}<=observed)
        self.assertEqual(self.story.dialogue.scene,'memory_after')
        while self.story.phase in ('dialogue','dialogue_pause'):
            self.press()
            if self.story.phase=='dialogue_pause':self.story.update(.8,self.orb)
        self.assertEqual(self.story.phase,'exit_fade')
        self.story.update(1.19,self.orb);self.assertEqual(self.story.phase,'exit_fade')
        self.story.update(.02,self.orb);self.assertEqual(self.story.phase,'chapter')

    def test_completed_scenes_and_line_restore(self):
        self.story.completed.add('opening');self.story.begin('healing_intro');self.press();self.press()
        restored=LevelOneNarrative();restored.reset(self.story.snapshot())
        self.assertEqual(restored.dialogue.index,1);self.assertFalse(restored.begin('opening'))
    def test_level_two_healing_unlock_survives_save(self):
        story=LevelTwoStory();self.assertFalse(story.flying_cleared)
        self.shadow.state='fly';story.poll(None,None,None,None,self.shadow);self.assertFalse(story.flying_cleared)
        self.shadow.state='finished';story.poll(None,None,None,None,self.shadow);self.assertTrue(story.flying_cleared)
        restored=LevelTwoStory();restored.reset(story.snapshot());self.assertTrue(restored.flying_cleared)
    def test_all_lines_fit_and_render(self):
        for scene,lines in DIALOGUES.items():
            for index,(_,line) in enumerate(lines):
                self.story.dialogue.start(scene,index);self.story.dialogue.reveal=1000
                self.assertLessEqual(len(self.story.dialogue.wrapped(line,848)),2)
                self.story.dialogue.draw(pygame.display.get_surface())
