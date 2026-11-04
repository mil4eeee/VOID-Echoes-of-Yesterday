"""Set up Level 2 and its shadow fights."""
import math
import pygame
from shadow_encounter import load_frames
from narrative import LevelOneNarrative, DIALOGUES, DIALOGUE_PAUSES
from instruction_ui import draw_instruction


# Place four fixed islands and one moving platform.
ISLANDS = [(0,490,300,20), (390,420,270,20),
           (1120,310,280,20), (1510,235,290,20)]
MOVING = (780,365,210,20)
MOVING_LIMITS = (710,900)
WORLD_WIDTH = 1840

# Use these lines for the second memory.
SECOND_MEMORY_LINES = {
    'l2_memory_before': [('Meadow', 'Not again...'), ('Meadow', 'My head...!')],
    'l2_confrontation': [
        ('Meadow (Past)', 'How could you do this, Noatak?!'),
        ('Meadow (Past)', 'They were like family to us!'),
        ('Noatak', "Meadow... there are things you don't understand."),
        ('Meadow (Past)', "DON'T UNDERSTAND?!"),
        ('Meadow (Past)', 'HOW CAN I POSSIBLY UNDERSTAND WHAT YOU DID?!'),
        ('Meadow (Past)', 'What kind of explanation could EVER justify this?!'),
        ('Noatak', 'You think I wanted any of this?'),
        ('Meadow (Past)', 'Then WHY?!'),
        ('Meadow (Past)', "LOOK AT WHAT YOU'VE DONE!"),
        ('Noatak', "If you'd just let me explain—"),
        ('Meadow (Past)', "NO! You don't get to explain this away!"),
        ('Noatak', "Meadow... I'm trying to protect you."),
        ('Meadow (Past)', 'Protect me...?'),
        ('Meadow (Past)', 'From WHAT?!'),
        ('Noatak', 'From the truth—'),
    ],
    'l2_memory_after': [('Meadow', line) for line in [
        'Noatak...', 'What... what did you do?', 'They were like family...?',
        'Who was I talking about?', 'And what truth was he trying to protect me from?',
        'Ugh... every answer just gives me more questions.']],
}
DIALOGUES.update(SECOND_MEMORY_LINES)
DIALOGUE_PAUSES.update({('l2_confrontation',11):.8, ('l2_memory_after',4):.75})


class LevelTwoStory(LevelOneNarrative):
    """Start dialogue when Meadow reaches the right place or encounter."""
    PHASES=LevelOneNarrative.PHASES | {'level2_title'}

    def reset(self,data=None,**kwargs):
        super().reset(data)
        self.completed.update(('opening','healing_intro','healing_after'))
        self.flying_cleared=isinstance(data,dict) and data.get('flying_cleared') is True
        self.second_memory_pending=isinstance(data,dict) and data.get('second_memory_pending') is True
        if not isinstance(data,dict):
            self.phase='opening_fade'
        elif data.get('version',0)<4:
            # Keep progress when loading an older save.
            if self.phase in ('gameplay','chapter','gold_flash'):
                self.completed.add('l2_arrival')
            if self.phase=='level2_title':self.set_phase('opening_fade')
        if 'l2_memory_intro' not in self.completed:
            self.completed.discard('memory_intro')
        if isinstance(data,dict) and kwargs.get('memory') and 'l2_memory_after' not in self.completed:
            # Show the new memory when loading an old ending save.
            if self.phase in ('chapter','exit_fade','gameplay'):
                self.second_memory_pending=True
                if 'l2_confrontation' in self.completed:self.begin('l2_memory_after')
                else:self.set_phase('gold_flash')

    def poll(self,player,islands,orb,memory,shadow,combat=None):
        if not self.flying_cleared and shadow.state=='finished':
            self.flying_cleared=True;self.dirty=True
        if self.blocked or combat is None:return
        if shadow.state in ('warning','fly'):
            self.react('l2_flying')
            return
        # Wait for the attack to finish before starting dialogue.
        if any(not e.defeated and e.state in ('windup','strike') for e in combat.enemies):return
        safe_grounded=self.supported(player,islands[:-1])
        first,second=combat.enemies
        if first.defeated and safe_grounded and 'l2_duel_after' not in self.completed:
            self.begin('l2_duel_after')
        elif second.defeated and self.flying_cleared and safe_grounded and 'l2_two_after' not in self.completed:
            self.begin('l2_two_after')
        elif self.supported(player,[islands[1]]) and not first.defeated and 'l2_duel_before' not in self.completed:
            self.begin('l2_duel_before')
        elif self.supported(player,[islands[2]]) and 'l2_two_before' not in self.completed and not (second.defeated and self.flying_cleared):
            self.begin('l2_two_before')
        elif (safe_grounded and memory.near and not memory.collected and combat.cleared
              and self.flying_cleared and 'l2_memory_intro' not in self.completed):
            self.begin('l2_memory_intro')
        elif ('l2_duel_after' in self.completed and 'l2_moving' not in self.completed
              and (self.supported(player,[islands[-1]])
                   or (player.centerx>=islands[1].right-45 and player.left<islands[2].left))):
            self.react('l2_moving')

    def snapshot(self):
        data=super().snapshot()
        data.update(version=6,flying_cleared=self.flying_cleared,
                    second_memory_pending=self.second_memory_pending)
        return data

    def finish_scene(self,scene):
        if scene=='l2_memory_before':self.set_phase('memory_fade')
        elif scene=='l2_confrontation':self.set_phase('black_cut')
        elif scene=='l2_memory_after':
            self.second_memory_pending=False
            self.set_phase('exit_fade')
        else:self.set_phase('gameplay')
        if scene=='l2_memory_intro':self.completed.add('memory_intro')

    def update(self,dt,orb):
        self.time+=dt
        self.update_text(dt)
        if self.phase in ('opening_fade','level2_title') and self.time>=3:
            self.begin('l2_arrival')
        elif self.phase=='heal_pickup' and orb.state=='gone':self.set_phase('gameplay')
        elif self.phase=='gold_flash' and self.time>=.3:self.begin('l2_memory_before')
        elif self.phase=='memory_fade' and self.time>=1.2:self.begin('l2_confrontation')
        elif self.phase=='black_cut' and self.time>=.65:self.begin('l2_memory_after')
        elif self.phase=='exit_fade' and self.time>=.8 and 'l2_memory_after' in self.completed:
            self.set_phase('chapter')

    def on_memory(self):
        if self.second_memory_pending or 'l2_memory_after' in self.completed:return
        self.second_memory_pending=True
        self.set_phase('gold_flash')

    def draw(self,screen):
        if self.phase in ('black_cut','exit_fade'):
            screen.fill((0,0,0))
            return
        if self.phase in ('dialogue','dialogue_pause') and self.dialogue.scene in ('l2_confrontation','l2_memory_after'):
            # Tint the memory red and the present black.
            screen.fill((16,2,3) if self.dialogue.scene=='l2_confrontation' else (0,0,0))
            if self.phase=='dialogue':self.dialogue.draw(screen)
            return
        if self.phase!='chapter':
            super().draw(screen)
            return
        screen.fill((7,11,22))
        for text,font,y in [('Memory fragment collected',self.title,195),
                            ('To be continued',self.small,260),
                            ('ENTER / ESC — Return to main menu',self.small,380)]:
            image=font.render(text,True,(242,217,164))
            screen.blit(image,image.get_rect(center=(screen.get_width()//2,y)))
        pygame.draw.rect(screen,(142,151,167),self.return_button(screen.get_size()),1,border_radius=6)


class DuelShadow:
    """Animate the ground creature as it runs, attacks, and recovers."""
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
        self.facing_right=False
        self.moving=False
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
        self.facing_right=player.centerx>self.x
        same_island=(player.right>self.island.left and player.left<self.island.right
                     and abs(player.bottom-self.island.top)<35)
        self.moving=self.state=='idle' and same_island and abs(player.centerx-self.x)>=105
        if self.moving:
            self.x+= (1 if self.facing_right else -1)*30*dt
            self.x=max(self.island.left+50,min(self.island.right-50,self.x))
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
        if (not self.defeated and self.state!='strike' and abs(delta)<=110
                and abs(player.bottom-self.island.top)<65
                and (abs(delta)<15 or (delta>0)==facing_right)):
            self.hp-=1
            # Getting hit does not cancel a prepared lunge.
            if self.state=='idle':
                self.state,self.time='windup',0.0
            return True
        return False

    def draw(self,screen,camera_x,camera_y,zoom):
        if self.defeated:
            return
        if self.state=='windup':
            frame=self.frames['attack'][min(2,int(self.time/self.WINDUP*3))]
        elif self.state=='strike':
            frame=self.frames['attack'][3+min(2,int(self.time/self.STRIKE*3))]
        else:
            frames=self.frames['run' if self.moving else 'idle']
            frame=frames[int(self.time*8)%len(frames)]
        if not self.facing_right:
            frame=pygame.transform.flip(frame,True,False)
        center=(round((self.x-camera_x)*zoom),round((self.island.top-43-camera_y)*zoom))
        screen.blit(frame,frame.get_rect(midbottom=(center[0],round((self.island.top+5-camera_y)*zoom))),
                    special_flags=pygame.BLEND_PREMULTIPLIED)
        color=(255,115,100) if self.state in ('windup','strike') else (125,226,214)
        if self.state=='windup':
            # Show a ring so the player knows when to jump.
            pygame.draw.ellipse(screen,color,(center[0]-90*zoom,round((self.island.top-camera_y)*zoom)-8,180*zoom,16),2)
        for i in range(2):
            pygame.draw.circle(screen,color if i<self.hp else (50,55,66),(center[0]-9+18*i,center[1]-55),5)
        if self.state in ('windup','recovery'):
            label=self.font.render('JUMP!' if self.state=='windup' else 'STRIKE NOW — F / G',True,color)
            screen.blit(label,label.get_rect(midbottom=(center[0],center[1]-67)))


class LevelTwoCombat:
    def __init__(self,root,zoom,islands,enemy_indices=(1,2)):
        self.zoom=zoom
        folder=root/'assets/enemies/ground'
        frames={state:load_frames(folder/state,state,count,(round(150*zoom),round(100*zoom)))
                for state,count in [('run',8),('attack',8),('idle',4)]}
        self.enemies=[DuelShadow(frames,islands[i],i) for i in enemy_indices]
        self.combined_index=enemy_indices[-1]
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

    def update(self,dt,player,facing_right,attack,health,flying_busy=False,enabled=(True,True)):
        self.cooldown=max(0,self.cooldown-dt)
        self.swing=max(0,self.swing-dt)
        changed=False
        for enemy,allowed in zip(self.enemies,enabled):
            if not allowed:
                enemy.reset_attack()
                continue
            if enemy.index==self.combined_index and flying_busy:
                enemy.reset_attack()
                continue
            if enemy.update(dt,player):
                changed=health.damage(enemy.DAMAGE) or changed
        if attack and self.cooldown==0:
            self.cooldown,self.swing=.25,.18
            for enemy,allowed in zip(self.enemies,enabled):
                if allowed:changed=enemy.receive_attack(player,facing_right) or changed
        return changed

    def draw(self,screen,player,facing_right,camera_x,camera_y,flying_busy=False):
        for enemy in self.enemies:
            enemy.draw(screen,camera_x,camera_y,self.zoom)
        center=(round((player.centerx-camera_x)*self.zoom),round((player.bottom-45-camera_y)*self.zoom))
        nearby=next((e for e in self.enemies if not e.defeated and abs(e.x-player.centerx)<190
                     and abs(player.bottom-e.island.top)<130),None)
        if nearby:
            lines=['F / G: attack; SPACE: dodge the lunge','Counter after dodging for a safe opening']
            if nearby.index==self.combined_index and flying_busy:
                lines=['S / DOWN: duck the flying shadow', 'The ground creature waits until it passes']
            draw_instruction(screen,self.font,lines,(center[0],center[1]-115))
