"""Health, the one-use healing crystal, and the opening gameplay tutorial."""
import math
import pygame
from instruction_ui import draw_instruction


class Health:
    MAX_HP=100
    START_HP=75
    SHADOW_DAMAGE=25

    def __init__(self):
        self.font=pygame.font.SysFont('Segoe UI',18,bold=True)
        self.small=pygame.font.SysFont('Segoe UI',12,bold=True)
        self.reset()

    def reset(self,hp=START_HP):
        self.current=max(0,min(self.MAX_HP,hp)) if type(hp) is int else self.START_HP
        self.display_hp=float(self.current)
        self.invulnerable=0.0

    def heal(self,amount):
        before=self.current
        self.current=min(self.MAX_HP,self.current+max(0,int(amount)))
        return self.current-before

    def damage(self,amount):
        if self.invulnerable>0 or self.current<=0:
            return False
        self.current=max(0,self.current-max(0,int(amount)))
        self.invulnerable=1.0
        return True

    def update(self,dt):
        self.invulnerable=max(0,self.invulnerable-dt)
        self.update_display(dt)

    def update_display(self,dt):
        """Animate the HUD even when dialogue freezes gameplay timers."""
        self.display_hp+=(self.current-self.display_hp)*(1-math.exp(-12*dt))

    @property
    def color(self):
        if self.current>50:
            return (78,205,124)
        if self.current>25:
            return (238,193,70)
        return (231,74,86)

    def draw(self,screen):
        # Screen coordinates only: camera movement and zoom cannot move this HUD.
        panel=pygame.Surface((280,76),pygame.SRCALPHA)
        panel.fill((9,19,27,230))
        pygame.draw.rect(panel,(175,153,99),(0,0,280,76),1,border_radius=8)
        panel.blit(self.small.render('MEADOW',True,(233,213,169)),(42,10))
        label=self.font.render(f'{self.current}/{self.MAX_HP} HP',True,(240,242,223))
        panel.blit(label,label.get_rect(topright=(264,7)))
        pygame.draw.polygon(panel,(217,189,117),[(22,12),(32,27),(22,42),(12,27)],2)
        pygame.draw.polygon(panel,self.color,[(22,19),(27,27),(22,35),(17,27)])
        pygame.draw.rect(panel,(3,11,17),(14,48,252,15),border_radius=6)
        fill=round(248*self.display_hp/self.MAX_HP)
        if fill>0:
            pygame.draw.rect(panel,self.color,(16,50,fill,11),border_radius=5)
            pygame.draw.line(panel,(184,239,191),(18,51),(16+max(1,fill-3),51))
        pygame.draw.rect(panel,(137,136,93),(14,48,252,15),1,border_radius=6)
        screen.blit(panel,(18,18))


class HealingOrb:
    HEAL_AMOUNT=25
    INTERACTION_RANGE=68
    FPS={'idle':8,'pickup':12,'spawn':12}
    COUNTS={'idle':8,'pickup':9,'spawn':9}

    def __init__(self,root,zoom):
        self.zoom=zoom
        self.frames={}
        for state,count in self.COUNTS.items():
            frames=[]
            for i in range(1,count+1):
                path=root/'assets/collectibles/healing'/state/f'{state}_{i:02d}.png'
                image=pygame.image.load(str(path)).convert_alpha()
                frames.append(pygame.transform.smoothscale(image.premul_alpha(),(round(72*zoom),round(72*zoom))))
            self.frames[state]=frames
        self.font=pygame.font.SysFont('Segoe UI',17,bold=True)
        self.reset(False)

    def reset(self,collected):
        self.collected=bool(collected)
        self.state='gone' if self.collected else 'spawn'
        self.time=0.0
        self.float_time=0.0
        self.near=False
        self.position=pygame.Vector2()

    def update(self,dt,player,platform,interact,health):
        dt=min(dt,.05)
        self.time+=dt
        self.float_time+=dt
        if self.state!='pickup':
            self.position.update(min(platform.right-45,platform.left+190),
                                 platform.top-34+4*math.sin(self.float_time*2))
        if self.state in ('spawn','pickup') and self.time>=len(self.frames[self.state])/self.FPS[self.state]:
            self.state='idle' if self.state=='spawn' else 'gone'
            self.time=0.0
        # A world-space radius around Meadow's torso, not screen/camera pixels.
        torso=pygame.Vector2(player.centerx,player.bottom-30)
        self.near=(not self.collected and self.state=='idle'
                   and torso.distance_to(self.position)<=self.INTERACTION_RANGE)
        if interact and self.near:
            self.collected=True  # Lock immediately, including during the pickup frames.
            self.near=False
            self.state,self.time='pickup',0.0
            health.heal(self.HEAL_AMOUNT)
            return True
        return False

    def draw(self,screen,camera_x,camera_y,show_prompt=True):
        if self.state=='gone':
            return
        frames=self.frames[self.state]
        index=int(self.time*self.FPS[self.state])
        index=index%len(frames) if self.state=='idle' else min(index,len(frames)-1)
        center=(round((self.position.x-camera_x)*self.zoom),round((self.position.y-camera_y)*self.zoom))
        # Premultiplied alpha keeps the green crystal's color against the blue forest.
        screen.blit(frames[index],frames[index].get_rect(center=center),special_flags=pygame.BLEND_PREMULTIPLIED)
        if self.near and show_prompt:
            draw_instruction(screen, self.font,
                             ['Press E to absorb', 'healing energy'],
                             (center[0], center[1]-120))


class OpeningTutorial:
    DURATION=6.0

    def __init__(self):
        self.font=pygame.font.SysFont('Segoe UI',17)
        self.reset()

    def reset(self,seen=False):
        self.time=self.DURATION if seen else 0.0

    @property
    def active(self):
        return self.time<self.DURATION

    def update(self,dt):
        self.time=min(self.DURATION,self.time+dt)

    def draw(self,screen,orb,health,enemy_busy=False,anchor=None):
        if enemy_busy or not self.active or anchor is None:
            return
        draw_instruction(screen, self.font,
                         ['A / D — Move', 'SPACE — Jump', 'E — Interact'], anchor)
