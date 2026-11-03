"""Level 1 dialogue, one-time story triggers and silent chapter transitions."""
import math
import pygame


DIALOGUES = {
    'opening': [('MEADOW', line) for line in [
        'Ugh... my head.', 'Where... am I?',
        "This isn't right. I don't recognize any of this.", 'What is this place?']],
    'healing_intro': [('MEADOW', line) for line in [
        'Wait... I know what that is.', 'A healing crystal.', 'How do I know that...?']],
    'healing_after': [('MEADOW', line) for line in [
        "Huh... that's better.", 'At least I remember something.']],
    'shadow_before': [('MEADOW', line) for line in [
        'What was that...?', 'WOAH—!', 'Okay, definitely not friendly!', 'Stay back!']],
    'shadow_after': [('MEADOW', line) for line in [
        'Great. A forest full of things trying to kill me.', 'I need to get out of here.']],
    'memory_intro': [('MEADOW', line) for line in [
        'Another crystal...?', "No. This one's different.",
        "Why does it feel like it's calling me?"]],
    'flashback': [('UNKNOWN BOY', "Come on, Meadow! You're too slow!"),
                  ('YOUNG MEADOW', 'Hey! Wait for me!')],
    'memory_after': [('MEADOW', line) for line in [
        'That... was me.', 'And that boy...', "Why can't I remember his face?"]],
    'ending': [('MEADOW', line) for line in [
        "Those weren't just visions...", 'They were memories.',
        "If there's more of them out there...", 'Then I have to keep going.']],
}


class InputEdges:
    """One action per physical E/Enter press, including across UI state changes."""
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
    TYPEWRITER=False  # Enable if desired; Enter first reveals a typing line.
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

    def draw(self,screen,flashback=False):
        speaker,text=DIALOGUES[self.scene][self.index]
        if self.TYPEWRITER:
            text=text[:int(self.reveal)]
        width,height=screen.get_size()
        if flashback:
            screen.fill((11,12,23))
            label=self.small.render('A MEMORY',True,(189,163,106))
            screen.blit(label,label.get_rect(center=(width//2,100)))
            name=self.name_font.render(speaker,True,(245,213,151))
            screen.blit(name,name.get_rect(center=(width//2,195)))
            for i,line in enumerate(self.wrapped(text,width-120)):
                image=self.body.render(line,True,(241,237,225))
                screen.blit(image,image.get_rect(center=(width//2,250+i*34)))
            hint=self.small.render('ENTER  —  Continue',True,(192,197,210))
            screen.blit(hint,hint.get_rect(center=(width//2,height-55)))
            return
        panel=pygame.Surface((width-60,148),pygame.SRCALPHA)
        panel.fill((8,17,30,235))
        pygame.draw.rect(panel,(166,150,110),panel.get_rect(),1,border_radius=8)
        panel.blit(self.name_font.render(speaker,True,(244,215,151)),(24,15))
        for i,line in enumerate(self.wrapped(text,width-112)):
            panel.blit(self.body.render(line,True,(242,242,235)),(24,45+i*31))
        hint=self.small.render('ENTER  —  Continue',True,(193,210,223))
        panel.blit(hint,(panel.get_width()-hint.get_width()-24,120))
        screen.blit(panel,(30,height-166))


class LevelOneNarrative:
    PHASES={'opening_fade','gameplay','dialogue','heal_pickup','gold_flash',
            'flashback','forest_fade','exit_fade','chapter','shadow_tutorial'}

    def __init__(self):
        self.dialogue=DialogueManager()
        self.title=pygame.font.SysFont('Georgia',31)
        self.small=pygame.font.SysFont('Segoe UI',19)
        self.reset()

    def reset(self,data=None,*,legacy=False,healed=False,memory=False):
        self.completed=set()
        self.phase='opening_fade'
        self.time=0.0
        self.shadow_resolved=False
        self.dirty=False
        self.restart_tutorial=False
        self.input_used=False
        self.dialogue.scene=None
        if isinstance(data,dict):
            completed=data.get('completed',[])
            self.completed={name for name in completed if isinstance(name,str) and name in DIALOGUES} if isinstance(completed,list) else set()
            phase=data.get('phase','gameplay')
            self.phase=phase if isinstance(phase,str) and phase in self.PHASES else 'gameplay'
            self.shadow_resolved=data.get('shadow_resolved') is True
            value=data.get('time',0)
            self.time=max(0,min(2,float(value))) if type(value) in (int,float) and math.isfinite(value) else 0.0
            if self.phase in ('dialogue','flashback','shadow_tutorial'):
                scene=data.get('scene')
                if isinstance(scene,str) and scene in DIALOGUES:
                    index=data.get('line',0)
                    self.dialogue.start(scene,index if type(index) is int else 0)
                else:
                    self.phase='gameplay'
        elif legacy:
            # Existing players keep their progress; do not replay the opening mid-level.
            self.completed.add('opening')
            self.phase='gameplay'
            if healed:
                self.completed.update(('healing_intro','healing_after'))
            if memory:
                self.completed.update(('memory_intro','flashback'))
                self.phase='forest_fade'

    @property
    def blocked(self):
        return self.phase!='gameplay'

    @property
    def portal_ready(self):
        return 'ending' in self.completed

    def snapshot(self):
        return {'completed':sorted(self.completed),'phase':self.phase,'time':self.time,
                'scene':self.dialogue.scene,'line':self.dialogue.index,
                'shadow_resolved':self.shadow_resolved}

    def begin(self,scene):
        if scene in self.completed:
            return False
        self.dialogue.start(scene)
        self.phase='flashback' if scene=='flashback' else 'dialogue'
        self.time=0.0
        self.dirty=True
        return True

    def set_phase(self,phase):
        self.phase=phase;self.time=0.0;self.dirty=True

    def advance(self):
        if self.input_used or self.phase not in ('dialogue','flashback'):
            return
        self.input_used=True
        self.dirty=True
        previous_index = self.dialogue.index
        if not self.dialogue.advance():
            if self.dialogue.scene == 'shadow_before' and previous_index == 0 and self.dialogue.index == 1:
                self.set_phase('shadow_tutorial')
            return
        scene=self.dialogue.scene
        self.completed.add(scene)
        if scene=='flashback':
            self.set_phase('forest_fade')
        elif scene=='memory_after':
            self.begin('ending')
        else:
            self.set_phase('gameplay')
            if scene=='opening':
                self.restart_tutorial=True

    def update(self,dt,orb):
        self.time+=dt
        self.dialogue.update(dt)
        if self.phase=='opening_fade' and self.time>=1.0:
            self.begin('opening')
        elif self.phase=='heal_pickup' and orb.state=='gone':
            self.begin('healing_after')
        elif self.phase=='gold_flash' and self.time>=.5:
            self.begin('flashback')
        elif self.phase=='forest_fade' and self.time>=.8:
            self.begin('memory_after')
        elif self.phase=='exit_fade' and self.time>=1.0:
            # No Level 2 exists in this project yet: use the requested chapter placeholder.
            self.set_phase('chapter')

    @staticmethod
    def supported(player,islands):
        return any(player.bottom==p.top and player.right>p.left and player.left<p.right for p in islands)

    def poll(self,player,islands,orb,memory,shadow):
        if self.blocked:
            return
        if shadow.state in ('finished','dissipate') or shadow.hit_notice>0:
            self.shadow_resolved=True
        grounded=self.supported(player,islands)
        if shadow.state=='warning' and 'shadow_before' not in self.completed:
            self.begin('shadow_before')
        elif self.shadow_resolved and grounded and 'shadow_after' not in self.completed:
            self.begin('shadow_after')
        elif grounded and orb.near and not orb.collected and 'healing_intro' not in self.completed:
            self.begin('healing_intro')
        elif grounded and memory.near and not memory.collected and 'memory_intro' not in self.completed:
            self.begin('memory_intro')

    def practice_crouch(self, crouch):
        # Keep the enemy and world frozen until the player has tried the dodge.
        if self.phase == 'shadow_tutorial' and crouch.state == 'hold':
            self.set_phase('dialogue')  # Resume at WOAH, after the instruction.

    def on_heal(self):
        self.set_phase('heal_pickup')

    def on_memory(self):
        self.set_phase('gold_flash')

    def portal_position(self,island):
        return pygame.Vector2(island.right-36,island.top-42)

    def portal_near(self,player,island):
        return self.portal_ready and pygame.Vector2(player.centerx,player.bottom-30).distance_to(self.portal_position(island))<=54

    def draw_portal(self,screen,island,camera_x,camera_y,zoom,player):
        if not self.portal_ready:
            return
        pos=self.portal_position(island)
        center=(round((pos.x-camera_x)*zoom),round((pos.y-camera_y)*zoom))
        surface=pygame.Surface((round(80*zoom),round(105*zoom)),pygame.SRCALPHA)
        mid=(surface.get_width()//2,surface.get_height()//2)
        pulse=1+.035*math.sin(pygame.time.get_ticks()/350)
        for radius,alpha in [(35,12),(31,22),(27,40),(23,75)]:
            rect=pygame.Rect(0,0,round(radius*2*zoom*pulse),round(84*zoom*pulse))
            rect.center=mid
            pygame.draw.ellipse(surface,(124,183,244,alpha),rect)
        rim=pygame.Rect(0,0,round(43*zoom),round(82*zoom));rim.center=mid
        pygame.draw.ellipse(surface,(245,214,146,235),rim,3)
        screen.blit(surface,surface.get_rect(center=center))
        if not self.blocked and self.portal_near(player,island):
            label=self.small.render('Press E to enter',True,(255,233,173))
            rect=label.get_rect(center=(center[0],center[1]-round(55*zoom)))
            rect.clamp_ip(screen.get_rect().inflate(-16,-16))
            pygame.draw.rect(screen,(11,22,34),rect.inflate(20,12),border_radius=5)
            screen.blit(label,rect)

    def draw(self,screen):
        if self.phase in ('dialogue','flashback'):
            self.dialogue.draw(screen,self.phase=='flashback')
        elif self.phase in ('opening_fade','forest_fade','exit_fade','gold_flash'):
            color=(0,0,0)
            if self.phase=='gold_flash':
                color=(255,218,130)
                alpha=round(245*min(1,self.time/.16))
            elif self.phase=='exit_fade':
                alpha=round(255*min(1,self.time))
            else:
                duration=.8 if self.phase=='forest_fade' else 1.0
                alpha=round(255*(1-min(1,self.time/duration)))
            veil=pygame.Surface(screen.get_size());veil.fill(color);veil.set_alpha(alpha)
            screen.blit(veil,(0,0))
        elif self.phase=='chapter':
            screen.fill((7,11,22))
            for text,font,y,color in [
                ('CHAPTER II — THE FORGOTTEN RUINS',self.title,200,(242,217,164)),
                ('To be continued',self.small,265,(213,222,236)),
                ('ENTER / ESC — Return to main menu',self.small,380,(191,208,220))]:
                image=font.render(text,True,color)
                screen.blit(image,image.get_rect(center=(screen.get_width()//2,y)))
            pygame.draw.rect(screen,(142,151,167),self.return_button(screen.get_size()),1,border_radius=6)

    @staticmethod
    def return_button(size):
        return pygame.Rect(size[0]//2-220,352,440,55)
