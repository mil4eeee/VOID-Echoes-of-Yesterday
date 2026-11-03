
from pathlib import Path
import random
import math

import pygame
from menu_ui import MenuUI, write_json
from memory_fragment import MemoryFragment
from shadow_encounter import CrouchAnimation, ShadowEncounter
from health_healing import Health, HealingOrb, OpeningTutorial
from instruction_ui import draw_instruction
from level_two import LevelTwoStory, LevelTwoCombat, ISLANDS, MOVING, MOVING_LIMITS, WORLD_WIDTH
from narrative import LevelOneNarrative, InputEdges

pygame.display.init()
pygame.font.init()

WIDTH = 960
HEIGHT = 540
LEVEL_WIDTH = 1600
ZOOM = 1.7

screen = pygame.display.set_mode((WIDTH, HEIGHT))
# Visible area in world coordinates; physics stays in world pixels.
VIEW_WIDTH = WIDTH / ZOOM
VIEW_HEIGHT = HEIGHT / ZOOM


def camera_rect(rect, camera_x, camera_y):
    """Project world edges to screen pixels, keeping adjacent edges aligned."""
    left = round((rect.left - camera_x) * ZOOM)
    top = round((rect.top - camera_y) * ZOOM)
    right = round((rect.right - camera_x) * ZOOM)
    bottom = round((rect.bottom - camera_y) * ZOOM)
    return pygame.Rect(left, top, right - left, bottom - top)

def scale_alpha(source, size):
    """Filter color multiplied by alpha to avoid dark transparent-edge halos.

    These surfaces must be drawn with BLEND_PREMULTIPLIED.
    """
    return pygame.transform.smoothscale(source.premul_alpha(), size)


pygame.display.set_caption("Void: Echoes of Yesterday")

# Load once, then scale to cover the window without changing the aspect ratio.
background_path = (Path(__file__).resolve().parent / "assets" / "backgrounds"
                   / "moonlit_forest.png")
background_source = pygame.image.load(str(background_path)).convert()
background_scale = max(WIDTH / background_source.get_width(),
                       HEIGHT / background_source.get_height())
background = pygame.transform.smoothscale(
    background_source,
    (max(WIDTH, round(background_source.get_width() * background_scale)),
     max(HEIGHT, round(background_source.get_height() * background_scale)))
)
background_rect = background.get_rect(center=(WIDTH // 2, HEIGHT // 2))

clock = pygame.time.Clock()

meadow = pygame.Rect(80, 400, 40, 60)

# Each extracted PNG uses the same 280 x 340 canvas and foot baseline.
# Keep the standing character about 100 world pixels tall, preserving aspect ratio.
ASSET_DIR = Path(__file__).resolve().parent / "assets" / "characters" / "meadow"
SPRITE_SCALE = 100 / 320
ANIMATION_FPS = {"idle": 4.0, "run": 12.0, "jump": 8.0}
FRAME_COUNTS = {"idle": 4, "run": 6, "jump": 4}


def load_animation(name, count):
    frames = []
    for number in range(1, count + 1):
        path = ASSET_DIR / name / f"{name}_{number:02d}.png"
        image = pygame.image.load(str(path)).convert_alpha()
        size = (round(image.get_width() * SPRITE_SCALE * ZOOM),
                round(image.get_height() * SPRITE_SCALE * ZOOM))
        frames.append(scale_alpha(image, size))
    return frames


animations = {
    name: load_animation(name, count) for name, count in FRAME_COUNTS.items()
}
# Precompute left-facing frames; no scaling or flipping is needed every frame.
animations_left = {
    name: [pygame.transform.flip(frame, True, False) for frame in frames]
    for name, frames in animations.items()
}
animation_state = "idle"
animation_time = 0.0

facing_right = True

spawn_x = 80
spawn_y = 400

speed = 5
velocity_y = 0.0
gravity = 0.5
jump_strength = -12
on_ground = False

platforms = [
    pygame.Rect(0, 490, random.randint(280, 320), 20),
    pygame.Rect(350, 410, random.randint(200, 240), 20),
    pygame.Rect(620, 330, random.randint(200, 240), 20),
    pygame.Rect(1370, 200, random.randint(180, 220), 20)
]

moving_platform = pygame.Rect(950, 290, random.randint(160, 200), 20)
moving_speed = 2
moving_min_x = 850
moving_max_x = 1190

# Each crop has its own walking-surface anchor (left, top, width).
# Plants and rock beneath that line are decoration, not extra collision shapes.
ISLAND_SURFACES = [(25, 110, 475), (30, 150, 455), (35, 245, 470),
                   (25, 155, 585), (25, 175, 565)]
platform_asset_dir = Path(__file__).resolve().parent / "assets" / "platforms"
island_sources = [
    pygame.image.load(str(platform_asset_dir / f"island_{i:02d}.png")).convert_alpha()
    for i in range(1, 6)
]
# Choose once per launch; neither respawning nor moving the camera reshuffles art.
island_order = random.sample(range(5), 5)
def rebuild_platform_art():
    global platform_art
    platform_art = []
    for platform, island_index in zip(platforms + [moving_platform], island_order):
        source = island_sources[island_index]
        surface_x, surface_y, surface_width = ISLAND_SURFACES[island_index]
        scale = platform.width * ZOOM / surface_width
        image = scale_alpha(
            source, (round(source.get_width() * scale), round(source.get_height() * scale))
        )
        platform_art.append((image, round(surface_x * scale), round(surface_y * scale)))


rebuild_platform_art()


def draw_island(platform, art, camera_x, camera_y):
    image, offset_x, offset_y = art
    screen.blit(image, (round((platform.left - camera_x) * ZOOM) - offset_x,
                        round((platform.top - camera_y) * ZOOM) - offset_y),
                special_flags=pygame.BLEND_PREMULTIPLIED)


# Cosmetic particles use their own RNG, leaving platform randomization alone.
FIREFLY_COUNT = 42
FIREFLY_SPEED = 1.0
firefly_rng = random.Random()
firefly_glows = []
for radius, color in [(6, (150, 225, 105)), (9, (85, 190, 170)),
                      (12, (195, 220, 115))]:
    levels = []
    for level in range(16):
        glow = pygame.Surface((radius * 2 + 1, radius * 2 + 1))
        strength = 0.2 + 0.8 * level / 15
        for y in range(-radius, radius + 1):
            for x in range(-radius, radius + 1):
                distance = math.hypot(x, y)
                # A tiny bright core and a broad, faint halo; black adds nothing.
                intensity = (0.17 * math.exp(-distance * distance / (radius * 0.45)**2)
                             + 0.83 * math.exp(-distance * distance / 1.6))
                glow.set_at((x + radius, y + radius),
                            tuple(round(c * intensity * strength) for c in color))
        levels.append(glow)
    firefly_glows.append(levels)


class Firefly:
    def __init__(self, foreground):
        self.foreground = foreground
        self.x = firefly_rng.uniform(0, WIDTH)
        self.y = firefly_rng.uniform(0, HEIGHT)
        self.vx = firefly_rng.uniform(-7, 7)
        self.vy = firefly_rng.uniform(-5, 2)
        self.phase = firefly_rng.uniform(0, math.tau)
        self.frequency = firefly_rng.uniform(0.7, 1.5)
        self.age = 0.0
        self.depth = firefly_rng.uniform(0.25, 0.4) if foreground else firefly_rng.uniform(0.04, 0.16)
        self.style = 2 if foreground else firefly_rng.randrange(2)

    def update(self, elapsed):
        self.age += elapsed
        self.x = (self.x + self.vx * elapsed * FIREFLY_SPEED) % (WIDTH + 40)
        self.y = (self.y + self.vy * elapsed * FIREFLY_SPEED) % (HEIGHT + 40)

    def draw(self, camera_x, camera_y):
        phase = self.phase + self.age * self.frequency
        x = ((self.x + 8 * math.sin(phase) - camera_x * ZOOM * self.depth)
             % (WIDTH + 40)) - 20
        y = ((self.y + 6 * math.sin(phase * 0.73) - camera_y * ZOOM * self.depth)
             % (HEIGHT + 40)) - 20
        level = round((0.5 + 0.5 * math.sin(phase * 1.3)) * 15)
        glow = firefly_glows[self.style][level]
        screen.blit(glow, glow.get_rect(center=(round(x), round(y))),
                    special_flags=pygame.BLEND_RGB_ADD)


fireflies = [Firefly(foreground=(i % 5 == 0)) for i in range(FIREFLY_COUNT)]

camera_x = 0
camera_y = 0
running = True
project_root = Path(__file__).resolve().parent
menu = MenuUI(project_root, (WIDTH, HEIGHT))
memory_fragment = MemoryFragment(project_root, ZOOM)
crouch = CrouchAnimation(project_root, ZOOM)
shadow = ShadowEncounter(project_root, ZOOM)
health = Health()
healing_orb = HealingOrb(project_root, ZOOM)
opening_tutorial = OpeningTutorial()
story = LevelOneNarrative()
current_level = 1
level2_combat = None
input_edges = InputEdges()
app_state = "menu"
session_active = False
autosave_time = 0.0


def apply_display():
    global screen
    flags = pygame.SCALED | pygame.FULLSCREEN if menu.fullscreen else 0
    try:
        screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    except pygame.error:
        menu.fullscreen = False
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        menu.notice = "Fullscreen unavailable; using windowed mode."


def save_progress():
    data = {"version": 1, "x": meadow.x, "y": meadow.y,
            "velocity_y": velocity_y, "on_ground": on_ground,
            "facing_right": facing_right,
            "widths": [p.width for p in platforms + [moving_platform]],
            "islands": island_order, "moving_x": moving_platform.x,
            "moving_speed": moving_speed,
            "memory_collected": memory_fragment.collected,
            "hp": health.current, "healing_collected": healing_orb.collected,
            "tutorial_seen": not opening_tutorial.active,
            "narrative": story.snapshot(), "level": current_level,
            "duels": level2_combat.snapshot() if level2_combat else []}
    try:
        write_json(menu.save_path, data)
        menu.saved = data
        menu.has_save = True
        menu.notice = "Journey saved."
        return True
    except OSError:
        menu.notice = "Could not save the journey. Check folder write access."
        return False


def configure_level(number):
    global current_level, platforms, moving_platform, moving_min_x, moving_max_x
    global LEVEL_WIDTH, story, level2_combat, spawn_x, spawn_y
    current_level = number
    if number == 2:
        platforms = [pygame.Rect(values) for values in ISLANDS]
        moving_platform = pygame.Rect(MOVING)
        moving_min_x, moving_max_x = MOVING_LIMITS
        LEVEL_WIDTH = WORLD_WIDTH
        story = LevelTwoStory()
        level2_combat = LevelTwoCombat(project_root, ZOOM, platforms)
    else:
        platforms = [pygame.Rect(0,490,300,20), pygame.Rect(350,410,220,20),
                     pygame.Rect(620,330,220,20), pygame.Rect(1370,200,200,20)]
        moving_platform = pygame.Rect(950,290,180,20)
        moving_min_x, moving_max_x = 850,1190
        LEVEL_WIDTH = 1600
        story = LevelOneNarrative()
        level2_combat = None
    spawn_x, spawn_y = 80,400


def start_game(continue_saved=False, level=1, carry_hp=None):
    global velocity_y, on_ground, facing_right, moving_speed, island_order
    global animation_state, animation_time, app_state, session_active, autosave_time
    global camera_x, camera_y
    configure_level(menu.saved.get("level",1) if continue_saved else level)
    if continue_saved:
        data = menu.saved
        meadow.topleft = (data["x"], data["y"])
        velocity_y, on_ground = data["velocity_y"], data["on_ground"]
        facing_right = data["facing_right"]
        widths = data["widths"]
        island_order = list(data["islands"])
        moving_platform.x, moving_speed = data["moving_x"], data["moving_speed"]
    else:
        meadow.topleft = (spawn_x, spawn_y)
        velocity_y, on_ground, facing_right = 0.0, False, True
        widths = [random.randint(lo, hi) for lo, hi in
                  [(280,320),(200,240),(200,240),(180,220),(160,200)]]
        island_order = random.sample(range(5), 5)
        moving_platform.x, moving_speed = 950, 2
    if current_level == 2 and not continue_saved:
        widths = [p.width for p in platforms + [moving_platform]]
        moving_platform.x = MOVING[0]
        island_order = [0,4,4,1,3]
    for platform, width in zip(platforms + [moving_platform], widths):
        platform.width = width
    rebuild_platform_art()
    # Older saves have no fragment field and start with the fragment available.
    memory_fragment.reset(continue_saved and menu.saved.get("memory_collected") is True)
    health.reset(menu.saved.get("hp", Health.START_HP) if continue_saved else Health.START_HP)
    if carry_hp is not None:
        health.reset(carry_hp)
    if health.current == 0:
        health.reset()
        meadow.topleft = (spawn_x, spawn_y)
        velocity_y, on_ground = 0.0, False
    healing_orb.reset(continue_saved and menu.saved.get("healing_collected") is True)
    opening_tutorial.reset(continue_saved and menu.saved.get("tutorial_seen") is True)
    if current_level == 2:
        healing_orb.reset(True)
        opening_tutorial.reset(True)
        if continue_saved:
            level2_combat.restore(menu.saved.get('duels'))
    crouch.reset()
    shadow.reset()
    animation_state, animation_time = "idle", 0.0
    autosave_time = 0.0
    app_state, session_active = "game", True
    menu.notice = ""
    story.reset(menu.saved.get("narrative") if continue_saved else None,
                legacy=continue_saved and "narrative" not in menu.saved,
                healed=healing_orb.collected, memory=memory_fragment.collected)
    if story.dialogue.scene == 'shadow_before' and story.blocked:
        shadow.state = 'warning'
        shadow.x, shadow.y = platforms[1].right+45, platforms[1].top-90
    if not continue_saved:
        meadow.bottom = platforms[0].top
        velocity_y, on_ground = 0.0, True
    camera_x = max(0, min(meadow.centerx - VIEW_WIDTH / 2, max(0, LEVEL_WIDTH - VIEW_WIDTH)))
    camera_y = max(0, min(meadow.bottom - 50 - VIEW_HEIGHT / 2, max(0, HEIGHT - VIEW_HEIGHT)))
    if not continue_saved:
        save_progress()


if menu.fullscreen:
    apply_display()

while running:
    dt = clock.tick(60) / 1000.0

    interact_pressed = False
    attack_pressed = False
    story.input_used = False
    world_was_blocked = story.blocked
    for event in pygame.event.get():
        fresh = input_edges.consume(event)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_e, pygame.K_f, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE) and not fresh:
            continue
        if event.type == pygame.QUIT:
            running = False
        elif app_state == "game":
            if story.phase == "chapter":
                if ((event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE))
                        or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                            and story.return_button(screen.get_size()).collidepoint(event.pos))):
                    save_progress()
                    menu.open("main")
                    app_state = "menu"
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                story.advance()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_e and not world_was_blocked and not story.blocked:
                interact_pressed = True
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_f and not world_was_blocked and not story.blocked:
                attack_pressed = True
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                save_progress()
                menu.pause_image = screen.copy()
                menu.open("pause")
                app_state = "menu"
        else:
            action = menu.event(event)
            if action == "new":
                start_game()
            elif action == "continue" and menu.has_save:
                start_game(continue_saved=True)
            elif action == "resume":
                app_state = "game"
            elif action == "save_menu":
                if save_progress():
                    menu.open("main")
            elif action == "display":
                apply_display()
            elif action == "quit":
                running = False

    if not running:
        break
    if app_state == "menu":
        menu.draw(screen)
        pygame.display.flip()
        continue

    # Dialogue/cutscenes freeze physics, moving platforms, combat, and interactions.
    if story.phase == 'heal_pickup':
        healing_orb.update(dt, meadow, platforms[0], False, health)
    if story.phase == 'gold_flash':
        memory_fragment.update(dt, meadow, platforms[-1], False)
    if story.phase == 'shadow_tutorial':
        held = pygame.key.get_pressed()
        crouch.update(dt, held[pygame.K_s] or held[pygame.K_DOWN], True)
        story.practice_crouch(crouch)
    story.update(dt, healing_orb)
    if current_level == 1 and story.phase == 'chapter':
        start_game(level=2, carry_hp=health.current)
        world_was_blocked = True
    story.poll(meadow, platforms + [moving_platform], healing_orb, memory_fragment, shadow)
    if story.restart_tutorial:
        opening_tutorial.reset(False)
        story.restart_tutorial = False
    if story.dialogue.scene == 'healing_intro' or 'healing_intro' in story.completed:
        opening_tutorial.reset(True)
    dx = 0
    respawned = False
    gameplay_allowed = not story.blocked and not world_was_blocked
    game_dt = dt if gameplay_allowed else 0.0
    if gameplay_allowed:
        keys = pygame.key.get_pressed()
        health.update(dt)
        opening_tutorial.update(dt)

        old_platform_x = moving_platform.x
        moving_platform.x += moving_speed

        if moving_platform.x >= moving_max_x:
            moving_platform.x = moving_max_x
            moving_speed = -abs(moving_speed)

        elif moving_platform.x <= moving_min_x:
            moving_platform.x = moving_min_x
            moving_speed = abs(moving_speed)

        platform_dx = moving_platform.x - old_platform_x

        if (
            on_ground
            and meadow.bottom == moving_platform.top
            and meadow.right > old_platform_x
            and meadow.left < old_platform_x + moving_platform.width
        ):
            meadow.x += platform_dx

        # S / Down lowers the combat hurtbox while terrain physics remains stable.
        grounded_before_move = velocity_y >= 0 and any(
            meadow.bottom == p.top and meadow.right > p.left and meadow.left < p.right
            for p in platforms + [moving_platform]
        )
        crouch.update(dt, keys[pygame.K_s] or keys[pygame.K_DOWN], grounded_before_move)
        move_speed = 2 if crouch.active else speed
        dx = 0

        if keys[pygame.K_a]:
            dx -= move_speed
            facing_right = False

        if keys[pygame.K_d]:
            dx += move_speed
            facing_right = True

        before_move_x = meadow.x
        meadow.x += dx

        all_platforms = platforms + [moving_platform]

        for platform in all_platforms:
            if meadow.colliderect(platform):
                if dx > 0:
                    meadow.right = platform.left
                elif dx < 0:
                    meadow.left = platform.right

        meadow.left = max(0, meadow.left)
        meadow.right = min(LEVEL_WIDTH, meadow.right)

        if keys[pygame.K_SPACE] and on_ground and not crouch.active:
            velocity_y = jump_strength
            on_ground = False

        velocity_y += gravity

        previous_top = meadow.top
        previous_bottom = meadow.bottom

        meadow.y += round(velocity_y)
        on_ground = False

        for platform in all_platforms:
            if meadow.colliderect(platform):
                if velocity_y >= 0 and previous_bottom <= platform.top:
                    meadow.bottom = platform.top
                    velocity_y = 0
                    on_ground = True

                elif velocity_y < 0 and previous_top >= platform.bottom:
                    meadow.top = platform.bottom
                    velocity_y = 0

        respawned = False
        if meadow.top > HEIGHT:
            respawned = True
            meadow.x = spawn_x
            meadow.y = spawn_y
            velocity_y = 0
            on_ground = False

        if respawned:
            if level2_combat:
                level2_combat.respawn()
            crouch.reset()
            shadow.reset()
        grounded_now = velocity_y >= 0 and any(
            meadow.bottom == p.top and meadow.right > p.left and meadow.left < p.right
            for p in all_platforms
        )
        if not grounded_now:
            crouch.reset()
        # The second island is the first encounter; the opening tutorial is protected.
        shadow_hit = False
        if not opening_tutorial.active:
            shadow_hit = shadow.update(dt, meadow, crouch.hurtbox(meadow), platforms[1 if current_level == 1 else 2])
        if level2_combat:
            if level2_combat.update(dt, meadow, facing_right, attack_pressed, health,
                                    shadow.state in ('warning','fly')):
                story.dirty = True
            if health.current == 0:
                shadow_hit = True
                level2_combat.respawn()
        if shadow_hit:
            health.damage(Health.SHADOW_DAMAGE)
            if health.current == 0:
                health.reset()  # A depleted life respawns with the starting 75 HP.
            meadow.topleft = (spawn_x, spawn_y)
            velocity_y, on_ground = 0.0, False
            respawned = True
            crouch.reset()
            animation_time = 0.0
            if level2_combat:
                level2_combat.respawn()

        camera_x = max(
            0,
            min(
                meadow.centerx - VIEW_WIDTH / 2,
                max(0, LEVEL_WIDTH - VIEW_WIDTH)
            )
        )

        # Follow the visual body vertically and clamp to the existing level bounds.
        camera_y = max(
            0,
            min(meadow.bottom - 50 - VIEW_HEIGHT / 2, max(0, HEIGHT - VIEW_HEIGHT))
        )

        if healing_orb.update(dt, meadow, platforms[0],
                              interact_pressed and 'healing_intro' in story.completed, health):
            story.on_heal()
            interact_pressed = False
            save_progress()  # Commit HP and the consumed orb together.

        if memory_fragment.update(dt, meadow, platforms[-1],
                                  interact_pressed and 'memory_intro' in story.completed and not story.blocked
                                  and (not level2_combat or level2_combat.cleared)):
            story.on_memory()
            interact_pressed = False
            save_progress()  # Persist the pickup immediately, not at the next autosave.

        if interact_pressed and not story.blocked and story.portal_near(meadow, platforms[-1]):
            story.set_phase('exit_fade')

    if not gameplay_allowed:
        health.update_display(dt)
    screen.blit(background, background_rect)
    for firefly in (fireflies if menu.fireflies else []):
        firefly.update(min(game_dt, 0.05))
        if not firefly.foreground:
            firefly.draw(camera_x, camera_y)

    for platform, art in zip(platforms, platform_art):
        draw_island(platform, art, camera_x, camera_y)
    draw_island(moving_platform, platform_art[-1], camera_x, camera_y)

    memory_fragment.draw(screen, camera_x, camera_y, show_prompt=not story.blocked and "memory_intro" in story.completed
                         and (not level2_combat or level2_combat.cleared))
    story.draw_portal(screen, platforms[-1], camera_x, camera_y, ZOOM, meadow)
    healing_orb.draw(screen, camera_x, camera_y, show_prompt=not story.blocked and "healing_intro" in story.completed)

    # Rounded gravity can clear on_ground for a frame despite exact contact.
    # This check affects drawing only, leaving collision and physics intact.
    supported = on_ground or (
        velocity_y >= 0
        and any(
            meadow.bottom == platform.top
            and meadow.right > platform.left
            and meadow.left < platform.right
            for platform in all_platforms
        )
    )
    # Airborne takes priority over directional input. Riding a platform is idle.
    if not supported:
        next_state = "jump"
    elif dx != 0 and meadow.x != before_move_x:
        next_state = "run"
    else:
        next_state = "idle"

    if next_state != animation_state or respawned:
        animation_state = next_state
        animation_time = 0.0
    else:
        animation_time += game_dt

    frames = (animations if facing_right else animations_left)[animation_state]
    frame_number = int(animation_time * ANIMATION_FPS[animation_state])
    if animation_state == "jump":
        # Play the four existing jump poses once, then hold the last until landing.
        frame_number = min(frame_number, len(frames) - 1)
    else:
        animation_time %= len(frames) / ANIMATION_FPS[animation_state]
        frame_number %= len(frames)
    current_image = frames[frame_number]
    if crouch.active and supported:
        current_image = crouch.image(facing_right)

    draw_x = (
        round((meadow.centerx - camera_x) * ZOOM)
        - current_image.get_width() // 2
    )

    # All poses share a baseline; only drawing changes, never the collider.
    draw_y = (round((meadow.bottom - camera_y) * ZOOM)
              - current_image.get_height())

    screen.blit(current_image, (draw_x, draw_y),
                special_flags=pygame.BLEND_PREMULTIPLIED)
    for firefly in (fireflies if menu.fireflies else []):
        if firefly.foreground:
            firefly.draw(camera_x, camera_y)

    if level2_combat:
        level2_combat.draw(screen, meadow, facing_right, camera_x, camera_y,
                          shadow.state in ('warning','fly'))
        if not level2_combat.cleared and memory_fragment.near:
            draw_instruction(screen, opening_tutorial.font,
                             ['Defeat both duel shadows', 'to claim this memory'], (WIDTH//2,180))
    shadow.draw(screen, camera_x, camera_y)
    health.draw(screen)
    memory_fragment.draw_hud(screen)
    if not story.blocked:
        opening_tutorial.draw(screen, healing_orb, health,
                              shadow.state in ('warning', 'fly') or shadow.hit_notice > 0,
                              anchor=(round((meadow.centerx-camera_x)*ZOOM),
                                      round((meadow.bottom-105-camera_y)*ZOOM)))
        if current_level == 1:
            shadow.draw_hint(screen)
    if story.phase == 'shadow_tutorial':
        draw_instruction(screen, opening_tutorial.font,
                         ['Shadow approaching!', 'Hold S or DOWN to crouch'],
                         (round((meadow.centerx-camera_x)*ZOOM),
                          round((meadow.bottom-105-camera_y)*ZOOM)))
    story.draw(screen)
    if story.dirty:
        if save_progress():
            story.dirty = False

    autosave_time += game_dt
    if autosave_time >= 10.0:
        save_progress()
        autosave_time = 0.0

    pygame.display.flip()

if session_active:
    save_progress()
pygame.quit()
