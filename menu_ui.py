"""Menu UI and small, atomic JSON saves for VOID."""
import json
import math
from pathlib import Path
import pygame


def read_json(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temporary.replace(path)


def valid_save(data):
    if not isinstance(data, dict) or data.get("version") != 1:
        return False
    try:
        widths = data["widths"]
        level=data.get('level',1)
        if type(level) is not int or level not in (1,2):
            return False
        ranges = ([(300,300),(270,270),(280,280),(290,290),(210,210)] if level==2
                  else [(280,320),(200,240),(200,240),(180,220),(160,200)])
        island_ids=data['islands']
        valid_islands=(isinstance(island_ids,list) and len(island_ids)==5
                       and all(type(i) is int and 0<=i<5 for i in island_ids))
        if level==1:
            valid_islands=valid_islands and sorted(island_ids)==list(range(5))
        duels=data.get('duels',[2,2])
        if level==2 and not (isinstance(duels,list) and len(duels)==2
                            and all(type(hp) is int and 0<=hp<=2 for hp in duels)):
            return False
        return (
            isinstance(widths, list) and len(widths) == 5
            and all(type(w) is int and lo <= w <= hi for w,(lo,hi) in zip(widths,ranges))
            and valid_islands
            and all(type(i) is int for i in data["islands"])
            and type(data["x"]) is int and 0 <= data["x"] <= (1800 if level==2 else 1560)
            and type(data["y"]) is int and -500 <= data["y"] <= 540
            and type(data["velocity_y"]) in (float,int) and -50 <= data["velocity_y"] <= 100
            and type(data["on_ground"]) is bool and type(data["facing_right"]) is bool
            and type(data["moving_x"]) is int and (710 if level==2 else 850) <= data["moving_x"] <= (900 if level==2 else 1190)
            and data["moving_speed"] in (-2, 2)
            and type(data.get("hp", 75)) is int and 0 <= data.get("hp",75) <= 100
            and type(data.get("healing_collected", False)) is bool
            and type(data.get("tutorial_seen", False)) is bool
        )
    except (KeyError, TypeError, ValueError):
        return False


class MenuUI:
    def __init__(self, root, size):
        self.root = root
        self.size = size
        self.save_path = root / "saves" / "savegame.json"
        self.settings_path = root / "saves" / "settings.json"
        self.saved = read_json(self.save_path)
        self.has_save = valid_save(self.saved)
        preferences = read_json(self.settings_path) or {}
        self.fireflies = preferences.get("fireflies", True) is not False
        self.fullscreen = preferences.get("fullscreen", False) is True
        self.page = "main"
        self.parent_page = "main"
        self.selected = 0
        self.notice = "" if self.has_save else "Begin a new journey to unlock Continue."
        self.font = pygame.font.SysFont("Segoe UI", 22)
        self.small = pygame.font.SysFont("Segoe UI", 15)
        self.heading = pygame.font.SysFont("Georgia", 34)
        self.logo_font = pygame.font.SysFont("Georgia", 78)
        self.subtitle_font = pygame.font.SysFont("Segoe UI", 17)
        self.button_font = pygame.font.SysFont("Segoe UI", 23, bold=True)
        self.tiny = pygame.font.SysFont("Segoe UI", 12, bold=True)
        # Fully cover the small baked-in title/buttons; render fresh text at native size.
        self.scrim = pygame.Surface(size, pygame.SRCALPHA)
        self.scrim.fill((0, 0, 0, 0))
        self.scrim.fill((10, 16, 29, 255), (0, 0, 430, size[1]))
        for x in range(430, 650):
            alpha = round(255 * (1 - (x-430)/220)**2)
            pygame.draw.line(self.scrim, (10, 16, 29, alpha), (x, 0), (x, size[1]))
        raw = pygame.image.load(str(root / "assets/backgrounds/main_menu.png")).convert()
        factor = max(size[0]/raw.get_width(), size[1]/raw.get_height())
        self.background = pygame.transform.smoothscale(raw,
            (round(raw.get_width()*factor), round(raw.get_height()*factor)))
        self.background_rect = self.background.get_rect(center=(size[0]//2,size[1]//2))
        self.pause_image = None

    def open(self, page):
        self.page = page
        self.selected = 0

    def options(self):
        if self.page == "main":
            return [("New Game", "new", True), ("Continue", "continue", self.has_save),
                    ("Settings", "settings", True), ("Controls", "controls", True),
                    ("Quit", "quit", True)]
        if self.page == "pause":
            return [("Resume", "resume", True), ("Settings", "settings", True),
                    ("Controls", "controls", True), ("Save & Main Menu", "save_menu", True),
                    ("Quit Game", "quit", True)]
        if self.page == "settings":
            return [(f"Fireflies: {'On' if self.fireflies else 'Off'}", "particles", True),
                    (f"Fullscreen: {'On' if self.fullscreen else 'Off'}", "fullscreen", True),
                    ("Back", "back", True)]
        if self.page == "confirm":
            return [("Keep my journey", "back", True), ("Start a new game", "replace", True)]
        return [("Back", "back", True)]

    def button_rect(self, index):
        if self.page == "main":
            if index < 2:
                return pygame.Rect(48, 232 + index * 64, 324, 52)
            columns = {2: 0, 3: 1, 4: 2}
            return pygame.Rect(48 + columns[index]*112, 385, 100, 42)
        if self.page == "controls":
            return pygame.Rect(270, 409, 420, 44)
        if self.page == "confirm":
            return pygame.Rect(270, 271 + index*58, 420, 46)
        return pygame.Rect(270, 177 + index*54, 420, 44)

    def event(self, event):
        options = self.options()
        activate = False
        if event.type == pygame.MOUSEMOTION:
            for index, (_, _, enabled) in enumerate(options):
                if enabled and self.button_rect(index).collidepoint(event.pos):
                    self.selected = index
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, (_, _, enabled) in enumerate(options):
                if enabled and self.button_rect(index).collidepoint(event.pos):
                    self.selected = index
                    activate = True
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s, pygame.K_TAB):
                direction = -1 if event.key in (pygame.K_UP, pygame.K_w) else 1
                for _ in options:
                    self.selected = (self.selected + direction) % len(options)
                    if options[self.selected][2]:
                        break
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                activate = options[self.selected][2]
            elif event.key == pygame.K_ESCAPE:
                if self.page == "pause":
                    return "resume"
                if self.page != "main":
                    self.open(self.parent_page)
                return None
        if not activate:
            return None
        action = options[self.selected][1]
        if action in ("settings", "controls"):
            self.parent_page = self.page
            self.open(action)
        elif action == "back":
            self.open(self.parent_page)
        elif action == "new" and self.has_save:
            self.parent_page = "main"
            self.open("confirm")
        elif action in ("particles", "fullscreen"):
            if action == "particles":
                self.fireflies = not self.fireflies
            else:
                self.fullscreen = not self.fullscreen
            self.store_preferences()
            if action == "fullscreen":
                return "display"
        else:
            return "new" if action == "replace" else action
        return None

    def store_preferences(self):
        try:
            write_json(self.settings_path, {"fireflies": self.fireflies, "fullscreen": self.fullscreen})
            self.notice = "Settings saved."
        except OSError:
            self.notice = "Settings apply for this session; could not save them."

    def text(self, screen, text, font, center, color=(235,225,210)):
        rendered = font.render(text, True, color)
        screen.blit(rendered, rendered.get_rect(center=center))

    def label(self, screen, text, font, position, color=(239,239,234)):
        screen.blit(font.render(text, True, color), position)

    def draw(self, screen):
        gold = (235, 204, 149)
        muted = (166, 180, 197)
        screen.blit(self.background, self.background_rect)
        screen.blit(self.scrim, (0, 0))
        # A few restrained gold motes animate the artwork without blurring the UI.
        seconds = pygame.time.get_ticks() / 1000
        for i in range(12):
            x = 520 + (i * 71) % 415 + 8 * math.sin(seconds * .2 + i)
            y = 40 + (i * 97 - seconds * (3 + i % 3)) % 410
            light = round(120 + 70 * math.sin(seconds + i)**2)
            pygame.draw.circle(screen, (light, light, round(light*.75)), (round(x), round(y)), 1)

        self.label(screen, "A JOURNEY BEYOND MEMORY", self.tiny, (52, 48), gold)
        self.label(screen, "VOID", self.logo_font, (43, 71))
        self.label(screen, "E C H O E S   O F   Y E S T E R D A Y", self.subtitle_font, (49, 164), gold)
        pygame.draw.line(screen, (77, 84, 95), (49, 207), (370, 207))
        pygame.draw.polygon(screen, gold, [(207,203),(211,207),(207,211),(203,207)])

        if self.page == "main":
            hint = "Your saved journey is ready." if self.has_save else "No saved journey yet. Start with New Game."
            self.label(screen, hint, self.small, (50, 356), muted)
            self.label(screen, "EXPLORE. REMEMBER. RETURN.", self.tiny, (51, 449), (135,157,178))
            self.label(screen, "THE SPIRIT FOREST", self.tiny, (708, 455), (224,226,237))
        else:
            if (self.page == "pause" or self.parent_page == "pause") and self.pause_image:
                screen.blit(self.pause_image, (0,0))
            veil = pygame.Surface(self.size, pygame.SRCALPHA)
            veil.fill((5,9,19,205))
            screen.blit(veil, (0,0))
            pygame.draw.rect(screen, (14,23,38), (230,55,500,420), border_radius=12)
            pygame.draw.rect(screen, (79,100,116), (230,55,500,420), 1, border_radius=12)
            pygame.draw.line(screen, gold, (270,56),(690,56),2)
            title = {"pause":"Journey paused", "settings":"Settings", "controls":"How to play",
                     "confirm":"A new beginning"}[self.page]
            self.text(screen, title, self.heading, (480,108))
            self.text(screen, "VOID: ECHOES OF YESTERDAY", self.tiny, (480,146), muted)
            if self.page == "confirm":
                self.text(screen, "This will replace your saved journey.", self.small, (480,205))
                self.text(screen, "Your current progress will be lost.", self.small, (480,231), muted)
            if self.page == "controls":
                for i, (key, action) in enumerate([("A / D", "Move left / right"),
                       ("SPACE", "Jump"), ("E", "Interact / heal"), ("S / DOWN", "Crouch / dodge"), ("F", "Strike (Level 2)"), ("ESC", "Pause / resume")]):
                    y = 165 + i*34
                    pygame.draw.rect(screen, (35,49,66), (270,y,98,34), border_radius=5)
                    pygame.draw.rect(screen, (90,114,132), (270,y,98,34),1,border_radius=5)
                    self.text(screen,key,self.small,(319,y+17),gold)
                    self.label(screen,action,self.font,(390,y+2))
                self.text(screen, "Navigate menus with arrows, Enter, or your mouse.", self.small, (480,390),muted)

        for i, (label, action, enabled) in enumerate(self.options()):
            rect = self.button_rect(i)
            selected = i == self.selected and enabled
            primary = self.page == "main" and i == 0
            fill = (228,200,148) if primary else ((39,61,77) if selected else (22,35,51))
            if not enabled:
                fill = (19,27,40)
            pygame.draw.rect(screen, (4,8,15), rect.move(0,3), border_radius=7)
            pygame.draw.rect(screen, fill, rect, border_radius=7)
            border = gold if selected or primary else ((71,91,110) if enabled else (43,54,68))
            pygame.draw.rect(screen, border, rect, 2 if selected else 1, border_radius=7)
            color = (20,27,38) if primary else ((241,244,244) if enabled else (137,149,166))
            font = self.button_font if self.page == "main" and i < 2 else self.font
            if self.page == "main" and i >= 2:
                font = self.small
            if self.page == "settings" and action in ("particles", "fullscreen"):
                self.label(screen, label.split(":")[0],self.font,(rect.x+18,rect.y+7))
                on = self.fireflies if action == "particles" else self.fullscreen
                toggle = pygame.Rect(rect.right-82, rect.y+9, 64, 26)
                pygame.draw.rect(screen, (97,185,170) if on else (59,72,89), toggle,border_radius=13)
                pygame.draw.circle(screen,(240,246,241),(toggle.right-13 if on else toggle.left+13,toggle.centery),9)
            else:
                self.text(screen,label,font,rect.center,color)
            if selected and not primary:
                pygame.draw.line(screen,gold,(rect.x+1,rect.y+10),(rect.x+1,rect.bottom-10),3)

        pygame.draw.rect(screen,(8,14,25),(0,486,960,54))
        if self.notice and self.notice != "Begin a new journey to unlock Continue.":
            self.text(screen,self.notice,self.small,(480,499),muted)
        self.text(screen,"ARROWS  Navigate     ENTER  Select     ESC  Back     /     Mouse supported",
                  self.small,(480,524),(188,202,215))
