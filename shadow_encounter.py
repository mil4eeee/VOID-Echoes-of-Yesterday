"""Handle crouching and the first flying shadow encounter."""
import math
import pygame


def load_frames(folder, prefix, count, size):
    frames=[]
    for number in range(1,count+1):
        source=pygame.image.load(str(folder/f'{prefix}_{number:02d}.png')).convert_alpha()
        frames.append(pygame.transform.smoothscale(source.premul_alpha(),size))
    return frames


class CrouchAnimation:
    def __init__(self,root,zoom):
        self.zoom=zoom
        size=(round(280*100/320*zoom),round(340*100/320*zoom))
        self.frames=load_frames(root/'assets/characters/meadow/crouch','crouch',8,size)
        self.left=[pygame.transform.flip(frame,True,False) for frame in self.frames]
        self.reset()

    def reset(self):
        self.state='standing'
        self.time=0.0
        self.index=0

    @property
    def active(self):
        return self.state!='standing'

    def update(self,dt,pressed,grounded):
        if not grounded:
            self.reset()
            return
        if pressed and self.state in ('standing','rising'):
            self.state,self.time='lowering',0.0
        elif not pressed and self.state in ('lowering','hold'):
            self.state,self.time='rising',0.0
        self.time+=min(dt,.05)
        if self.state=='lowering':
            self.index=min(3,int(self.time/.05))
            if self.time>=.20:
                self.state,self.time,self.index='hold',0.0,4
        elif self.state=='hold':
            self.index=4+int(self.time/.25)%2
        elif self.state=='rising':
            self.index=6+min(1,int(self.time/.07))
            if self.time>=.14:
                self.reset()

    def image(self,facing_right):
        return (self.frames if facing_right else self.left)[self.index]

    def hurtbox(self,player):
        # Match damage detection to the crouching pose.
        height=90
        if self.active:
            height=max(48,min(90,math.ceil(self.frames[self.index].get_bounding_rect(64).height/self.zoom)-8))
        rect=pygame.Rect(0,0,30,height)
        rect.midbottom=player.midbottom
        return rect


class ShadowEncounter:
    SPEED=235
    WARNING_SECONDS=0.65

    def __init__(self,root,zoom):
        self.zoom=zoom
        folder=root/'assets/enemies/shadow'
        size=(round(90*zoom),round(67.5*zoom))
        self.fly=load_frames(folder/'fly','fly',7,size)
        self.dissipate=load_frames(folder/'dissipate','dissipate',6,size)
        self.font=pygame.font.SysFont('Segoe UI',20,bold=True)
        self.reset()

    def reset(self):
        self.state='idle'
        self.time=0.0
        self.x=self.y=0.0
        self.hit_notice=0.0

    def body_rect(self):
        rect=pygame.Rect(0,0,46,28)
        rect.center=(round(self.x-8),round(self.y+10))
        return rect

    def update(self,dt,player,hurtbox,island):
        dt=min(dt,.05)
        self.hit_notice=max(0,self.hit_notice-dt)
        self.time+=dt
        supported=(player.bottom==island.top and player.right>island.left and player.left<island.right)
        if self.state=='idle' and supported:
            self.state,self.time='warning',0.0
            self.x,self.y=island.right+45,island.top-90
        elif self.state=='warning' and self.time>=self.WARNING_SECONDS:
            self.state,self.time='fly',0.0
        elif self.state=='fly':
            old=self.body_rect()
            self.x-=self.SPEED*dt
            # Check the whole flight path so fast attacks still detect hits.
            if old.union(self.body_rect()).colliderect(hurtbox):
                self.state,self.time='dissipate',0.0
                self.hit_notice=3.0
                return True
            if self.x<island.left-140:
                self.state,self.time='finished',0.0
        elif self.state=='dissipate' and self.time>=.6:
            self.state,self.time='finished',0.0
        elif self.state=='finished' and (player.right<island.left-60 or player.left>island.right+60):
            self.state,self.time='idle',0.0
        return False

    def draw(self,screen,camera_x,camera_y):
        if self.state in ('warning','fly','dissipate'):
            frames=self.fly if self.state in ('warning','fly') else self.dissipate
            index=int(self.time*10)
            index=index%len(frames) if self.state in ('warning','fly') else min(index,len(frames)-1)
            center=(round((self.x-camera_x)*self.zoom),round((self.y-camera_y)*self.zoom))
            screen.blit(frames[index],frames[index].get_rect(center=center),special_flags=pygame.BLEND_PREMULTIPLIED)

    def draw_hint(self,screen):
        message=''
        if self.state in ('warning','fly'):
            message='SHADOW APPROACHING  —  Hold S or DOWN to crouch'
        elif self.hit_notice>0:
            message='Shadow strike!  Crouch to let it pass overhead.'
        if message:
            text=self.font.render(message,True,(224,228,255))
            panel=pygame.Surface((text.get_width()+36,42),pygame.SRCALPHA)
            panel.fill((13,12,34,230))
            panel.blit(text,(18,8))
            screen.blit(panel,(screen.get_width()//2-panel.get_width()//2,screen.get_height()-60))
