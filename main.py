
from pathlib import Path
import random
import math

import pygame

pygame.init()

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


pygame.display.set_caption("VOID - Level 1")

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
platform_art = []
for platform, island_index in zip(platforms + [moving_platform], island_order):
    source = island_sources[island_index]
    surface_x, surface_y, surface_width = ISLAND_SURFACES[island_index]
    scale = platform.width * ZOOM / surface_width
    image = scale_alpha(
        source, (round(source.get_width() * scale), round(source.get_height() * scale))
    )
    platform_art.append((image, round(surface_x * scale), round(surface_y * scale)))


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

while running:
    dt = clock.tick(60) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()

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

    dx = 0

    if keys[pygame.K_a]:
        dx -= speed
        facing_right = False

    if keys[pygame.K_d]:
        dx += speed
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

    if keys[pygame.K_SPACE] and on_ground:
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

    screen.blit(background, background_rect)
    for firefly in fireflies:
        firefly.update(min(dt, 0.05))
        if not firefly.foreground:
            firefly.draw(camera_x, camera_y)

    for platform, art in zip(platforms, platform_art):
        draw_island(platform, art, camera_x, camera_y)
    draw_island(moving_platform, platform_art[-1], camera_x, camera_y)

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
        animation_time += dt

    frames = (animations if facing_right else animations_left)[animation_state]
    frame_number = int(animation_time * ANIMATION_FPS[animation_state])
    if animation_state == "jump":
        # Play the four existing jump poses once, then hold the last until landing.
        frame_number = min(frame_number, len(frames) - 1)
    else:
        animation_time %= len(frames) / ANIMATION_FPS[animation_state]
        frame_number %= len(frames)
    current_image = frames[frame_number]

    draw_x = (
        round((meadow.centerx - camera_x) * ZOOM)
        - current_image.get_width() // 2
    )

    # All poses share a baseline; only drawing changes, never the collider.
    draw_y = (round((meadow.bottom - camera_y) * ZOOM)
              - current_image.get_height())

    screen.blit(current_image, (draw_x, draw_y),
                special_flags=pygame.BLEND_PREMULTIPLIED)
    for firefly in fireflies:
        if firefly.foreground:
            firefly.draw(camera_x, camera_y)

    pygame.display.flip()

pygame.quit()
