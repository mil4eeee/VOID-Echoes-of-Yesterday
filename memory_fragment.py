"""Animated, persistent end-of-level memory collectible; no changes to physics."""
import math
import random
import pygame


class MemoryFragment:
    FRAME_FPS = 8
    BOUNCE_HEIGHT = 12  # world pixels
    BOUNCE_PERIOD = 1.5

    def __init__(self, root, zoom):
        self.zoom = zoom
        self.frames = []
        for index in range(1,5):
            path = root / 'assets/collectibles/memory' / f'memory_{index:02d}.png'
            source = pygame.image.load(str(path)).convert_alpha()
            self.frames.append(pygame.transform.smoothscale(source.premul_alpha(),
                                (round(52*zoom), round(55*zoom))))
        self.rng = random.Random()
        self.font = pygame.font.SysFont('Segoe UI',18,bold=True)
        self.heading = pygame.font.SysFont('Georgia',29)
        self.small = pygame.font.SysFont('Segoe UI',17)
        self.reset(False)

    def reset(self, collected):
        self.collected = bool(collected)
        self.near = False
        self.time = 0.0
        self.message_time = 0.0
        self.burst = []
        self.position = pygame.Vector2()
        self.ground_y = 0

    def update(self, dt, player, final_platform, interact=False):
        dt = min(dt, 0.05)
        self.time += dt
        self.message_time = max(0.0, self.message_time-dt)
        for p in self.burst:
            p[0] += p[2]*dt
            p[1] += p[3]*dt
            p[3] += 30*dt
            p[4] -= dt
        self.burst = [p for p in self.burst if p[4] > 0]
        if self.collected:
            self.near = False
            return False
        # Two soft hops per cycle. Anchor to the actual randomized final island.
        bounce = abs(math.sin(math.tau*self.time/self.BOUNCE_PERIOD))
        self.position.update(final_platform.centerx,
                             final_platform.top-40-self.BOUNCE_HEIGHT*bounce)
        self.ground_y = final_platform.top
        pickup_rect = pygame.Rect(0,0,26,40)
        pickup_rect.center = (round(self.position.x),round(self.position.y))
        self.near = pygame.Vector2(player.centerx, player.bottom-30).distance_to(self.position) <= 64
        if not (interact and self.near):
            return False
        self.collected = True
        self.near = False
        self.message_time = 0.0
        for _ in range(28):
            angle = self.rng.uniform(0,math.tau)
            speed = self.rng.uniform(25,85)
            self.burst.append([self.position.x,self.position.y,
                math.cos(angle)*speed,math.sin(angle)*speed,self.rng.uniform(.6,1.3)])
        return True

    def draw(self, screen, camera_x, camera_y, show_prompt=True):
        if not self.collected:
            center = (round((self.position.x-camera_x)*self.zoom),
                      round((self.position.y-camera_y)*self.zoom))
            frame = self.frames[int(self.time*self.FRAME_FPS) % len(self.frames)]
            screen.blit(frame,frame.get_rect(center=center),special_flags=pygame.BLEND_PREMULTIPLIED)
            # Orbiting sparks stay attached to the fragment as the camera moves.
            for i in range(4):
                phase = self.time*2+i*math.tau/4
                x = center[0]+math.cos(phase)*22*self.zoom
                y = center[1]+math.sin(phase)*9*self.zoom
                pygame.draw.circle(screen,(255,224,146),(round(x),round(y)),2)
        if show_prompt and self.near and not self.collected:
            text = self.small.render('Press E to touch the memory fragment', True, (255,235,184))
            box = text.get_rect(center=(round((self.position.x-camera_x)*self.zoom),
                                       round((self.position.y-camera_y)*self.zoom)-110))
            box.clamp_ip(screen.get_rect().inflate(-20,-20))
            pygame.draw.rect(screen, (10,20,34), box.inflate(18,12), border_radius=5)
            screen.blit(text,box)
        for x,y,_,_,life in self.burst:
            color = (255,round(175+60*min(1,life)),105)
            point = (round((x-camera_x)*self.zoom),round((y-camera_y)*self.zoom))
            pygame.draw.circle(screen,color,point,max(1,round(3*min(1,life))))

    def draw_hud(self, screen):
        panel = pygame.Surface((218,38),pygame.SRCALPHA)
        panel.fill((8,15,28,205))
        screen.blit(panel,(18,104))
        pygame.draw.polygon(screen,(245,202,106),[(35,112),(42,123),(35,134),(28,123)],
                            0 if self.collected else 2)
        label = self.font.render(f'MEMORY   {int(self.collected)} / 1',True,(247,232,197))
        screen.blit(label,(54,110))
