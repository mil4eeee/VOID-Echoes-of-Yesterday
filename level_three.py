"""Set up Level 3 platforms and story events."""
import math
import pygame
from narrative import LevelOneNarrative, DIALOGUES


ISLANDS = [(0,490,300,20), (380,430,270,20), (810,370,270,20),
           (1160,315,250,20), (1540,260,310,20), (2050,200,280,20)]
# Each entry gives the island, movement limits, and speed.
MOTIONS = [(1,360,470,72), (3,1150,1260,60), (4,1540,1660,78)]
WORLD_WIDTH = 2360
ART_ORDER = [0,4,2,1,4,3]

LEVEL_THREE_LINES = {
    'l3_arrival': ['They were like family...', 'What happened to them?',
        'And Noatak... what did you do?', "I don't know what scares me more...",
        'Not remembering... or finding out.', 'But I have to keep going.'],
    'l3_first_before': ['Oh, look. Another one.',
        "You guys really don't know when to quit, do you?"],
    'l3_first_after': ["That's one less thing trying to kill me."],
    'l3_safe': ['Okay... so far, so good.', 'Just keep moving.'],
    'l3_healing_intro': ['Oh, thank goodness. A healing crystal.', 'Finally, something useful.'],
    'l3_healing_after': ['Ahh... much better.', "Alright. Let's keep going."],
    'l3_two_before': ["Oh, you've got to be kidding me.", 'Both of you? Seriously?'],
    'l3_flying': ['WOAH! WATCH IT!'],
    'l3_two_after': ['Okay... that was a little too close.',
        "Why does it feel like they're getting more aggressive?",
        "It's almost like they don't want me reaching those fragments..."],
    'l3_memory_intro': ['There it is...', 'Another memory fragment.',
        "Alright... let's see what you've been hiding from me."],
    'l3_memory_after': ["Wait... something's happening again...", 'No... not my head...',
        'What am I about to remember this time?'],
}
DIALOGUES.update({scene:[('MEADOW',line) for line in lines] for scene,lines in LEVEL_THREE_LINES.items()})


class MovingIslands:
    """Move platforms and everything riding them together."""
    def __init__(self,islands):
        self.islands=islands
        self.positions=[float(islands[index].x) for index,_,_,_ in MOTIONS]
        self.directions=[1,1,1]

    def snapshot(self):
        return [{'x':x,'direction':direction} for x,direction in zip(self.positions,self.directions)]

    def restore(self,data,enemies=()):
        if not valid_motion_save(data):return
        for j,(index,_,_,_) in enumerate(MOTIONS):
            rect=self.islands[index];old=rect.x
            self.positions[j]=float(data[j]['x']);self.directions[j]=data[j]['direction']
            rect.x=round(self.positions[j])
            for enemy in enemies:
                if enemy.island is rect:enemy.x+=rect.x-old

    def update(self,dt,player,velocity_y,enemies=(),orb=None):
        deltas={}
        for j,(index,lo,hi,speed) in enumerate(MOTIONS):
            rect=self.islands[index];old=rect.copy()
            self.positions[j]+=self.directions[j]*speed*min(dt,.05)
            if self.positions[j]>=hi:self.positions[j]=float(hi);self.directions[j]=-1
            elif self.positions[j]<=lo:self.positions[j]=float(lo);self.directions[j]=1
            rect.x=round(self.positions[j]);dx=rect.x-old.x;deltas[index]=dx
            if (velocity_y>=0 and player.bottom==old.top and player.right>old.left and player.left<old.right):
                player.x+=dx
            for enemy in enemies:
                if enemy.island is rect:enemy.x+=dx
            if index==3 and orb is not None and orb.state=='pickup':orb.position.x+=dx
        return deltas


def valid_motion_save(data):
    if not isinstance(data,list) or len(data)!=3:return False
    for item,(_,lo,hi,_) in zip(data,MOTIONS):
        if not isinstance(item,dict):return False
        x=item.get('x');direction=item.get('direction')
        if type(x) not in (int,float) or not math.isfinite(x) or not lo<=x<=hi:return False
        if type(direction) is not int or direction not in (-1,1):return False
    return True


class LevelThreeStory(LevelOneNarrative):
    PHASES=LevelOneNarrative.PHASES | {'memory_wait'}

    def reset(self,data=None,**kwargs):
        super().reset(data)
        self.completed.add('opening')
        self.flying_cleared=isinstance(data,dict) and data.get('flying_cleared') is True
        self.next_memory_pending=isinstance(data,dict) and data.get('next_memory_pending') is True
        self.heal_waiting=isinstance(data,dict) and data.get('heal_waiting') is True
        self.reaction_queue=[]
        if not isinstance(data,dict):self.phase='opening_fade'
        else:
            for entry in data.get('reaction_queue',[]) if isinstance(data.get('reaction_queue'),list) else []:
                if isinstance(entry,(list,tuple)) and len(entry)==2 and isinstance(entry[0],str) and entry[0] in LEVEL_THREE_LINES and type(entry[1]) is int:
                    self.reaction_queue.append((entry[0],entry[1]))
            active=data.get('reaction')
            if isinstance(active,dict) and isinstance(active.get('scene'),str) and active['scene'] in LEVEL_THREE_LINES:
                self.reaction.start(active['scene'],active.get('line',0) if type(active.get('line')) is int else 0)

    def snapshot(self):
        data=super().snapshot()
        data.update(version=5,flying_cleared=self.flying_cleared,next_memory_pending=self.next_memory_pending,
                    heal_waiting=self.heal_waiting,reaction_queue=list(self.reaction_queue),
                    reaction={'scene':self.reaction.scene,'line':self.reaction.index})
        return data

    def queue(self,scene,urgent=False):
        if scene in self.completed or any(name==scene for name,_ in self.reaction_queue):return
        if urgent:
            if self.reaction.scene:
                self.reaction_queue.insert(0,(self.reaction.scene,self.reaction.index))
            self.reaction.start(scene);self.completed.add(scene)
        else:self.reaction_queue.append((scene,0))
        self.dirty=True

    def update(self,dt,orb):
        self.time+=dt
        previous=self.reaction.scene
        self.update_text(dt)
        if previous=='l3_healing_intro' and self.reaction.scene is None:
            self.completed.add('healing_intro');self.dirty=True
        if self.heal_waiting and orb.state=='gone':
            self.heal_waiting=False;self.queue('l3_healing_after')
        if self.phase=='opening_fade' and self.time>=3:self.begin('l3_arrival')
        elif self.phase=='gold_flash' and self.time>=.3:self.begin('l3_memory_after')
        elif self.phase=='memory_wait' and self.time>=1.5:self.set_phase('chapter')
        if not self.blocked and self.reaction.scene is None and self.reaction_queue:
            scene,index=self.reaction_queue.pop(0)
            self.reaction.start(scene,index);self.completed.add(scene);self.dirty=True

    def poll(self,player,islands,orb,memory,shadow,combat=None):
        if shadow.state=='finished' and not self.flying_cleared:
            self.flying_cleared=True;self.dirty=True
        if self.blocked or combat is None:return
        first,second=combat.enemies
        def near(index):
            island=islands[index]
            return player.right>=island.left-60 and player.left<=island.right and abs(player.bottom-island.top)<100
        if near(1) and not first.defeated:self.queue('l3_first_before')
        if first.defeated:self.queue('l3_first_after')
        if self.supported(player,[islands[2]]):self.queue('l3_safe')
        if orb.near and not orb.collected:self.queue('l3_healing_intro')
        if near(4) and not (second.defeated and self.flying_cleared):self.queue('l3_two_before')
        if shadow.state in ('warning','fly'):self.queue('l3_flying',urgent=True)
        if second.defeated and self.flying_cleared:self.queue('l3_two_after')
        if (memory.near and not memory.collected and combat.cleared and self.flying_cleared
                and self.supported(player,[islands[-1]]) and not self.reaction.scene
                and not self.reaction_queue and 'l3_memory_intro' not in self.completed):
            self.begin('l3_memory_intro')

    def finish_scene(self,scene):
        if scene=='l3_memory_after':
            elapsed=self.time;self.set_phase('memory_wait');self.time=elapsed
        else:
            self.set_phase('gameplay')
            if scene=='l3_memory_intro':self.completed.add('memory_intro')

    def on_heal(self):
        self.heal_waiting=True;self.dirty=True

    def on_memory(self):
        self.next_memory_pending=True;self.set_phase('gold_flash')

    def draw(self,screen):
        if self.phase=='chapter':
            screen.fill((0,0,0))
            for text,font,y in [('The next memory awaits...',self.title,210),
                                ('To be continued',self.small,275),
                                ('ENTER / ESC — Return to main menu',self.small,380)]:
                label=font.render(text,True,(236,215,155))
                screen.blit(label,label.get_rect(center=(screen.get_width()//2,y)))
            pygame.draw.rect(screen,(142,151,167),self.return_button(screen.get_size()),1,border_radius=6)
        elif self.phase=='memory_wait':self.fade.draw(screen,self.time,1.5)
        elif self.phase=='dialogue' and self.dialogue.scene=='l3_memory_after':
            self.fade.draw(screen,self.time,1.5)
            self.dialogue.draw(screen)
        else:super().draw(screen)
