import sys
import math
import random
import os
import array
import pygame

# -----------------------------------------------------------------------------
# GLOBAL CONSTANTS & CONFIGURATION
# -----------------------------------------------------------------------------
SCREEN_WIDTH = 900
SCREEN_HEIGHT = 400
FPS = 60

GROUND_Y = 320
INITIAL_SPEED = 360.0  # Pixels per second
MAX_SPEED = 950.0
SPEED_ACCELERATION = 0.15  # Speed increase per score point

# Palette Definitions
COLOR_DAY_BG = (247, 247, 247)
COLOR_DAY_FG = (83, 83, 83)
COLOR_DAY_ACCENT = (115, 115, 115)

COLOR_NIGHT_BG = (30, 30, 34)
COLOR_NIGHT_FG = (220, 220, 220)
COLOR_NIGHT_ACCENT = (160, 160, 170)

# -----------------------------------------------------------------------------
# SOUND SYNTHESIS SYSTEM (No external WAV files needed)
# -----------------------------------------------------------------------------
class SoundManager:
    def __init__(self):
        self.enabled = False
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.enabled = True
            self.sfx_jump = self._synth_sound(lambda t: 300 + t * 1200, 0.12, 0.3)
            self.sfx_duck = self._synth_sound(lambda t: 250 - t * 800, 0.08, 0.25)
            self.sfx_milestone = self._synth_milestone()
            self.sfx_hit = self._synth_sound(lambda t: max(50, 180 - t * 1000) + random.uniform(-30, 30), 0.25, 0.4)
        except Exception:
            self.enabled = False

    def _synth_sound(self, freq_func, duration, volume=0.3, sample_rate=22050):
        num_samples = int(sample_rate * duration)
        buf = array.array('h')
        for i in range(num_samples):
            t = i / sample_rate
            freq = freq_func(t)
            # Envelope (fade out near end)
            env = 1.0 - (i / num_samples)
            sample = int(volume * env * 32767.0 * math.sin(2.0 * math.pi * freq * t))
            buf.append(sample)  # Left
            buf.append(sample)  # Right
        return pygame.mixer.Sound(buffer=buf)

    def _synth_milestone(self, sample_rate=22050):
        # Two high notes (Arpeggio)
        duration = 0.2
        num_samples = int(sample_rate * duration)
        buf = array.array('h')
        for i in range(num_samples):
            t = i / sample_rate
            freq = 784.0 if t < 0.1 else 1046.5  # G5 then C6
            env = 1.0 - (t / duration)
            sample = int(0.3 * env * 32767.0 * math.sin(2.0 * math.pi * freq * t))
            buf.append(sample)
            buf.append(sample)
        return pygame.mixer.Sound(buffer=buf)

    def play(self, sound_name):
        if not self.enabled:
            return
        sound = getattr(self, f"sfx_{sound_name}", None)
        if sound:
            sound.play()

# -----------------------------------------------------------------------------
# HIGH SCORE PERSISTENCE
# -----------------------------------------------------------------------------
SAVE_FILE = "dino_highscore.txt"

def load_high_score():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                return int(f.read().strip())
        except Exception:
            return 0
    return 0

def save_high_score(score):
    try:
        with open(SAVE_FILE, "w") as f:
            f.write(str(int(score)))
    except Exception:
        pass

# -----------------------------------------------------------------------------
# PLAYER SUBSYSTEM (DINO)
# -----------------------------------------------------------------------------
class Dino:
    def __init__(self, x, y):
        self.base_x = x
        self.ground_y = y
        self.x = x
        self.vy = 0.0

        # Physics variables
        self.gravity = 2200.0
        self.jump_impulse = -720.0
        self.fast_fall_gravity = 5000.0
        self.is_grounded = True
        self.jump_lock = False

        # State Machine: 'IDLE', 'RUNNING', 'JUMPING', 'DUCKING', 'DEAD'
        self.state = 'IDLE'

        # Animation tracking
        self.anim_timer = 0.0
        self.anim_frame = 0

        # Dynamic Dimensions
        self.stand_width = 44
        self.stand_height = 52
        self.duck_width = 58
        self.duck_height = 30

        self.width = self.stand_width
        self.height = self.stand_height
        self.y = self.ground_y - self.height

    def handle_input(self, keys_pressed, sound_mgr, dt):
        jump_key = keys_pressed[pygame.K_SPACE] or keys_pressed[pygame.K_UP]
        duck_key = keys_pressed[pygame.K_DOWN]

        if self.jump_lock:
            if not jump_key:
                self.jump_lock = False
            jump_key = False

        if self.state in ('DEAD', 'IDLE'):
            return

        prev_state = self.state

        if self.is_grounded:
            if jump_key:
                self.vy = self.jump_impulse
                self.is_grounded = False
                self.state = 'JUMPING'
                sound_mgr.play('jump')
            elif duck_key:
                self.state = 'DUCKING'
                if prev_state != 'DUCKING':
                    sound_mgr.play('duck')
            else:
                self.state = 'RUNNING'
        else:
            # Variable Jump Height
            if not jump_key and self.vy < 0:
                self.vy += 1200.0 * dt

            if duck_key:
                self.state = 'DUCKING'
                if prev_state != 'DUCKING':
                    sound_mgr.play('duck')
            else:
                self.state = 'JUMPING'

    def update(self, dt):
        if self.state == 'DEAD':
            return

        prev_height = self.height

        # Dimensions based on ducking state
        if self.state == 'DUCKING':
            self.width = self.duck_width
            self.height = self.duck_height
        else:
            self.width = self.stand_width
            self.height = self.stand_height

        # Gravity & Physics
        if not self.is_grounded:
            self.y += (prev_height - self.height)
            current_gravity = self.fast_fall_gravity if self.state == 'DUCKING' else self.gravity
            self.vy += current_gravity * dt
            self.y += self.vy * dt

            if self.y >= self.ground_y - self.height:
                self.y = self.ground_y - self.height
                self.vy = 0.0
                self.is_grounded = True
                self.state = 'DUCKING' if pygame.key.get_pressed()[pygame.K_DOWN] else 'RUNNING'
        else:
            self.y = self.ground_y - self.height

        # Animation frame update
        if self.state != 'IDLE':
            self.anim_timer += dt
            if self.anim_timer >= 0.1:
                self.anim_timer = 0.0
                self.anim_frame = (self.anim_frame + 1) % 2

    @property
    def hitbox(self):
        # Padding for forgiving collision detection
        pad_x = 4
        pad_y = 4
        return pygame.Rect(
            self.x + pad_x,
            self.y + pad_y,
            max(1, self.width - pad_x * 2),
            max(1, self.height - pad_y * 2)
        )

    def draw(self, surface, color):
        x, y = int(self.x), int(self.y)

        if self.state == 'DEAD':
            # Draw Dead Dino (Standing pose with X eye)
            # Body
            pygame.draw.rect(surface, color, (x + 12, y + 16, 24, 22))
            # Head
            pygame.draw.rect(surface, color, (x + 20, y, 22, 18))
            # Eye (X mark)
            ex, ey = x + 32, y + 4
            pygame.draw.line(surface, COLOR_DAY_BG if color == COLOR_DAY_FG else COLOR_NIGHT_BG, (ex, ey), (ex + 4, ey + 4), 2)
            pygame.draw.line(surface, COLOR_DAY_BG if color == COLOR_DAY_FG else COLOR_NIGHT_BG, (ex + 4, ey), (ex, ey + 4), 2)
            # Legs
            pygame.draw.rect(surface, color, (x + 16, y + 38, 4, 14))
            pygame.draw.rect(surface, color, (x + 28, y + 38, 4, 14))
            # Arm
            pygame.draw.rect(surface, color, (x + 26, y + 22, 6, 4))
            return

        if self.state == 'IDLE':
            # Idle Dino (standing baseline, no leg movement)
            pygame.draw.rect(surface, color, (x + 20, y, 22, 18))
            pygame.draw.rect(surface, COLOR_DAY_BG if color == COLOR_DAY_FG else COLOR_NIGHT_BG, (x + 32, y + 4, 4, 4))
            pygame.draw.rect(surface, color, (x + 10, y + 16, 24, 22))
            pygame.draw.rect(surface, color, (x + 2, y + 20, 10, 10))
            pygame.draw.rect(surface, color, (x + 26, y + 20, 6, 4))
            pygame.draw.rect(surface, color, (x + 14, y + 38, 4, 14))
            pygame.draw.rect(surface, color, (x + 26, y + 38, 4, 14))
            return

        if self.state == 'DUCKING':
            # Ducking Dino
            # Body
            pygame.draw.rect(surface, color, (x, y + 10, 42, 16))
            # Head (extended right)
            pygame.draw.rect(surface, color, (x + 36, y + 4, 22, 14))
            # Eye
            pygame.draw.rect(surface, COLOR_DAY_BG if color == COLOR_DAY_FG else COLOR_NIGHT_BG, (x + 48, y + 6, 4, 4))
            # Tail
            pygame.draw.rect(surface, color, (x - 6, y + 10, 8, 8))
            # Legs alternating
            if self.anim_frame == 0:
                pygame.draw.rect(surface, color, (x + 10, y + 26, 6, 4))
                pygame.draw.rect(surface, color, (x + 28, y + 26, 6, 4))
            else:
                pygame.draw.rect(surface, color, (x + 16, y + 26, 6, 4))
                pygame.draw.rect(surface, color, (x + 34, y + 26, 6, 4))
        else:
            # Standing / Running / Jumping Dino
            # Head
            pygame.draw.rect(surface, color, (x + 20, y, 22, 18))
            # Eye
            pygame.draw.rect(surface, COLOR_DAY_BG if color == COLOR_DAY_FG else COLOR_NIGHT_BG, (x + 32, y + 4, 4, 4))
            # Body
            pygame.draw.rect(surface, color, (x + 10, y + 16, 24, 22))
            # Tail
            pygame.draw.rect(surface, color, (x + 2, y + 20, 10, 10))
            # Arms
            pygame.draw.rect(surface, color, (x + 26, y + 20, 6, 4))

            # Legs logic
            if not self.is_grounded:
                pygame.draw.rect(surface, color, (x + 14, y + 38, 4, 10))
                pygame.draw.rect(surface, color, (x + 26, y + 38, 4, 10))
            else:
                if self.anim_frame == 0:
                    pygame.draw.rect(surface, color, (x + 14, y + 38, 4, 14))
                    pygame.draw.rect(surface, color, (x + 26, y + 38, 8, 4))
                else:
                    pygame.draw.rect(surface, color, (x + 14, y + 38, 8, 4))
                    pygame.draw.rect(surface, color, (x + 26, y + 38, 4, 14))

# -----------------------------------------------------------------------------
# OBSTACLE SUBSYSTEM
# -----------------------------------------------------------------------------
class Obstacle:
    def __init__(self, x, y, width, height, obstacle_type, num_stems=1):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.type = obstacle_type  # 'cactus_small', 'cactus_large', 'pterodactyl'
        self.num_stems = num_stems
        self.alive = True
        self.velocity = 0.0
        self.anim_timer = 0.0
        self.anim_frame = 0

    def isOffScreen(self):
        return self.x + self.width < -50

    def update(self, dt, speed):
        self.velocity = speed
        self.x -= self.velocity * dt
        if self.isOffScreen():
            self.alive = False

        self.anim_timer += dt
        if self.anim_timer >= 0.15:
            self.anim_timer = 0.0
            self.anim_frame = (self.anim_frame + 1) % 2

    @property
    def hitbox(self):
        pad = 4
        return pygame.Rect(
            self.x + pad,
            self.y + pad,
            max(1, self.width - pad * 2),
            max(1, self.height - pad * 2)
        )

    def render(self, surface, color):
        pass

    draw = render


class GroundObstacle(Obstacle):
    def render(self, surface, color):
        x, y = int(self.x), int(self.y)
        num_stems = max(1, self.num_stems)
        stem_w = self.width // num_stems
        for i in range(num_stems):
            sx = x + i * stem_w
            # Main trunk
            pygame.draw.rect(surface, color, (sx + 4, y, max(1, stem_w - 8), self.height))
            # Side arms
            pygame.draw.rect(surface, color, (sx, y + 10, 4, 12))
            pygame.draw.rect(surface, color, (sx + max(0, stem_w - 4), y + 6, 4, 12))


class AirObstacle(Obstacle):
    def render(self, surface, color):
        x, y = int(self.x), int(self.y)
        # Body
        pygame.draw.rect(surface, color, (x + 16, y + 12, 22, 10))
        # Head & Beak aligned within bounds
        pygame.draw.rect(surface, color, (x + 6, y + 8, 12, 8))
        pygame.draw.rect(surface, color, (x, y + 12, 8, 4))

        # Wings animation
        if self.anim_frame == 0:
            # Wings Up
            pygame.draw.polygon(surface, color, [(x + 24, y + 12), (x + 16, y - 10), (x + 34, y + 12)])
        else:
            # Wings Down
            pygame.draw.polygon(surface, color, [(x + 24, y + 12), (x + 16, y + 26), (x + 34, y + 12)])


class ObstacleManager:
    def __init__(self):
        self.obstacles = []
        self.pool = []
        self.min_spawn_distance = 320
        self.time_since_last_spawn = 0.0

    def reset(self):
        for obs in self.obstacles:
            obs.alive = False
            self.pool.append(obs)
        self.obstacles.clear()
        self.time_since_last_spawn = 0.0

    def get_obstacle(self, x, y, width, height, obstacle_type, num_stems=1):
        cls = AirObstacle if obstacle_type == 'pterodactyl' else GroundObstacle
        for i, obs in enumerate(self.pool):
            if isinstance(obs, cls):
                self.pool.pop(i)
                obs.x = x
                obs.y = y
                obs.width = width
                obs.height = height
                obs.type = obstacle_type
                obs.num_stems = num_stems
                obs.alive = True
                obs.anim_timer = 0.0
                obs.anim_frame = 0
                return obs
        return cls(x, y, width, height, obstacle_type, num_stems)

    def update(self, dt, current_speed, score):
        self.time_since_last_spawn += dt

        # Spawn logic based on distance & time interval
        can_spawn = False
        if not self.obstacles:
            can_spawn = True
        else:
            last_obstacle = self.obstacles[-1]
            if (SCREEN_WIDTH - last_obstacle.x) >= max(self.min_spawn_distance, current_speed * 0.75):
                can_spawn = True

        if can_spawn and self.time_since_last_spawn >= 0.6 and random.random() < 0.03:
            self.spawn_obstacle(score)
            self.time_since_last_spawn = 0.0

        # Update existing obstacles and recycle dead ones into object pool
        active_obstacles = []
        for obs in self.obstacles:
            obs.update(dt, current_speed)
            if obs.alive:
                active_obstacles.append(obs)
            else:
                self.pool.append(obs)
        self.obstacles = active_obstacles

    def spawn_obstacle(self, score):
        # Pterodactyls appear only after reaching 150 points
        allow_air = score > 150
        choice = random.choice(['cactus_small', 'cactus_large', 'pterodactyl'] if allow_air else ['cactus_small', 'cactus_large'])

        if choice == 'cactus_small':
            count = random.randint(1, 3)
            w = 16 * count + 6
            h = 36
            obs = self.get_obstacle(SCREEN_WIDTH + 20, GROUND_Y - h, w, h, 'cactus_small', num_stems=count)
        elif choice == 'cactus_large':
            count = random.randint(1, 2)
            w = 24 * count + 8
            h = 50
            obs = self.get_obstacle(SCREEN_WIDTH + 20, GROUND_Y - h, w, h, 'cactus_large', num_stems=count)
        else:
            # Pterodactyl altitude options: High (jump safe), Mid (duck or jump), Low (must jump)
            altitudes = [GROUND_Y - 32, GROUND_Y - 58, GROUND_Y - 85]
            y_pos = random.choice(altitudes)
            obs = self.get_obstacle(SCREEN_WIDTH + 20, y_pos, 42, 30, 'pterodactyl', num_stems=1)

        self.obstacles.append(obs)

# -----------------------------------------------------------------------------
# ENVIRONMENT & SCROLLING PARALLAX SYSTEM
# -----------------------------------------------------------------------------
class Environment:
    def __init__(self):
        self.ground_x = 0.0
        # Generate static ground detail dots
        self.ground_bumps = [(random.randint(0, SCREEN_WIDTH * 2), random.randint(4, 25)) for _ in range(60)]

        # Parallax Clouds
        self.clouds = []
        for _ in range(5):
            self.clouds.append([random.randint(0, SCREEN_WIDTH), random.randint(30, 130), random.uniform(0.15, 0.35)])

        # Parallax Stars (For Night Mode)
        self.stars = [(random.randint(0, SCREEN_WIDTH), random.randint(10, 160), random.randint(1, 3)) for _ in range(30)]

    def update(self, dt, speed):
        # Ground movement
        self.ground_x = (self.ground_x - speed * dt) % SCREEN_WIDTH

        # Cloud movement
        for cloud in self.clouds:
            cloud[0] -= speed * cloud[2] * dt
            if cloud[0] < -80:
                cloud[0] = SCREEN_WIDTH + random.randint(10, 100)
                cloud[1] = random.randint(30, 130)

    def draw(self, surface, fg_color, bg_color, is_night):
        # Draw Moon / Stars if night
        if is_night:
            for sx, sy, size in self.stars:
                pygame.draw.rect(surface, fg_color, (sx, sy, size, size))
            # Crescent Moon
            pygame.draw.circle(surface, fg_color, (SCREEN_WIDTH - 100, 60), 16)
            pygame.draw.circle(surface, bg_color, (SCREEN_WIDTH - 108, 56), 14)

        # Draw Parallax Clouds
        for cx, cy, _ in self.clouds:
            x = int(cx)
            pygame.draw.rect(surface, fg_color, (x, cy, 40, 10))
            pygame.draw.rect(surface, fg_color, (x + 10, cy - 8, 20, 8))

        # Main Ground Line
        pygame.draw.line(surface, fg_color, (0, GROUND_Y), (SCREEN_WIDTH, GROUND_Y), 2)

        # Ground bumps detail scrolling
        for bx, offset in self.ground_bumps:
            render_x = (bx + self.ground_x) % SCREEN_WIDTH
            pygame.draw.rect(surface, fg_color, (render_x, GROUND_Y + offset, 3, 2))

# -----------------------------------------------------------------------------
# MAIN GAME ENGINE & STATE MANAGER
# -----------------------------------------------------------------------------
class GameEngine:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Dino Runner")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()

        # Audio and Persistence
        self.sound_mgr = SoundManager()
        self.high_score = load_high_score()

        # Font
        self.font = pygame.font.SysFont("monospace", 18, bold=True)
        self.big_font = pygame.font.SysFont("monospace", 32, bold=True)

        # Entities & Systems
        self.dino = Dino(80, GROUND_Y)
        self.obstacle_mgr = ObstacleManager()
        self.environment = Environment()

        # Game Loop Variables
        self.state = 'START_MENU'  # 'START_MENU', 'PLAYING', 'PAUSED', 'GAME_OVER'
        self.score = 0.0
        self.speed = INITIAL_SPEED
        self.last_milestone = 0

    def reset_game(self):
        self.dino = Dino(80, GROUND_Y)
        self.dino.state = 'RUNNING'
        self.dino.jump_lock = True
        self.obstacle_mgr.reset()
        self.score = 0.0
        self.speed = INITIAL_SPEED
        self.last_milestone = 0
        self.state = 'PLAYING'

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0  # Delta time in seconds
            dt = min(dt, 0.05)  # Cap delta time to prevent clipping during hitches

            self.handle_events()
            self.update(dt)
            self.render()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

                if self.state == 'START_MENU':
                    if event.key in (pygame.K_SPACE, pygame.K_UP):
                        self.reset_game()

                elif self.state == 'PLAYING':
                    if event.key == pygame.K_p:
                        self.state = 'PAUSED'

                elif self.state == 'PAUSED':
                    if event.key == pygame.K_p:
                        self.state = 'PLAYING'

                elif self.state == 'GAME_OVER':
                    if event.key in (pygame.K_r, pygame.K_SPACE, pygame.K_UP):
                        self.reset_game()

    def update(self, dt):
        if self.state != 'PLAYING':
            return

        # Continuous Score & Difficulty Progression
        self.score += dt * 10.0
        self.speed = min(MAX_SPEED, INITIAL_SPEED + (self.score * SPEED_ACCELERATION))

        # Milestone SFX Trigger (Every 100 Points)
        current_milestone = int(self.score) // 100
        if current_milestone > self.last_milestone:
            self.last_milestone = current_milestone
            self.sound_mgr.play('milestone')

        # Update Player Input & Physics
        keys = pygame.key.get_pressed()
        self.dino.handle_input(keys, self.sound_mgr, dt)
        self.dino.update(dt)

        # Update Obstacles & Environment
        self.obstacle_mgr.update(dt, self.speed, int(self.score))
        self.environment.update(dt, self.speed)

        # AABB Collision Detection
        dino_rect = self.dino.hitbox
        for obs in self.obstacle_mgr.obstacles:
            if dino_rect.colliderect(obs.hitbox):
                self.trigger_game_over()
                break

    def trigger_game_over(self):
        self.state = 'GAME_OVER'
        self.dino.state = 'DEAD'
        self.sound_mgr.play('hit')

        if int(self.score) > self.high_score:
            self.high_score = int(self.score)
            save_high_score(self.high_score)

    def render(self):
        # Day/Night Cycle (Switches theme every 500 points)
        is_night = (int(self.score) // 500) % 2 == 1
        bg_color = COLOR_NIGHT_BG if is_night else COLOR_DAY_BG
        fg_color = COLOR_NIGHT_FG if is_night else COLOR_DAY_FG
        accent_color = COLOR_NIGHT_ACCENT if is_night else COLOR_DAY_ACCENT

        self.screen.fill(bg_color)

        # Render Environment & World
        self.environment.draw(self.screen, fg_color, bg_color, is_night)

        # Render Obstacles & Dino
        for obs in self.obstacle_mgr.obstacles:
            obs.render(self.screen, fg_color)
        self.dino.draw(self.screen, fg_color)

        # Render HUD (Heads-Up Display)
        score_str = f"HI {self.high_score:05d}  {int(self.score):05d}"
        score_surface = self.font.render(score_str, True, fg_color)
        self.screen.blit(score_surface, (SCREEN_WIDTH - 220, 20))

        # Render State Overlays
        if self.state == 'START_MENU':
            title_surf = self.big_font.render("D I N O  R U N N E R", True, fg_color)
            prompt_surf = self.font.render("Press SPACE or UP to Jump", True, accent_color)
            self.screen.blit(title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 110))
            self.screen.blit(prompt_surf, (SCREEN_WIDTH // 2 - prompt_surf.get_width() // 2, 170))

        elif self.state == 'PAUSED':
            pause_surf = self.big_font.render("P A U S E D", True, fg_color)
            prompt_surf = self.font.render("Press P to Resume", True, accent_color)
            self.screen.blit(pause_surf, (SCREEN_WIDTH // 2 - pause_surf.get_width() // 2, 120))
            self.screen.blit(prompt_surf, (SCREEN_WIDTH // 2 - prompt_surf.get_width() // 2, 170))

        elif self.state == 'GAME_OVER':
            go_surf = self.big_font.render("G A M E  O V E R", True, fg_color)
            score_summary_surf = self.font.render(f"FINAL SCORE: {int(self.score):05d}", True, fg_color)
            restart_surf = self.font.render("Press R or SPACE to Restart", True, accent_color)
            self.screen.blit(go_surf, (SCREEN_WIDTH // 2 - go_surf.get_width() // 2, 90))
            self.screen.blit(score_summary_surf, (SCREEN_WIDTH // 2 - score_summary_surf.get_width() // 2, 140))
            self.screen.blit(restart_surf, (SCREEN_WIDTH // 2 - restart_surf.get_width() // 2, 180))

        pygame.display.flip()

# -----------------------------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    game = GameEngine()
    game.run()