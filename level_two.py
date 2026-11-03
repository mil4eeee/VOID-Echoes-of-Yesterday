"""Chapter II layout and compact, reusable shadow duel encounters."""
import math
import pygame
from shadow_encounter import load_frames
from narrative import LevelOneNarrative
from instruction_ui import draw_instruction


# Four fixed islands and one moving bridge, in the order of the supplied sketch.
ISLANDS = [(0,490,300,20), (390,420,270,20),
           (1120,310,280,20), (1510,235,290,20)]
MOVING = (780,365,210,20)
MOVING_LIMITS = (710,900)
WORLD_WIDTH = 1840


class LevelTwoStory(LevelOneNarrative):
    """No invented story dialogue: title, gameplay, and a completion card."""
    def reset(self,data=None,**kwargs):
        super().reset()
        self.completed = {'opening','healing_intro','healing_after','memory_intro'}
        self.phase = 'level2_title'
        if isinstance(data,dict):
            phase=data.get('phase')
            if phase in ('level2_title','opening_fade','gameplay','gold_flash','chapter'):
                self.phase=phase

    @property
    def portal_ready(self):
        return False

    def poll(self,*args):
        pass

    def update(self,dt,orb):
        self.time+=dt
        if self.phase=='level2_title' and self.time>=2:
            self.set_phase('opening_fade')
        elif self.phase=='opening_fade' and self.time>=1:
            self.set_phase('gameplay')
        elif self.phase=='gold_flash' and self.time>=.65:
            self.set_phase('chapter')

    def draw(self,screen):
        if self.phase not in ('level2_title','chapter'):
            super().draw(screen)
            return
        screen.fill((7,11,22))
        lines=[('CHAPTER II — THE FORGOTTEN RUINS',self.title,195),
               ('Level 2 complete' if self.phase=='chapter' else 'The journey continues',self.small,260)]
        if self.phase=='chapter':
            lines.append(('ENTER / ESC — Return to main menu',self.small,380))
        for text,font,y in lines:
            image=font.render(text,True,(242,217,164))
            screen.blit(image,image.get_rect(center=(screen.get_width()//2,y)))
        if self.phase=='chapter':
            pygame.draw.rect(screen,(142,151,167),self.return_button(screen.get_size()),1,border_radius=6)


class DuelShadow:
    """Two animation types: hovering and a clearly telegraphed strike."""
    WINDUP=.85
    STRIKE=.22
    RECOVERY=1.1
    DAMAGE=20

    def __init__(self,frames,island,index):
        self.frames=frames
        self.island=island
        self.index=index
        self.hp=2
        self.state='idle'
        self.time=0.0
        self.x=island.centerx+40
        self.did_hit=False
        self.font=pygame.font.SysFont('Segoe UI',14,bold=True)

    @property
    def defeated(self):
        return self.hp<=0

    def reset_attack(self):
        self.state,self.time,self.did_hit='idle',0.0,False

    def update(self,dt,player):
        if self.defeated:
            return False
        self.time+=dt
        near=(abs(player.centerx-self.x)<105 and abs(player.bottom-self.island.top)<35)
        if self.state=='idle' and near:
            self.state,self.time='windup',0.0
        elif self.state=='windup' and self.time>=self.WINDUP:
            self.state,self.time,self.did_hit='strike',0.0,False
        elif self.state=='strike':
            if self.time>=self.STRIKE:
                self.state,self.time='recovery',0.0
            elif not self.did_hit and abs(player.centerx-self.x)<90 and abs(player.bottom-self.island.top)<35:
                self.did_hit=True
                return True
        elif self.state=='recovery' and self.time>=self.RECOVERY:
            self.reset_attack()
        return False

    def receive_attack(self,player,facing_right):
        delta=self.x-player.centerx
        if (not self.defeated and self.state=='recovery' and abs(delta)<=110
                and abs(player.bottom-self.island.top)<65
                and (abs(delta)<15 or (delta>0)==facing_right)):
            self.hp-=1
            self.reset_attack()
            return True
        return False

    def draw(self,screen,camera_x,camera_y,zoom):
        if self.defeated:
            return
        frame_set=self.frames['attack' if self.state in ('windup','strike') else 'idle']
        frame=frame_set[min(len(frame_set)-1,int(self.time*10)) if self.state in ('windup','strike')
                        else int(self.time*8)%len(frame_set)]
        center=(round((self.x-camera_x)*zoom),round((self.island.top-43-camera_y)*zoom))
        screen.blit(frame,frame.get_rect(center=center),special_flags=pygame.BLEND_PREMULTIPLIED)
        color=(255,115,100) if self.state in ('windup','strike') else (125,226,214)
        if self.state=='windup':
            # A ground ring announces a low sweep: jumping clears it.
            pygame.draw.ellipse(screen,color,(center[0]-90*zoom,round((self.island.top-camera_y)*zoom)-8,180*zoom,16),2)
        for i in range(2):
            pygame.draw.circle(screen,color if i<self.hp else (50,55,66),(center[0]-9+18*i,center[1]-55),5)
        if self.state in ('windup','recovery'):
            label=self.font.render('JUMP!' if self.state=='windup' else 'STRIKE NOW — F',True,color)
            screen.blit(label,label.get_rect(midbottom=(center[0],center[1]-67)))


class LevelTwoCombat:
    def __init__(self,root,zoom,islands):
        self.zoom=zoom
        folder=root/'assets/enemies/shadow'
        frames={'idle':load_frames(folder/'fly','fly',7,(round(98*zoom),round(74*zoom))),
                'attack':load_frames(folder/'attack','attack',6,(round(98*zoom),round(74*zoom)))}
        self.enemies=[DuelShadow(frames,islands[i],i) for i in (1,2)]
        self.cooldown=0.0
        self.swing=0.0
        self.font=pygame.font.SysFont('Segoe UI',17,bold=True)

    def restore(self,data):
        if isinstance(data,list) and len(data)==2 and all(type(hp) is int and 0<=hp<=2 for hp in data):
            for enemy,hp in zip(self.enemies,data):
                enemy.hp=hp

    def snapshot(self):
        return [enemy.hp for enemy in self.enemies]

    def respawn(self):
        for enemy in self.enemies:
            enemy.reset_attack()
        self.cooldown=self.swing=0.0

    @property
    def cleared(self):
        return all(enemy.defeated for enemy in self.enemies)

    def update(self,dt,player,facing_right,attack,health,flying_busy=False):
        self.cooldown=max(0,self.cooldown-dt)
        self.swing=max(0,self.swing-dt)
        changed=False
        for enemy in self.enemies:
            if enemy.index==2 and flying_busy:
                enemy.reset_attack()
                continue
            if enemy.update(dt,player):
                changed=health.damage(enemy.DAMAGE) or changed
        if attack and self.cooldown==0:
            self.cooldown,self.swing=.4,.18
            for enemy in self.enemies:
                changed=enemy.receive_attack(player,facing_right) or changed
        return changed

    def draw(self,screen,player,facing_right,camera_x,camera_y,flying_busy=False):
        for enemy in self.enemies:
            enemy.draw(screen,camera_x,camera_y,self.zoom)
        center=(round((player.centerx-camera_x)*self.zoom),round((player.bottom-45-camera_y)*self.zoom))
        if self.swing>0:
            rect=pygame.Rect(0,0,160,110);rect.center=center
            start,end=(-1.2,1.2) if facing_right else (math.pi-1.2,math.pi+1.2)
            pygame.draw.arc(screen,(244,222,148),rect,start,end,4)
        nearby=next((e for e in self.enemies if not e.defeated and abs(e.x-player.centerx)<190
                     and abs(player.bottom-e.island.top)<130),None)
        if nearby:
            lines=['SPACE: jump the red sweep','F: counter when STRIKE NOW appears']
            if nearby.index==2 and flying_busy:
                lines=['S / DOWN: duck the flying shadow', 'The duel shadow waits until it passes']
            draw_instruction(screen,self.font,lines,(center[0],center[1]-115))
