"""
Psychological Horror Text Game
A pygame-based interactive fiction game with multiple story paths.
"""

import pygame
import textwrap

# ----- INITIALIZATION -----
pygame.init()
SCREEN = pygame.display.set_mode((1280, 640))
pygame.display.set_caption("Psychological Horror Text Game")

# ----- CONSTANTS -----
FONT = pygame.font.SysFont("consolas", 20)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


# ----- UTILITIES -----
def draw_text(surface, text, x, y, color=WHITE, width=600):
    """Render wrapped text on a pygame surface."""
    lines = textwrap.wrap(text, 75)
    for line in lines:
        img = FONT.render(line, True, color)
        surface.blit(img, (x, y))
        y += 24
    return y


# ----- CLASSES -----
class Scene:
    """Represents a scene in the story with text and choices."""
    
    def __init__(self, text, choices=None):
        self.text = text
        self.choices = choices or {}  # {'1': next_scene, ...}

# ----- STORY NODES -----
intro = Scene(
    "Anna: Captain, I detected an anomaly in the engine room.\n"
    "You: I'm busy right now Anna, can it wait?\n"
    "Anna: Captain, this is serious. Please check it out.\n\n"
    "Choices:\n"
    "1. Investigate the anomaly yourself.\n"
    "2. Tell Anna to investigate.\n"
    "3. Ignore the anomaly for now.\n"
)

death_generic = Scene(
    "You have met a tragic end.\n\nPress 1 to restart.",
    {"1": "INTRO"}
)

scene1 = Scene(
    "You decide to investigate the anomaly yourself.\n"
    "As you enter the engine room, a strange humming fills the air.\n\n"
    "Choices:\n"
    "1. Examine the leaking pipe.\n"
    "2. Call Anna for assistance.\n"
    "3. Leave the engine room immediately.\n",
    {"1": "DEAD", "2": "DEAD", "3": "DEAD"}
)

scene2 = Scene(
    "You tell Anna to investigate.\n"
    "Moments later you hear static… then a scream.\n\n"
    "Choices:\n"
    "1. Rush to help Anna.\n"
    "2. Try to contact her again.\n"
    "3. Wait for her to respond.\n",
    {"1": "DEAD", "2": "DEAD", "3": "DEAD"}
)

scene3 = Scene(
    "You ignore the anomaly.\n"
    "Moments later, the engines fail and alarms blare…\n\n"
    "Choices:\n"
    "1. Attempt manual restart.\n"
    "2. Order crew to abandon ship.\n"
    "3. Search for the source of the anomaly.\n",
    {"1": "DEAD", "2": "DEAD", "3": "DEAD"}
)

# ----- STORY MAP -----
STORY = {
    "INTRO": intro,
    "1": scene1,
    "2": scene2,
    "3": scene3,
    "DEAD": death_generic
}

current_scene_key = "INTRO"


# ----- GAME LOOP -----
running = True
while running:
    SCREEN.fill(BLACK)

    scene = STORY[current_scene_key]
    y = draw_text(SCREEN, scene.text, 20, 20)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            key = pygame.key.name(event.key)

            if key in scene.choices:
                next_key = scene.choices[key]
                current_scene_key = next_key

    pygame.display.flip()

pygame.quit()
