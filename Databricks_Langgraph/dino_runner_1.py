import pygame
import random
import sys

# Initialize Pygame
pygame.init()
pygame.font.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 400
FPS = 60
GROUND_Y = 320

# Colors
COLOR_BG = (247, 247, 247)
COLOR_PRIMARY = (83, 83, 83)
COLOR_LIGHT = (220, 220, 220)

# Setup Display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Dino Runner")
clock = pygame.time.Clock()

# --- Procedural Sprite Generation ---

def create_dino_sprite(state, frame, color=COLOR_PRIMARY):
    """Generates Dino sprites procedurally to avoid external asset dependencies."""
    if "duck" in state:
        surf = pygame.Surface((59, 30), pygame.SRCALPHA)
        # Body
        pygame.draw.rect(surf, color, (10, 10, 38, 14))
        # Head
        pygame.draw.rect(surf, color, (44, 6, 15, 10))
        # Beak/Snout
        pygame.draw.rect(surf, color, (48, 16, 11, 6))
        # Eye
        pygame.draw.rect(surf, COLOR_BG, (50, 8, 2, 2))
        # Tail
        pygame.draw.rect(surf, color, (2, 10, 8, 8))
        # Legs
        if frame == 0:
            pygame.draw.rect(surf, color, (18, 24, 4, 6))
            pygame.draw.rect(surf, color, (32, 24, 4, 3))
        else:
            pygame.draw.rect(surf, color, (18, 24, 4, 3))
            pygame.draw.rect(surf, color, (32, 24, 4, 6))
    else:
        surf = pygame.Surface((44, 47), pygame.SRCALPHA)
        # Body
        pygame.draw.rect(surf, color, (10, 12, 24, 20))
        # Head
        pygame.draw.rect(surf, color, (22, 2, 20, 12))
        # Snout
        pygame.draw.rect(surf, color, (30, 6, 12, 8))
        # Eye
        pygame.draw.rect(surf, COLOR_BG, (26, 4, 2, 2))
        # Tail
        pygame.draw.rect(surf, color, (2, 14, 8, 12))
        # Legs
        if state == "jump":
            pygame.draw.rect(surf, color, (14, 32, 4, 6))
            pygame.draw.rect(surf, color, (24, 32, 4, 6))
        elif frame == 0:
            pygame.draw.rect(surf, color, (14, 32, 4, 12))
            pygame.draw.rect(surf, color, (24, 32, 4, 6))
        else:
            pygame.draw.rect(surf, color, (14, 32, 4, 6))
            pygame.draw.rect(surf, color, (24, 32, 4, 12))
            
    # Draw a crashed eye if state is 'dead'
    if state == "dead":
        surf = pygame.Surface((44, 47), pygame.SRCALPHA)
        # Body
        pygame.draw.rect(surf, color, (10, 12, 24, 20))
        # Head
        pygame.draw.rect(surf, color, (22, 2, 20, 12))
        # Snout
        pygame.draw.rect(surf, color, (30, 6, 12, 8))
        # Tail
        pygame.draw.rect(surf, color, (2, 14, 8, 12))
        # Legs
        pygame.draw.rect(surf, color, (14, 32, 4, 12))
        pygame.draw.rect(surf, color, (24, 32, 4, 12))
        # Dead Eye (X)
        pygame.draw.line(surf, COLOR_BG, (25, 4), (29, 8), 2)
        pygame.draw.line(surf, COLOR_BG, (29, 4), (25, 8), 2)
        
    return surf

def create_cactus_sprite(size_type, count, color=COLOR_PRIMARY):
    """Generates Cactus sprites procedurally."""
    unit_w = 15 if size_type == "small" else 23
    unit_h = 35 if size_type == "small" else 50
    surf = pygame.Surface((unit_w * count, unit_h), pygame.SRCALPHA)
    
    for i in range(count):
        offset_x = i * unit_w
        if size_type == "small":
            # Main trunk
            pygame.draw.rect(surf, color, (offset_x + 6, 4, 3, 31))
            # Left branch
            pygame.draw.rect(surf, color, (offset_x + 2, 12, 4, 3))
            pygame.draw.rect(surf, color, (offset_x + 2, 8, 3, 6))
            # Right branch
            pygame.draw.rect(surf, color, (offset_x + 9, 16, 4, 3))
            pygame.draw.rect(surf, color, (offset_x + 10, 11, 3, 7))
        else:
            # Main trunk
            pygame.draw.rect(surf, color, (offset_x + 9, 6, 5, 44))
            # Left branch
            pygame.draw.rect(surf, color, (offset_x + 3, 18, 6, 4))
            pygame.draw.rect(surf, color, (offset_x + 3, 11, 4, 10))
            # Right branch
            pygame.draw.rect(surf, color, (offset_x + 14, 22, 6, 4))
            pygame.draw.rect(surf, color, (offset_x + 16, 15, 4, 10))
    return surf

def create_ptero_sprite(frame, color=COLOR_PRIMARY):
    """Generates Pterodactyl sprites procedurally."""
    surf = pygame.Surface((46, 40), pygame.SRCALPHA)
    # Body
    pygame.draw.rect(surf, color, (12, 16, 22, 8))
    # Head & Beak
    pygame.draw.rect(surf, color, (34, 14, 12, 6))
    # Eye
    pygame.draw.rect(surf, COLOR_BG, (36, 16, 2, 2))
    # Tail
    pygame.draw.rect(surf, color, (4, 18, 8, 4))
    
    if frame == 0:
        # Wings up
        pygame.draw.polygon(surf, color, [(20, 16), (28, 16), (24, 2)])
        pygame.draw.polygon(surf, color, [(20, 24), (26, 24), (23, 32)])
    else:
        # Wings down
        pygame.draw.polygon(surf, color, [(20, 16), (28, 16), (24, 30)])
        pygame.draw.polygon(surf, color, [(20, 24), (26, 24), (23, 10)])
    return surf


# --- Game Classes ---

class Dino:
    GRAVITY = 0.6
    JUMP_VELOCITY = -11.5

    def __init__(self, sprites):
        self.sprites = sprites
        self.x = 50
        self.y = GROUND_Y - 47
        self.vy = 0
        self.is_jumping = False
        self.is_ducking = False
        self.is_dead = False
        self.step_index = 0
        self.rect = pygame.Rect(self.x, self.y, 44, 47)

    def handle_input(self, keys):
        if self.is_dead:
            return

        # Jump
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP]) and not self.is_jumping and not self.is_ducking:
            self.vy = self.JUMP_VELOCITY
            self.is_jumping = True

        # Ducking State
        if keys[pygame.K_DOWN] and not self.is_jumping:
            self.is_ducking = True
        else:
            self.is_ducking = False

        # Fast Fall / Heavy Gravity when pressing down in mid-air
        if keys[pygame.K_DOWN] and self.is_jumping:
            self.vy += 1.2

    def update(self):
        if self.is_dead:
            return

        # Apply Gravity
        if self.is_jumping:
            self.vy += self.GRAVITY
            self.y += self.vy
            
            # Landing Check
            if self.y >= GROUND_Y - 47:
                self.y = GROUND_Y - 47
                self.vy = 0
                self.is_jumping = False

        # Update Hitbox and Position
        if self.is_ducking and not self.is_jumping:
            self.rect = pygame.Rect(self.x, GROUND_Y - 30, 59, 30)
        else:
            self.rect = pygame.Rect(self.x, self.y, 44, 47)

        # Cycle Animation Frames
        self.step_index = (self.step_index + 1) % 20

    def draw(self, screen):
        if self.is_dead:
            sprite = self.sprites['dead']
        elif self.is_jumping:
            sprite = self.sprites['jump']
        elif self.is_ducking:
            sprite = self.sprites['duck'][self.step_index // 10]
        else:
            sprite = self.sprites['run'][self.step_index // 10]
            
        screen.blit(sprite, (self.rect.x, self.rect.y))


class Obstacle:
    def __init__(self, x, y, sprite):
        self.x = x
        self.y = y
        self.sprite = sprite
        self.rect = self.sprite.get_rect()
        self.rect.x = x
        self.rect.y = y

    def update(self, speed):
        self.x -= speed
        self.rect.x = self.x

    def draw(self, screen):
        screen.blit(self.sprite, (self.rect.x, self.rect.y))


class Cactus(Obstacle):
    def __init__(self, x, size_type, count, sprites):
        sprite = sprites[(size_type, count)]
        h = 35 if size_type == "small" else 50
        y = GROUND_Y - h
        super().__init__(x, y, sprite)


class Pterodactyl(Obstacle):
    def __init__(self, x, height_type, sprites):
        # Variable Heights adjusted for proper clearance
        if height_type == "low":
            y = GROUND_Y - 50  # Must jump
        elif height_type == "mid":
            y = GROUND_Y - 75  # Can duck or jump
        else:
            y = GROUND_Y - 95  # Safe to stand still
            
        self.sprites = sprites
        self.step_index = 0
        super().__init__(x, y, self.sprites[0])

    def update(self, speed):
        super().update(speed)
        self.step_index = (self.step_index + 1) % 20
        self.sprite = self.sprites[self.step_index // 10]


class ObstacleManager:
    def __init__(self, cactus_sprites, ptero_sprites):
        self.cactus_sprites = cactus_sprites
        self.ptero_sprites = ptero_sprites
        self.obstacles = []
        self.spawn_distance = random.randint(300, 500)

    def update(self, speed, score):
        # Move obstacles
        for obs in self.obstacles:
            obs.update(speed)

        # Remove off-screen obstacles
        self.obstacles = [obs for obs in self.obstacles if obs.rect.right > 0]

        # Spawn logic
        if len(self.obstacles) == 0 or (SCREEN_WIDTH - self.obstacles[-1].rect.right) > self.spawn_distance:
            self.spawn_obstacle(score, speed)

    def spawn_obstacle(self, score, speed):
        # Pterodactyls start spawning after score 150
        if score > 150 and random.random() < 0.25:
            height = random.choice(["low", "mid", "high"])
            new_obs = Pterodactyl(SCREEN_WIDTH + 50, height, self.ptero_sprites)
        else:
            # Cacti spawning
            if score < 80:
                size = "small"
                count = random.choice([1, 2])
            else:
                size = random.choice(["small", "large"])
                count = random.choice([1, 2, 3])
            new_obs = Cactus(SCREEN_WIDTH + 50, size, count, self.cactus_sprites)

        self.obstacles.append(new_obs)
        # Scale spawn distance dynamically with speed to prevent impossible jumps
        self.spawn_distance = random.randint(int(speed * 35), int(speed * 65))

    def draw(self, screen):
        for obs in self.obstacles:
            obs.draw(screen)

    def reset(self):
        self.obstacles = []
        self.spawn_distance = random.randint(300, 500)


class ScoreManager:
    def __init__(self):
        self.current_score = 0.0
        self.high_score = 0
        self.font = pygame.font.SysFont("Courier New", 18, bold=True)

    def update(self):
        self.current_score += 0.15

    def reset(self):
        if int(self.current_score) > self.high_score:
            self.high_score = int(self.current_score)
        self.current_score = 0.0

    def draw(self, screen):
        score_str = f"{int(self.current_score):05d}"
        hi_score_str = f"HI {self.high_score:05d}"
        
        text_surface = self.font.render(f"{hi_score_str}  {score_str}", True, COLOR_PRIMARY)
        screen.blit(text_surface, (SCREEN_WIDTH - 180, 20))


# --- Main Game Controller ---

class Game:
    def __init__(self):
        self.state = "START_SCREEN"
        self.base_speed = 6.0
        self.game_speed = self.base_speed

        # Load/Generate Sprites
        self.dino_sprites = {
            'run': [create_dino_sprite("run", 0), create_dino_sprite("run", 1)],
            'jump': create_dino_sprite("jump", 0),
            'duck': [create_dino_sprite("duck", 0), create_dino_sprite("duck", 1)],
            'dead': create_dino_sprite("dead", 0)
        }
        
        self.cactus_sprites = {
            ("small", 1): create_cactus_sprite("small", 1),
            ("small", 2): create_cactus_sprite("small", 2),
            ("small", 3): create_cactus_sprite("small", 3),
            ("large", 1): create_cactus_sprite("large", 1),
            ("large", 2): create_cactus_sprite("large", 2),
            ("large", 3): create_cactus_sprite("large", 3),
        }
        
        self.ptero_sprites = [create_ptero_sprite(0), create_ptero_sprite(1)]

        # Instantiate Systems
        self.dino = Dino(self.dino_sprites)
        self.obstacle_manager = ObstacleManager(self.cactus_sprites, self.ptero_sprites)
        self.score_manager = ScoreManager()

        # Environment Elements
        self.clouds = []
        for _ in range(3):
            self.clouds.append({
                'x': random.randint(0, SCREEN_WIDTH),
                'y': random.randint(40, 120),
                'speed': random.uniform(0.2, 0.8)
            })

        self.ground_lines = []
        for _ in range(5):
            self.ground_lines.append({
                'x': random.randint(0, SCREEN_WIDTH),
                'y': random.randint(GROUND_Y + 5, GROUND_Y + 30),
                'len': random.randint(5, 15)
            })

    def reset_game(self):
        self.dino = Dino(self.dino_sprites)
        self.obstacle_manager.reset()
        self.score_manager.reset()
        self.game_speed = self.base_speed

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            if event.type == pygame.KEYDOWN:
                if self.state == "START_SCREEN":
                    if event.key in [pygame.K_SPACE, pygame.K_UP]:
                        self.state = "PLAYING"
                elif self.state == "GAME_OVER":
                    if event.key in [pygame.K_SPACE, pygame.K_UP]:
                        self.reset_game()
                        self.state = "PLAYING"

    def update(self):
        if self.state == "PLAYING":
            keys = pygame.key.get_pressed()
            self.dino.handle_input(keys)
            self.dino.update()
            
            self.score_manager.update()
            
            # Gradually increase speed based on score
            self.game_speed = self.base_speed + (self.score_manager.current_score / 150.0)
            self.game_speed = min(self.game_speed, 15.0)  # Cap maximum speed
            
            self.obstacle_manager.update(self.game_speed, self.score_manager.current_score)

            # Update Environment
            for cloud in self.clouds:
                cloud['x'] -= cloud['speed']
                if cloud['x'] < -60:
                    cloud['x'] = SCREEN_WIDTH + random.randint(10, 100)
                    cloud['y'] = random.randint(40, 120)

            for line in self.ground_lines:
                line['x'] -= self.game_speed
                if line['x'] < -line['len']:
                    line['x'] = SCREEN_WIDTH + random.randint(0, 50)
                    line['y'] = random.randint(GROUND_Y + 5, GROUND_Y + 30)

            # Collision Detection (AABB with slightly shrunk hitboxes for fairness)
            dino_rect = self.dino.rect
            if self.dino.is_ducking and not self.dino.is_jumping:
                dino_hitbox = dino_rect.inflate(-6, -4)
            else:
                dino_hitbox = dino_rect.inflate(-10, -8)

            for obs in self.obstacle_manager.obstacles:
                obs_hitbox = obs.rect.inflate(-6, -6)
                if dino_hitbox.colliderect(obs_hitbox):
                    self.state = "GAME_OVER"
                    self.dino.is_dead = True

    def draw(self):
        screen.fill(COLOR_BG)

        # Draw Ground Line
        pygame.draw.line(screen, COLOR_PRIMARY, (0, GROUND_Y), (SCREEN_WIDTH, GROUND_Y), 2)

        # Draw Environment
        for cloud in self.clouds:
            cx, cy = cloud['x'], cloud['y']
            pygame.draw.ellipse(screen, COLOR_LIGHT, (cx, cy, 50, 18))
            pygame.draw.ellipse(screen, COLOR_LIGHT, (cx + 15, cy - 8, 25, 18))

        for line in self.ground_lines:
            pygame.draw.line(screen, COLOR_PRIMARY, (line['x'], line['y']), (line['x'] + line['len'], line['y']), 1)

        # Draw Entities
        self.dino.draw(screen)
        self.obstacle_manager.draw(screen)
        self.score_manager.draw(screen)

        # State Overlays
        if self.state == "START_SCREEN":
            font_large = pygame.font.SysFont("Courier New", 24, bold=True)
            text_start = font_large.render("P R E S S   S P A C E   T O   P L A Y", True, COLOR_PRIMARY)
            rect_start = text_start.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            screen.blit(text_start, rect_start)

        elif self.state == "GAME_OVER":
            font_large = pygame.font.SysFont("Courier New", 24, bold=True)
            font_small = pygame.font.SysFont("Courier New", 14, bold=True)
            
            text_go = font_large.render("G A M E   O V E R", True, COLOR_PRIMARY)
            text_restart = font_small.render("PRESS SPACE TO RESTART", True, COLOR_PRIMARY)
            
            rect_go = text_go.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20))
            rect_restart = text_restart.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
            
            screen.blit(text_go, rect_go)
            screen.blit(text_restart, rect_restart)

        pygame.display.flip()

    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            clock.tick(FPS)


if __name__ == "__main__":
    game = Game()
    game.run()