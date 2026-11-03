import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pygame
from narrative import LevelOneNarrative, DialogueManager, InputEdges, DIALOGUES
from memory_fragment import MemoryFragment


class NarrativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init();pygame.font.init();pygame.display.set_mode((960,540))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.story=LevelOneNarrative()
        self.orb=SimpleNamespace(state='idle',near=False,collected=False)

    def finish(self,scene):
        self.assertEqual(self.story.dialogue.scene,scene)
        for _ in DIALOGUES[scene]:
            self.story.input_used=False
            self.story.advance()
        self.assertIn(scene,self.story.completed)

    def test_opening_fade_and_exact_dialogue(self):
        self.assertTrue(self.story.blocked)
        self.story.update(.99,self.orb)
        self.assertEqual(self.story.phase,'opening_fade')
        self.story.update(.02,self.orb)
        self.assertEqual(DIALOGUES['opening'][0],('MEADOW','Ugh... my head.'))
        self.finish('opening')
        self.assertFalse(self.story.blocked)
        self.assertTrue(self.story.restart_tutorial)

    def test_physical_key_latch_and_one_line_per_frame(self):
        gate=InputEdges()
        down=pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN)
        up=pygame.event.Event(pygame.KEYUP,key=pygame.K_RETURN)
        self.assertTrue(gate.consume(down))
        self.assertFalse(gate.consume(down))
        gate.consume(up);self.assertTrue(gate.consume(down))
        self.assertFalse(gate.consume(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e,repeat=True)))
        self.story.begin('opening');self.story.advance();self.story.advance()
        self.assertEqual(self.story.dialogue.index,1)

    def test_pickup_waits_for_animation_before_dialogue(self):
        self.story.on_heal();self.orb.state='pickup'
        self.story.update(1,self.orb)
        self.assertEqual(self.story.phase,'heal_pickup')
        self.orb.state='gone';self.story.update(.01,self.orb)
        self.finish('healing_after')
        self.assertFalse(self.story.blocked)

    def test_crouch_instruction_precedes_woah_and_survives_continue(self):
        self.story.begin('shadow_before')
        self.story.advance()
        self.assertEqual(self.story.phase,'shadow_tutorial')
        self.assertTrue(self.story.blocked)
        self.story.input_used=False
        self.story.advance()  # Enter cannot skip the crouch practice.
        self.assertEqual(self.story.phase,'shadow_tutorial')
        restored=LevelOneNarrative()
        restored.reset(self.story.snapshot())
        self.assertEqual(restored.phase,'shadow_tutorial')
        restored.practice_crouch(SimpleNamespace(state='lowering'))
        self.assertEqual(restored.phase,'shadow_tutorial')
        restored.practice_crouch(SimpleNamespace(state='hold'))
        self.assertEqual(restored.phase,'dialogue')
        self.assertEqual(DIALOGUES[restored.dialogue.scene][restored.dialogue.index][1],'WOAH—!')

    def test_instruction_bubble_stays_inside_screen_at_edges(self):
        from instruction_ui import draw_instruction
        screen=pygame.display.get_surface()
        for anchor in [(0,0),(960,540),(200,200)]:
            box=draw_instruction(screen,self.story.small,['Press E to absorb','healing energy'],anchor)
            self.assertTrue(screen.get_rect().contains(box))

    def test_flashback_ending_portal_and_one_second_exit(self):
        self.story.on_memory();self.story.update(.49,self.orb)
        self.assertEqual(self.story.phase,'gold_flash')
        self.story.update(.02,self.orb)
        self.assertEqual(self.story.phase,'flashback')
        self.assertEqual([speaker for speaker,_ in DIALOGUES['flashback']],['UNKNOWN BOY','YOUNG MEADOW'])
        self.assertNotIn('Noah',str(DIALOGUES))
        self.finish('flashback')
        self.story.update(.81,self.orb);self.finish('memory_after');self.finish('ending')
        self.assertTrue(self.story.portal_ready)
        self.story.set_phase('exit_fade');self.story.update(.99,self.orb)
        self.assertEqual(self.story.phase,'exit_fade')
        self.story.update(.02,self.orb);self.assertEqual(self.story.phase,'chapter')

    def test_active_line_and_completed_triggers_restore(self):
        self.story.completed.add('opening');self.story.begin('healing_intro');self.story.advance()
        restored=LevelOneNarrative();restored.reset(self.story.snapshot())
        self.assertEqual(restored.dialogue.scene,'healing_intro')
        self.assertEqual(restored.dialogue.index,1)
        self.assertFalse(restored.begin('opening'))
        restored.reset({'completed':None,'phase':[]})
        self.assertEqual(restored.phase,'gameplay')

    def test_old_collected_memory_save_has_exit_path(self):
        self.story.reset(legacy=True,healed=True,memory=True)
        self.assertIn('opening',self.story.completed)
        self.story.update(.81,self.orb);self.finish('memory_after');self.finish('ending')
        self.assertTrue(self.story.portal_ready)

    def test_memory_requires_e_once_within_range(self):
        memory=MemoryFragment(ROOT,1.7)
        island=pygame.Rect(1370,200,200,20)
        player=pygame.Rect(1450,140,40,60)
        self.assertFalse(memory.update(.016,player,island))
        self.assertTrue(memory.near)
        self.assertTrue(memory.update(.016,player,island,True))
        self.assertFalse(memory.update(.016,player,island,True))
        self.assertEqual(memory.message_time,0)

    def test_ui_text_wraps_and_all_scenes_render(self):
        screen=pygame.display.get_surface()
        for scene,lines in DIALOGUES.items():
            for index,(_,text) in enumerate(lines):
                self.story.dialogue.start(scene,index)
                for line in self.story.dialogue.wrapped(text,848):
                    self.assertLessEqual(self.story.dialogue.body.size(line)[0],848)
                self.story.phase='flashback' if scene=='flashback' else 'dialogue'
                self.story.draw(screen)
        self.story.phase='chapter';self.story.draw(screen)


if __name__=='__main__':
    unittest.main()
