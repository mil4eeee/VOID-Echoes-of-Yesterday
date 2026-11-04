"""Handle Level 1 dialogue, reactions, and screen fades."""
import math
import pygame

DIALOGUES = {'opening': [('MEADOW', 'Ughhh... my head...'),
             ('MEADOW', 'Where... am I? What is this place?'),
             ('MEADOW', 'Come on, Meadow... think. How did I get here?'),
             ('MEADOW', 'Nothing. Great. Just great.')],
 'healing_intro': [('MEADOW', "Huh? What's that glowing over there?"),
                   ('MEADOW', 'Wait... a healing crystal? I recognize that!'),
                   ('MEADOW', "But... how? Why can't I remember anything else?")],
 'healing_after': [('MEADOW', 'Ahh... much better. Guess I needed that.'),
                   ('MEADOW',
                    "Alright... I have no idea what's going on, but I can't stay here forever."),
                   ('MEADOW', "Let's see where this leads.")],
 'second_platform': [('MEADOW', 'Well... at least these things seem stable.')],
 'shadow_before': [('MEADOW', 'WOAH! WHAT THE—?!')],
 'shadow_after': [('MEADOW', 'What the hell was THAT?!'),
                  ('MEADOW', 'Was that some kind of... shadow spirit?'),
                  ('MEADOW',
                   'Okay... floating islands, creepy shadows trying to kill me... anything '
                   'else?!')],
 'moving_platforms': [('MEADOW', 'Moving platforms. Of course. Why would anything be easy?'),
                      ('MEADOW', "Alright, Meadow. Focus. You've got this.")],
 'memory_intro': [('MEADOW', "Wait... what's that?"),
                  ('MEADOW', "It's... glowing. But it's different from the crystal."),
                  ('MEADOW', 'Why does it feel so... familiar?'),
                  ('MEADOW', "Something's telling me I need to touch it...")],
 'memory_after': [('MEADOW', 'Noatak...?'),
                  ('MEADOW', 'Why... why do I know that name?'),
                  ('MEADOW', 'Who are you?'),
                  ('MEADOW', 'And what are you sorry for...?'),
                  ('MEADOW', 'What the hell happened to me?')],
 'memory_before': [('MEADOW', "Wait... what's happening?"), ('MEADOW', 'My head...!')],
 'flashback': [('UNKNOWN VOICE', 'Meadow!'),
               ('MEADOW', 'Huh...?'),
               ('UNKNOWN VOICE', 'Meadow, look at me!'),
               ('UNKNOWN VOICE', 'You have to trust me.'),
               ('MEADOW', 'Wait... I know that voice...'),
               ('UNKNOWN VOICE', "I'm sorry...")],
 'l2_arrival': [('MEADOW', 'Noatak...'),
                ('MEADOW', 'Why does that name feel so familiar?'),
                ('MEADOW', 'Ugh. The more I try to remember, the worse my head gets.'),
                ('MEADOW', 'Alright... one thing at a time.'),
                ('MEADOW', 'I need to find more of those fragments.')],
 'l2_duel_before': [('MEADOW', 'Oh, great. Another one of you.'),
                    ('MEADOW', "You're not going to make this easy, are you?")],
 'l2_duel_after': [('MEADOW', "Huh. That wasn't so bad."),
                   ('MEADOW', 'Guess I still remember how to fight.'),
                   ('MEADOW', 'Funny how that works...')],
 'l2_moving': [('MEADOW', 'Another moving platform...'),
               ('MEADOW', 'Alright. Just time the jump.')],
 'l2_two_before': [('MEADOW', "Wait... there's two of them?"),
                   ('MEADOW', "Oh, you've got to be kidding me.")],
 'l2_flying': [('MEADOW', 'WOAH! Not again!')],
 'l2_two_after': [('MEADOW', 'Okay... that was a little too close.'),
                  ('MEADOW', 'These things just keep coming.'),
                  ('MEADOW', 'What even ARE they?')],
 'l2_memory_intro': [('MEADOW', 'Wait...'),
                     ('MEADOW', 'Another fragment?'),
                     ('MEADOW', 'So there are more of these things...'),
                     ('MEADOW', 'If the last one showed me Noatak...'),
                     ('MEADOW', 'Maybe this one will finally give me some answers.')]}

# Pause briefly before these dialogue lines.
DIALOGUE_PAUSES={('memory_after',4):.75,('l2_duel_after',2):.65,('l2_memory_intro',4):.65}


class ScreenFade:
    """Fade the screen using a black overlay."""
    def __init__(self):
        self.surface=None

    def draw(self,screen,elapsed,duration,fade_in=False):
        if self.surface is None or self.surface.get_size()!=screen.get_size():
            self.surface=pygame.Surface(screen.get_size())
            self.surface.fill((0,0,0))
        progress=max(0,min(1,elapsed/max(.001,duration)))
        self.surface.set_alpha(round(255*((1-progress) if fade_in else progress)))
        screen.blit(self.surface,(0,0))


class InputEdges:
    """Allow only one action each time E or Enter is pressed."""
    def __init__(self):
        self.held=set()

    def consume(self,event):
        if event.type==pygame.KEYUP:
            self.held.discard(event.key)
        elif event.type==pygame.WINDOWFOCUSLOST:
            self.held.clear()
        elif event.type==pygame.KEYDOWN:
            if getattr(event,'repeat',False) or event.key in self.held:
                return False
            self.held.add(event.key)
            return True
        return False


class DialogueManager:
    TYPEWRITER=True  # Press E to reveal the text, then again for the next line.
    LETTERS_PER_SECOND=45

    def __init__(self):
        self.body=pygame.font.SysFont('Segoe UI',23)
        self.name_font=pygame.font.SysFont('Segoe UI',17,bold=True)
        self.small=pygame.font.SysFont('Segoe UI',15)
        self.scene=None
        self.index=0
        self.reveal=0.0

    def start(self,scene,index=0):
        self.scene=scene
        self.index=max(0,min(index,len(DIALOGUES[scene])-1))
        self.reveal=0.0

    def update(self,dt):
        self.reveal+=dt*self.LETTERS_PER_SECOND

    def advance(self):
        if self.scene is None:
            return False
        text=DIALOGUES[self.scene][self.index][1]
        if self.TYPEWRITER and self.reveal<len(text):
            self.reveal=float(len(text))
            return False
        self.index+=1
        self.reveal=0.0
        return self.index>=len(DIALOGUES[self.scene])

    def wrapped(self,text,width):
        lines=[]
        line=''
        for word in text.split():
            candidate=f'{line} {word}'.strip()
            if line and self.body.size(candidate)[0]>width:
                lines.append(line);line=word
            else:
                line=candidate
        return lines+[line]

    def draw(self,screen,reaction=False):
        speaker,text=DIALOGUES[self.scene][self.index]
        if self.TYPEWRITER:
            text=text[:int(self.reveal)]
        width,height=screen.get_size()
        panel=pygame.Surface((width-60,132),pygame.SRCALPHA)
        panel.fill((8,17,30,235))
        pygame.draw.rect(panel,(166,150,110),panel.get_rect(),1,border_radius=8)
        panel.blit(self.name_font.render(speaker,True,(244,215,151)),(24,15))
        for i,line in enumerate(self.wrapped(text,width-112)):
            panel.blit(self.body.render(line,True,(242,242,235)),(24,45+i*31))
        hint=self.small.render('' if reaction else 'E  —  Reveal / Continue',True,(193,210,223))
        panel.blit(hint,(panel.get_width()-hint.get_width()-24,108))
        screen.blit(panel,(30,height-146))


class LevelOneNarrative:
    PHASES={'opening_hold','opening_fade','gameplay','dialogue','dialogue_pause','heal_pickup',
            'gold_flash','memory_fade','flashback','flashback_gap','flashback_distort','black_cut','exit_fade','chapter'}
    REACTIONS={'second_platform','shadow_before','moving_platforms','l2_moving','l2_flying'}

    def __init__(self):
        self.fade=ScreenFade()
        self.dialogue=DialogueManager()
        self.reaction=DialogueManager()
        self.title=pygame.font.SysFont('Georgia',31)
        self.small=pygame.font.SysFont('Segoe UI',19)
        self.reset()

    def reset(self,data=None,*,legacy=False,healed=False,memory=False):
        self.completed=set()
        self.phase='opening_hold'
        self.time=0.0
        self.shadow_resolved=False
        self.dirty=False
        self.restart_tutorial=False
        self.input_used=False
        self.dialogue.scene=None
        self.reaction.scene=None
        if isinstance(data,dict):
            completed=data.get('completed',[])
            self.completed={s for s in completed if isinstance(s,str) and s in DIALOGUES} if isinstance(completed,list) else set()
            phase=data.get('phase','gameplay')
            self.phase=phase if isinstance(phase,str) and phase in self.PHASES else 'gameplay'
            self.shadow_resolved=data.get('shadow_resolved') is True
            value=data.get('time',0)
            self.time=max(0,min(30,float(value))) if type(value) in (int,float) and math.isfinite(value) else 0.0
            scene=data.get('scene')
            if self.phase in ('dialogue','dialogue_pause','flashback','flashback_gap','flashback_distort') and isinstance(scene,str) and scene in DIALOGUES and scene not in self.REACTIONS:
                self.dialogue.start(scene,data.get('line',0) if type(data.get('line')) is int else 0)
            elif self.phase in ('dialogue','dialogue_pause','flashback','flashback_gap','flashback_distort'):
                self.phase='gameplay'
            if self.phase=='exit_fade' and scene=='memory_after':
                self.dialogue.start('memory_after',len(DIALOGUES['memory_after'])-1)
            if self.dialogue.scene:
                reveal=data.get('reveal',0)
                if type(reveal) in (int,float) and math.isfinite(reveal):
                    self.dialogue.reveal=max(0,min(float(reveal),len(DIALOGUES[self.dialogue.scene][self.dialogue.index][1])))
            # Update older saves to use the current story transition.
            if memory and data.get('version',0)<3 and (scene in ('flashback','ending') or phase=='forest_fade'):
                self.begin('memory_after')
            if memory and self.phase=='gameplay' and 'memory_after' in self.completed:
                self.set_phase('exit_fade')
        elif legacy:
            self.completed.add('opening');self.phase='gameplay'
            if healed:self.completed.update(('healing_intro','healing_after'))
            if memory:self.begin('memory_after')

    @property
    def blocked(self):
        return self.phase!='gameplay'

    @property
    def portal_ready(self):
        return False

    def snapshot(self):
        return {'version':3,'completed':sorted(self.completed),'phase':self.phase,'time':self.time,
                'scene':self.dialogue.scene,'line':self.dialogue.index,'reveal':self.dialogue.reveal,
                'shadow_resolved':self.shadow_resolved}

    def begin(self,scene):
        if scene in self.completed:return False
        self.reaction.scene=None
        self.dialogue.start(scene);self.set_phase('dialogue')
        return True

    def react(self,scene):
        if scene in self.completed:return
        self.completed.add(scene)
        self.reaction.start(scene)
        self.dirty=True

    def set_phase(self,phase):
        self.phase=phase;self.time=0.0;self.dirty=True

    def advance(self):
        if self.input_used or self.phase not in ('dialogue','flashback'):return
        self.input_used=True;self.dirty=True
        if self.phase=='flashback':
            self.advance_flashback()
            return
        previous=self.dialogue.index
        if not self.dialogue.advance():
            if previous!=self.dialogue.index and (self.dialogue.scene,self.dialogue.index) in DIALOGUE_PAUSES:
                self.set_phase('dialogue_pause')
            return
        scene=self.dialogue.scene
        self.completed.add(scene)
        self.finish_scene(scene)

    def finish_scene(self,scene):
        if scene=='memory_before':self.set_phase('memory_fade')
        elif scene=='memory_after':self.set_phase('exit_fade')
        else:self.set_phase('gameplay')
        if scene=='opening':self.restart_tutorial=True

    def advance_flashback(self):
        previous=self.dialogue.index
        if self.dialogue.advance():
            self.completed.add('flashback')
            self.set_phase('black_cut')
        elif self.dialogue.index!=previous:
            phase={3:'flashback_gap',5:'flashback_distort'}.get(self.dialogue.index,'flashback')
            self.set_phase(phase)

    def update_text(self,dt):
        if self.phase in ('dialogue','flashback'):self.dialogue.update(dt)
        if self.phase=='dialogue_pause' and self.time>=DIALOGUE_PAUSES.get((self.dialogue.scene,self.dialogue.index),.65):
            self.set_phase('dialogue')
        if self.phase=='gameplay' and self.reaction.scene:
            self.reaction.update(dt)
            text=DIALOGUES[self.reaction.scene][self.reaction.index][1]
            if self.reaction.reveal>=len(text)+2.8*self.reaction.LETTERS_PER_SECOND:
                if self.reaction.advance():self.reaction.scene=None

    def update(self,dt,orb):
        self.time+=dt
        self.update_text(dt)
        if self.phase=='opening_hold' and self.time>=.75:self.set_phase('opening_fade')
        elif self.phase=='opening_fade' and self.time>=3:self.begin('opening')
        elif self.phase=='heal_pickup' and orb.state=='gone':self.begin('healing_after')
        elif self.phase=='gold_flash' and self.time>=.3:self.begin('memory_before')
        elif self.phase=='memory_fade' and self.time>=1.2:
            self.dialogue.start('flashback');self.set_phase('flashback')
        elif self.phase=='flashback':
            text=DIALOGUES['flashback'][self.dialogue.index][1]
            if self.time>=len(text)/self.dialogue.LETTERS_PER_SECOND+2.2:
                self.advance_flashback()
        elif self.phase=='flashback_gap' and self.time>=.65:self.set_phase('flashback')
        elif self.phase=='flashback_distort' and self.time>=.6:self.set_phase('flashback')
        elif self.phase=='black_cut' and self.time>=.85:self.begin('memory_after')
        elif self.phase=='exit_fade' and self.time>=1.2:self.set_phase('chapter')

    @staticmethod
    def supported(player,islands):
        return any(player.bottom==p.top and player.right>p.left and player.left<p.right for p in islands)

    def poll(self,player,islands,orb,memory,shadow):
        if self.blocked:return
        if shadow.state in ('finished','dissipate') or shadow.hit_notice>0:self.shadow_resolved=True
        grounded=self.supported(player,islands)
        if shadow.state in ('warning','fly'):
            self.react('shadow_before')
        elif self.shadow_resolved and grounded and 'shadow_after' not in self.completed:
            self.begin('shadow_after')
        elif grounded and orb.near and not orb.collected and 'healing_intro' not in self.completed:
            self.begin('healing_intro')
        elif grounded and memory.near and not memory.collected and 'memory_intro' not in self.completed:
            self.begin('memory_intro')
        elif self.supported(player,[islands[1]]):
            self.react('second_platform')
        elif ('shadow_after' in self.completed and 'moving_platforms' not in self.completed
              and player.centerx>=islands[2].right-90):
            self.react('moving_platforms')

    def on_heal(self):self.set_phase('heal_pickup')
    def on_memory(self):self.set_phase('gold_flash')
    def portal_near(self,*args):return False
    def draw_portal(self,*args):pass

    def draw(self,screen):
        memory_backdrop=(self.phase in ('flashback','flashback_gap','flashback_distort','black_cut')
                         or (self.dialogue.scene=='memory_after' and self.phase in ('dialogue','dialogue_pause','exit_fade')))
        if memory_backdrop:
            screen.fill((10,9,3) if self.phase!='black_cut' else (0,0,0))
        if self.phase=='dialogue':self.dialogue.draw(screen)
        elif self.phase=='gameplay' and self.reaction.scene:self.reaction.draw(screen,reaction=True)
        elif self.phase=='flashback':
            speaker,text=DIALOGUES['flashback'][self.dialogue.index]
            text=text[:int(self.dialogue.reveal)]
            width,height=screen.get_size()
            name=self.dialogue.name_font.render(speaker,True,(195,170,91))
            screen.blit(name,name.get_rect(center=(width//2,height//2-45)))
            for i,line in enumerate(self.dialogue.wrapped(text,width-120)):
                image=self.dialogue.body.render(line,True,(236,217,160))
                screen.blit(image,image.get_rect(center=(width//2,height//2+i*32)))
            hint=self.dialogue.small.render('E — Reveal / Continue',True,(136,128,98))
            screen.blit(hint,hint.get_rect(center=(width//2,height-45)))
        elif self.phase=='flashback_distort':
            for i in range(7):
                y=int(screen.get_height()*(i+1)/8)
                offset=round(15*math.sin(self.time*13+i))
                pygame.draw.line(screen,(42,35,9),(90+offset,y),(screen.get_width()-90+offset,y),1)
        elif self.phase=='opening_hold':screen.fill((0,0,0))
        elif self.phase=='opening_fade':self.fade.draw(screen,self.time,3,fade_in=True)
        elif self.phase in ('memory_fade','exit_fade'):self.fade.draw(screen,self.time,1.2)
        elif self.phase=='gold_flash':
            veil=pygame.Surface(screen.get_size());veil.fill((255,219,96))
            veil.set_alpha(round(240*max(0,1-self.time/.3)))
            screen.blit(veil,(0,0))

    @staticmethod
    def return_button(size):
        return pygame.Rect(size[0]//2-220,352,440,55)
