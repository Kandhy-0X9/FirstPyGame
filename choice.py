# game.py
# Pygame adaptation of the full terminal story from main.py
# - Clean Scene system
# - 1:1 story conversion (all branches)
# - VN-style UI with keyboard and clickable choices
#
# Sources: main.py and readme.MD provided by the user.
# main.py story content was converted into scenes. :contentReference[oaicite:2]{index=2} :contentReference[oaicite:3]{index=3}

import pygame
import textwrap
import sys

pygame.init()
WIDTH, HEIGHT = 800, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Psycho Horror — Bastion One")
clock = pygame.time.Clock()

# Fonts & colors
FONT = pygame.font.SysFont("consolas", 20)
TITLE_FONT = pygame.font.SysFont("consolas", 26, bold=True)
WHITE = (245, 245, 245)
BLACK = (10, 10, 10)
GRAY = (40, 40, 40)
BUTTON_BG = (70, 70, 90)
BUTTON_HOVER = (100, 100, 130)
RED = (180, 50, 50)

# Layout
TEXT_BOX_RECT = pygame.Rect(40, 60, WIDTH - 80, HEIGHT - 180)
CHOICE_AREA_RECT = pygame.Rect(40, HEIGHT - 110, WIDTH - 80, 80)

# Utility: wrap & draw text inside TEXT_BOX_RECT
def draw_wrapped_text(surface, text, rect, font, color=WHITE, line_spacing=4):
    # Break text into paragraphs
    x, y = rect.topleft
    max_width = rect.width
    space = font.size(' ')[0]
    lines_drawn = 0
    for paragraph in text.splitlines():
        if paragraph.strip() == "":
            y += font.get_height() + line_spacing
            continue
        words = paragraph.split(' ')
        line = ""
        for w in words:
            test_line = (line + " " + w).strip()
            if font.size(test_line)[0] <= max_width:
                line = test_line
            else:
                img = font.render(line, True, color)
                surface.blit(img, (x, y))
                y += font.get_height() + line_spacing
                lines_drawn += 1
                line = w
        if line:
            img = font.render(line, True, color)
            surface.blit(img, (x, y))
            y += font.get_height() + line_spacing
            lines_drawn += 1
    return lines_drawn

# Button helper
class Button:
    def __init__(self, rect, text, key):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.key = key  # string '1','2','3', or 'yes' etc.

    def draw(self, surf, mouse_pos):
        hover = self.rect.collidepoint(mouse_pos)
        color = BUTTON_HOVER if hover else BUTTON_BG
        pygame.draw.rect(surf, color, self.rect, border_radius=6)
        txt = FONT.render(self.text, True, WHITE)
        tx = self.rect.x + 12
        ty = self.rect.y + (self.rect.height - txt.get_height()) // 2
        surf.blit(txt, (tx, ty))

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

# Scene system
class Scene:
    def __init__(self, id, text, choices=None):
        self.id = id
        self.text = text
        # choices: list of tuples (label_text, choice_key, next_scene_id)
        # choice_key is '1','2','3' or other labels; keyboard presses map by '1','2','3'
        self.choices = choices or []

# Build scenes by converting main.py content
# The text is preserved, but adjusted for VN format (line breaks).
SCENES = {}

def s(id, text, choices=None):
    SCENES[id] = Scene(id, text, choices)
    return SCENES[id]

# Helper to reuse end-of-game
END_TRAGIC = "You have met a tragic end."
END_RESTART_PROMPT = "\nPress '1' to restart or click the Restart button."

# --- Scenes (full conversion) ---
s("INTRO",
"""Anna: Captain, I detected an anomaly in the engine room.
You: I'm busy right now Anna, can it wait?
Anna: Captain, this is serious. Please check it out.

Choices:
1. Investigate the anomaly yourself.
2. Tell Anna to investigate.
3. Ignore the anomaly for now.
""", [
    ("1. Investigate the anomaly yourself.", '1', "INVESTIGATE"),
    ("2. Tell Anna to investigate.", '2', "TELL_ANNA"),
    ("3. Ignore the anomaly for now.", '3', "IGNORE")
])

# Choice 1 path
s("INVESTIGATE",
"""You decide to investigate the anomaly yourself. As you enter the engine room, you notice a strange humming sound coming from one of the reactors.

A black liquid drips on your forehead from a leaking pipe above.
You: What the...?

Choices:
1. Examine the leaking pipe.
2. Call Anna for assistance.
3. Leave the engine room immediately.
""", [
    ("1. Examine the leaking pipe.", '1', "INV_PIPE"),
    ("2. Call Anna for assistance.", '2', "INV_CALL_ANNA"),
    ("3. Leave the engine room immediately.", '3', "INV_LEAVE")
])

s("INV_PIPE", END_TRAGIC + "\n\nSuddenly you are sprayed with the black liquid, and everything goes dark." + END_RESTART_PROMPT, [
    ("1. Restart", '1', "INTRO")
])

s("INV_CALL_ANNA",
"""Calvin: Anna is busy right now, what do you need Cap?
You: Can you check the pipes? Something seems off.
Calvin: On it, Cap.

Before you can blink, Calvin's top half is gone as blood sprays everywhere.

Choices:
1. Run away screaming.
2. Reach out for your Taser.
3. Faint from the horror.
""", [
    ("1. Run away screaming.", '1', "INV_CALL_ANNA_RUN"),
    ("2. Reach out for your Taser.", '2', "INV_CALL_ANNA_TASER"),
    ("3. Faint from the horror.", '3', "INV_CALL_ANNA_FAINT")
])

s("INV_CALL_ANNA_RUN", END_TRAGIC + "\n\nYou run away screaming, but the creature chases you down and you meet a tragic end." + END_RESTART_PROMPT, [
    ("1. Restart", '1', "INTRO")
])

s("INV_CALL_ANNA_TASER", END_TRAGIC + "\n\nYou reach for your Taser and manage to stun the creature long enough, but the reactor overloads and you meet a tragic end." + END_RESTART_PROMPT, [
    ("1. Restart", '1', "INTRO")
])

s("INV_CALL_ANNA_FAINT",
"""You faint from the horror, and the creature leaves you alone thinking you're dead. However, you later wake up in the medbay.
Anna: Captain, what happened to you?
You: Calvin... where is he?
Anna: He's okay, he managed to fix the pipes.
You: He died... The thing in the engine room... it got him.
Calvin: Cap, you good?
You: Yeah... just a nightmare, I guess.
Anna: Stop being paranoid, Captain. Everything is fine.

MAKE SURE YOU TAKE YOUR MEDS NEXT TIME!

TY 4 Playing!
""", [
    ("1. Restart", '1', "INTRO")
])

s("INV_LEAVE", END_TRAGIC + "\n\nYou leave the engine room immediately, but as you exit, you hear a loud explosion behind you. Half the ship is torn apart and you're dragged into space." + END_RESTART_PROMPT, [
    ("1. Restart", '1', "INTRO")
])

# Choice 2 path
s("TELL_ANNA",
"""You tell Anna to investigate the anomaly.
Anna's Radio: Captain, you should come check this out... *static* ...Captain!!
You: Anna? Are you okay?

Choices:
1. Rush to the engine room to help Anna.
2. Try to contact Anna again.
3. Wait for Anna to respond.
""", [
    ("1. Rush to the engine room to help Anna.", '1', "TELL_RUSH"),
    ("2. Try to contact Anna again.", '2', "TELL_CONTACT"),
    ("3. Wait for Anna to respond.", '3', "TELL_WAIT")
])

s("TELL_RUSH",
"""You rush to the engine room and find trails of blood.
You: Anna? Anna!!

Choices:
1. Follow the blood trail.
2. Call for backup.
3. Initiate an emergency lockdown.
""", [
    ("1. Follow the blood trail.", '1', "TELL_RUSH_FOLLOW"),
    ("2. Call for backup.", '2', "TELL_RUSH_BACKUP"),
    ("3. Initiate an emergency lockdown.", '3', "TELL_RUSH_LOCK")
])

s("TELL_RUSH_FOLLOW", END_TRAGIC + "\n\nYou follow the blood trail deeper into the engine room and suddenly a creature leaps out and attacks you." + END_RESTART_PROMPT, [
    ("1. Restart", '1', "INTRO")
])

s("TELL_RUSH_BACKUP",
"""Rasta: Capitan man, what de problem man?
You: There's been an attack in the engine room, I need help!
Rasta: Count on me man, I gat you. What we doin'?
You: Go in there and secure the area.
Rasta: On it, Capitan.
You: I will get the others ready.

Choices:
1. Close the engine room while Rasta is in there.
2. Go to the Weaponry to arm yourself.
3. Call for help from HQ.
""", [
    ("1. Close the engine room while Rasta is in there.", '1', "TELL_RUSH_BACKUP_CLOSE"),
    ("2. Go to the Weaponry to arm yourself.", '2', "TELL_RUSH_BACKUP_ARM"),
    ("3. Call for help from HQ.", '3', "TELL_RUSH_BACKUP_HQ")
])

s("TELL_RUSH_BACKUP_CLOSE",
"""You close the engine room door while Rasta is inside.
After a few moments, you hear a loud thud and silence.

Congrats! You have eliminated the anomaly but at the cost of Rasta's life.
""", [
    ("1. Restart", '1', "INTRO")
])

s("TELL_RUSH_BACKUP_ARM", END_TRAGIC + "\n\nYou head to the Weaponry and arm yourself with a laser rifle. You return to the engine room to find Rasta fighting the creature. With your help, you manage to subdue the creature and secure the area. You and Rasta look down at the creature—suddenly it sprays black liquid everywhere." + END_RESTART_PROMPT, [
    ("1. Restart", '1', "INTRO")
])

s("TELL_RUSH_BACKUP_HQ", END_TRAGIC + "\n\nYou call for help from HQ... You have met a tragic end." + END_RESTART_PROMPT, [
    ("1. Restart", '1', "INTRO")
])

s("TELL_RUSH_LOCK", END_TRAGIC + "\n\nYou initiate an emergency lockdown, sealing the engine room. You lock yourself with your crew in the ship and all die of suffocation." + END_RESTART_PROMPT, [
    ("1. Restart", '1', "INTRO")
])

s("TELL_CONTACT",
"""You try to contact Anna again but there is no response.
You: Anna, please respond.

Suddenly, you hear a loud crash from the engine room.

Choices:
1. Rush to the engine room.
2. Call for backup.
3. Check the ship's security cameras.
""", [
    ("1. Rush to the engine room.", '1', "TELL_CONTACT_RUSH"),
    ("2. Call for backup.", '2', "TELL_CONTACT_BACKUP"),
    ("3. Check the ship's security cameras.", '3', "TELL_CONTACT_CAM")
])

s("TELL_CONTACT_RUSH", END_TRAGIC + "\n\nMegan: This is Megan from security. We have a situation in the engine room. Everyone stay calm.\nYou rush to the engine room and find Anna injured but alive. Anna: Captain... thank god you came. Anna: Captain, watch out! You have met a tragic end." + END_RESTART_PROMPT, [
    ("1. Restart", '1', "INTRO")
])

s("TELL_CONTACT_BACKUP", END_TRAGIC + "\n\nYou call for backup...\nYou: Why is an orbital strike heading towards us? You have met a tragic end." + END_RESTART_PROMPT, [
    ("1. Restart", '1', "INTRO")
])

s("TELL_CONTACT_CAM",
"""You access the ship's security cameras and see a creature moving through the engine room.
You: What is that thing?
You suddenly wake up in the medbay.
Anna: Captain, you forgot to take your meds again.
You: Oh... right.

MAKE SURE YOU TAKE YOUR MEDS NEXT TIME!

TY 4 Playing!
""", [
    ("1. Restart", '1', "INTRO")
])

s("TELL_WAIT", END_TRAGIC + "\n\nYou wait for Anna to respond... No answer ever comes. Silence fills the ship." + END_RESTART_PROMPT, [
    ("1. Restart", '1', "INTRO")
])

# Choice 3 path
s("IGNORE",
"""You decide to ignore the anomaly for now.
The engines suddenly stop functioning and the ship drifts into an asteroid field.
You call on the crew to fix the engines but there is no power.
Anna: Captain... anomaly spreading... systems compromised...
You: Anna? Stay with me!

Choices:
1. Attempt to manually restart the engines.
2. Order the crew to abandon ship.
3. Search for the source of the anomaly despite ignoring it earlier.
""", [
    ("1. Attempt to manually restart the engines.", '1', "IGNORE_RESTART"),
    ("2. Order the crew to abandon ship.", '2', "IGNORE_ABANDON"),
    ("3. Search for the source of the anomaly.", '3', "IGNORE_SEARCH")
])

s("IGNORE_RESTART", END_TRAGIC + "\n\nYou rush to the control panel and attempt a manual restart. The engines roar back to life for a moment, but then overload. You have met a tragic end." + END_RESTART_PROMPT, [
    ("1. Restart", '1', "INTRO")
])

s("IGNORE_ABANDON",
"""You order the crew to abandon ship.
Escape pods launch into the void, scattering across the asteroid field.
You remain behind, watching as the ship collides with an asteroid.
Your sacrifice ensures some of your crew survives.

Congrats, you eliminated the anomaly at the expense of your own life.
""", [
    ("1. Restart", '1', "INTRO")
])

s("IGNORE_SEARCH", END_TRAGIC + "\n\nAs you enter the engine room, the black liquid has spread across the walls. Suddenly, a creature emerges from the liquid and attacks you in a swift motion. You have met a tragic end." + END_RESTART_PROMPT, [
    ("1. Restart", '1', "INTRO")
])

# Fallback scene for safety
s("NOT_FOUND", "An error occurred: scene not found. Press 1 to go back to the start.", [
    ("1. Restart", '1', "INTRO")
])

# --- End scene construction ---

# Global state
current_scene = SCENES.get("INTRO")
buttons = []  # Buttons for current scene
mouse_pos = (0, 0)

def build_buttons_for_scene(scene):
    btns = []
    # Layout up to 3 choices horizontally
    margin = 12
    btn_w = (CHOICE_AREA_RECT.width - margin * 4) // 3
    btn_h = 48
    x0 = CHOICE_AREA_RECT.x + margin
    y0 = CHOICE_AREA_RECT.y + 16
    for idx, (label, key, next_id) in enumerate(scene.choices):
        x = x0 + idx * (btn_w + margin)
        r = (x, y0, btn_w, btn_h)
        btns.append(Button(r, label, key))
    # If no choices, provide a Restart button
    if not btns:
        r = (CHOICE_AREA_RECT.centerx - 80, CHOICE_AREA_RECT.y + 16, 160, 48)
        btns.append(Button(r, "Restart", '1'))
    return btns

def go_to_scene(scene_id):
    global current_scene, buttons
    current_scene = SCENES.get(scene_id, SCENES.get("NOT_FOUND"))
    buttons = build_buttons_for_scene(current_scene)

# Initialize buttons
buttons = build_buttons_for_scene(current_scene)

# Draw UI frame
def draw_ui():
    screen.fill(BLACK)
    # Title
    title = TITLE_FONT.render("Bastion One — Psychological Horror", True, WHITE)
    screen.blit(title, (40, 18))

    # Text box
    pygame.draw.rect(screen, GRAY, TEXT_BOX_RECT, border_radius=8)
    pygame.draw.rect(screen, BLACK, TEXT_BOX_RECT.inflate(-6, -6), border_radius=6)
    # Draw wrapped text
    draw_wrapped_text(screen, current_scene.text, TEXT_BOX_RECT.inflate(-12, -12), FONT, WHITE)

    # Choices area
    pygame.draw.rect(screen, GRAY, CHOICE_AREA_RECT, border_radius=8)
    pygame.draw.rect(screen, BLACK, CHOICE_AREA_RECT.inflate(-6, -6), border_radius=6)

    # Buttons
    for btn in buttons:
        btn.draw(screen, mouse_pos)

# Main loop
running = True
while running:
    clock.tick(30)
    mouse_pos = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            break

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in buttons:
                if btn.is_clicked(event.pos):
                    # Find the corresponding next scene for that button's key
                    # Match by key in current_scene.choices
                    chosen = None
                    for label, key, next_id in current_scene.choices:
                        if key == btn.key:
                            chosen = next_id
                            break
                    # If button is Restart or no choices, default to INTRO
                    if chosen is None:
                        chosen = "INTRO"
                    go_to_scene(chosen)
                    break

        if event.type == pygame.KEYDOWN:
            keyname = pygame.key.name(event.key)
            # Map numeric keys '1','2','3' to choices
            # Also accept keypad numbers by checking event.key for K_KP1 etc.
            # If current scene has matching choice key, go to its scene
            matched = False
            for label, key, next_id in current_scene.choices:
                # keyboard returns e.g. '1'
                if keyname == key:
                    go_to_scene(next_id)
                    matched = True
                    break
            # If no choices (end scenes), pressing '1' restarts
            if not matched and keyname == '1' and not current_scene.choices:
                go_to_scene("INTRO")

    draw_ui()
    pygame.display.flip()

pygame.quit()
sys.exit()
