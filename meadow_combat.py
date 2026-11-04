"""Play staff attacks and apply damage on the contact frame."""
import pygame


class MeadowAttack:
    FPS=12
    CONTACT_FRAME=3
    FRAME_SECONDS=(.04,.05,.05,.08,.09,.05)
    BUFFER_SECONDS=.22

    def __init__(self,root,zoom):
        self.frames={}
        self.left={}
        # Scale attack frames to match Meadow’s normal height.
        scale=100/380*zoom
        for kind in ('sweep','overhead'):
            name='attack_'+kind
            frames=[]
            for i in range(1,7):
                image=pygame.image.load(str(root/'assets/characters/meadow'/name/f'{name}_{i:02d}.png')).convert_alpha()
                frames.append(pygame.transform.smoothscale(image.premul_alpha(),
                              (round(image.get_width()*scale),round(image.get_height()*scale))))
            self.frames[kind]=frames
            self.left[kind]=[pygame.transform.flip(frame,True,False) for frame in frames]
        self.reset()

    def reset(self):
        self.kind=None
        self.time=0.0
        self.hit_sent=False
        self.facing_right=True
        self.queued=None
        self.buffer_time=0.0

    @property
    def active(self):
        return self.kind is not None

    def start(self,kind,facing_right):
        if kind not in self.frames:
            return False
        if self.active:
            self.queued=(kind,facing_right)
            self.buffer_time=self.BUFFER_SECONDS
            return False
        self.kind,self.time,self.hit_sent=kind,0.0,False
        self.facing_right=facing_right
        self.queued=None
        return True

    def update(self,dt):
        if not self.active:
            return False
        self.time+=dt
        self.buffer_time=max(0,self.buffer_time-dt)
        hit=not self.hit_sent and self.time>=sum(self.FRAME_SECONDS[:self.CONTACT_FRAME])
        if hit:
            self.hit_sent=True
        if self.time>=sum(self.FRAME_SECONDS):
            self.kind=None
            if self.queued and self.buffer_time>0:
                self.start(*self.queued)
        return hit

    def image(self):
        if not self.active:
            return None
        elapsed=0.0
        index=5
        for i,duration in enumerate(self.FRAME_SECONDS):
            elapsed+=duration
            if self.time<elapsed:
                index=i
                break
        return (self.frames if self.facing_right else self.left)[self.kind][index]
