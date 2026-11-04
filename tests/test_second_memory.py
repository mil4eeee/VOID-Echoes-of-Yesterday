import os,sys,unittest
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame
from level_two import LevelTwoStory,SECOND_MEMORY_LINES
from narrative import DIALOGUES
from level_three import LEVEL_THREE_LINES


class SecondMemoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init();pygame.font.init();pygame.display.set_mode((960,540))
    @classmethod
    def tearDownClass(cls):pygame.quit()

    def setUp(self):self.story=LevelTwoStory()

    def press(self):
        self.story.input_used=False;self.story.advance()

    def finish(self,scene):
        self.assertEqual(self.story.dialogue.scene,scene)
        for _ in range(60):
            if self.story.phase=='dialogue_pause':self.story.update(1,None)
            if scene in self.story.completed:break
            self.press()
        self.assertIn(scene,self.story.completed)

    def test_entire_memory_requires_key_presses_before_level_three(self):
        self.story.on_memory();self.story.update(.3,None)
        self.assertEqual(self.story.dialogue.scene,'l2_memory_before')
        self.story.update(120,None)
        self.assertEqual(self.story.dialogue.index,0)
        self.finish('l2_memory_before');self.assertEqual(self.story.phase,'memory_fade')
        self.story.update(1.2,None);self.assertEqual(self.story.dialogue.scene,'l2_confrontation')
        self.story.update(120,None);self.assertEqual(self.story.dialogue.index,0)
        self.finish('l2_confrontation');self.assertEqual(self.story.phase,'black_cut')
        self.story.update(.65,None);self.assertEqual(self.story.dialogue.scene,'l2_memory_after')
        self.story.update(120,None);self.assertEqual(self.story.dialogue.index,0)
        self.finish('l2_memory_after');self.assertEqual(self.story.phase,'exit_fade')
        self.story.update(.79,None);self.assertNotEqual(self.story.phase,'chapter')
        self.story.update(.02,None);self.assertEqual(self.story.phase,'chapter')
        self.assertFalse(self.story.second_memory_pending)

    def test_repeated_collection_does_not_restart_active_or_completed_memory(self):
        self.story.on_memory();self.story.update(.3,None)
        self.press();self.press()
        index=self.story.dialogue.index
        self.story.on_memory();self.assertEqual(self.story.dialogue.index,index)
        self.story.completed.add('l2_memory_after');self.story.second_memory_pending=False
        self.story.set_phase('chapter');self.story.on_memory()
        self.assertEqual(self.story.phase,'chapter')

    def test_save_restores_exact_memory_line_and_typing_progress(self):
        self.story.second_memory_pending=True;self.story.begin('l2_confrontation')
        self.story.dialogue.index=8;self.story.dialogue.reveal=7
        restored=LevelTwoStory();restored.reset(self.story.snapshot(),memory=True)
        self.assertEqual(restored.dialogue.scene,'l2_confrontation')
        self.assertEqual(restored.dialogue.index,8);self.assertEqual(restored.dialogue.reveal,7)
        restored.update(60,None);self.assertEqual(restored.dialogue.index,8)

    def test_legacy_level_two_completion_waits_for_new_flashback(self):
        self.story.reset({'version':4,'phase':'chapter','completed':[],'second_memory_pending':True},memory=True)
        self.assertEqual(self.story.phase,'gold_flash')
        self.story.update(.3,None);self.assertEqual(self.story.dialogue.scene,'l2_memory_before')

    def test_speakers_cutoff_and_arrival_preserve_mystery(self):
        self.assertEqual({speaker for speaker,_ in SECOND_MEMORY_LINES['l2_confrontation']},{'Meadow (Past)','Noatak'})
        self.assertEqual(SECOND_MEMORY_LINES['l2_confrontation'][-1],('Noatak','From the truth—'))
        self.assertEqual(LEVEL_THREE_LINES['l3_arrival'][-1],'But I have to keep going.')
        self.assertEqual(len(SECOND_MEMORY_LINES['l2_confrontation']),15)

    def test_red_tint_is_removed_in_present(self):
        screen=pygame.display.get_surface()
        self.story.begin('l2_confrontation');self.story.draw(screen)
        self.assertEqual(tuple(screen.get_at((0,0)))[:3],(16,2,3))
        self.story.begin('l2_memory_after');self.story.draw(screen)
        self.assertEqual(tuple(screen.get_at((0,0)))[:3],(0,0,0))
        for scene,lines in SECOND_MEMORY_LINES.items():
            for i,(_,line) in enumerate(lines):
                self.story.dialogue.start(scene,i);self.story.dialogue.reveal=1000
                self.assertLessEqual(len(self.story.dialogue.wrapped(line,848)),2)
                self.story.draw(screen)
