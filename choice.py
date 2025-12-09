# game.py
# Fully upgraded Pygame VN engine with:
# - typewriter per-letter sound
# - background images & portraits (assets/ folder)
# - looping music
# - auto / skip / fast-forward
# - message log
# - adjustable text speed (+/-)
#
# Story content sourced and converted from the user's main.py. :contentReference[oaicite:2]{index=2}
# README referenced for project description. :contentReference[oaicite:3]{index=3}

import pygame
import textwrap
import os
import sys
from pathlib import Path
from collections import deque
from pygame import mixer
from time import perf_counter

pygame.init()
mixer.init()

# ---------- CONFIG ----------
WIDTH, HEIGHT = 1000, 700
FPS = 60
ASSETS_DIR = Path("assets")
BG_DIR = ASSETS_DIR / "bg"
PORTRAITS_DIR = ASSETS_DIR / "portraits"
MUSIC_FILE = ASSETS_DIR / "music" / "ambient_loop.ogg"
TYPE_SFX = ASSETS_DIR / "sfx" / "type.wav"

# Fonts & Colors
FONT = pygame.font.SysFont("consolas", 20)
NAME_FONT = pygame.font.SysFont("consolas", 22, bold=True)
TITLE_FONT = pygame.font.SysFont("consolas", 26, bold=True)
WHITE = (245, 245, 245)
BLACK = (10, 10, 10)
GRAY = (40, 40, 40)
DARK = (18, 18, 28)
BUTTON_BG = (65, 72, 90)
BUTTON_HOVER = (95, 102, 130)
ACCENT = (170, 120, 120)
LOG_BG = (20, 20, 30)

# Layout
TEXT_BOX_RECT = pygame.Rect(40, HEIGHT - 210, WIDTH - 320, 160)
NAME_BOX_RECT = pygame.Rect(TEXT_BOX_RECT.x, TEXT_BOX_RECT.y - 36, 220, 34)
CHOICE_AREA_RECT = pygame.Rect(TEXT_BOX_RECT.right + 10, TEXT_BOX_RECT.y, 230, TEXT_BOX_RECT.height)
PORTRAIT_RECT = pygame.Rect(TEXT_BOX_RECT.right + 10, 40, 230, 300)
TITLE_POS = (40, 12)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Bastion One — Psychological Horror (VN Engine)")

clock = pygame.time.Clock()

# ---------- Utility helpers ----------
def load_image_safe(path, size=None):
    try:
        img = pygame.image.load(path).convert_alpha()
        if size:
            img = pygame.transform.smoothscale(img, size)
        return img
    except Exception:
        return None

def draw_wrapped_text(surface, text, rect, font, color=WHITE, line_spacing=4, max_lines=None):
    """Draw wrapped text inside rect. Returns number of lines drawn."""
    x, y = rect.topleft
    max_width = rect.width
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
                if max_lines and lines_drawn >= max_lines:
                    return lines_drawn
        if line:
            img = font.render(line, True, color)
            surface.blit(img, (x, y))
            y += font.get_height() + line_spacing
            lines_drawn += 1
            if max_lines and lines_drawn >= max_lines:
                return lines_drawn
    return lines_drawn

# ---------- Button with wrapping ----------
class Button:
    def __init__(self, rect, text, key):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.key = key  # e.g., '1', '2', '3', or 'restart'
    def draw(self, surf, mouse_pos):
        hover = self.rect.collidepoint(mouse_pos)
        color = BUTTON_HOVER if hover else BUTTON_BG
        pygame.draw.rect(surf, color, self.rect, border_radius=8)
        # Draw wrapped lines inside
        inner = self.rect.inflate(-10, -10)
        draw_wrapped_text(surf, self.text, inner, FONT)
    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

# ---------- Scene system ----------
class Scene:
    def __init__(self, id, text, choices=None, bg=None, portrait=None, name=None):
        self.id = id
        self.text = text
        # choices: list of tuples (label_text, key, next_scene_id)
        self.choices = choices or []
        self.bg = bg  # background key (filename without ext)
        self.portrait = portrait  # portrait filename (no ext)
        self.name = name  # speaking character name

SCENES = {}
def s(id, text, choices=None, bg=None, portrait=None, name=None):
    SCENES[id] = Scene(id, text, choices, bg, portrait, name)
    return SCENES[id]

# ---------- Convert your full story into scenes ----------
# (All text is taken from main.py; full conversion done)
# For brevity, only story scenes from main.py have been ported. They are identical in content.
INTRO_TEXT = """Anna: Captain, I detected an anomaly in the engine room.
You: I'm busy right now Anna, can it wait?
Anna: Captain, this is serious. Please check it out.

Choices:
1. Investigate the anomaly yourself.
2. Tell Anna to investigate.
3. Ignore the anomaly for now.
"""
s("INTRO", INTRO_TEXT, [
    ("1. Investigate the anomaly yourself.", '1', "INVESTIGATE"),
    ("2. Tell Anna to investigate.", '2', "TELL_ANNA"),
    ("3. Ignore the anomaly for now.", '3', "IGNORE")
], bg="bridge", portrait="anna", name="Anna")

# Investigate branch
s("INVESTIGATE",
"""You decide to investigate the anomaly yourself. As you enter the engine room, you notice a strange humming sound coming from one of the reactors.
A black liquid drips on your forehead from a leaking pipe above.
You: What the...?""",
[("1. Examine the leaking pipe.", '1', "INV_PIPE"),
 ("2. Call Anna for assistance.", '2', "INV_CALL_ANNA"),
 ("3. Leave the engine room immediately.", '3', "INV_LEAVE")],
bg="engine_room", portrait="captain", name="You")

s("INV_PIPE", "Suddenly you are sprayed with the black liquid, and everything goes dark.\n\nYou have met a tragic end.", [], bg="death", portrait="creature", name=None)
s("INV_CALL_ANNA",
"""Calvin: Anna is busy right now, what do you need Cap?
You: Can you check the pipes? Something seems off.
Calvin: On it, Cap.

Before you can blink, Calvin's top half is gone as blood sprays everywhere.""",
[("1. Run away screaming.", '1', "INV_CALL_ANNA_RUN"),
 ("2. Reach out for your Taser.", '2', "INV_CALL_ANNA_TASER"),
 ("3. Faint from the horror.", '3', "INV_CALL_ANNA_FAINT")],
bg="engine_room", portrait="calvin", name="Calvin")

s("INV_CALL_ANNA_RUN", "You run away screaming, but the creature chases you down and you meet a tragic end.", [], bg="death", portrait="creature")
s("INV_CALL_ANNA_TASER", "You reach for your Taser and manage to stun the creature long enough, but the reactor overloads and you meet a tragic end.", [], bg="death", portrait="creature")
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

TY 4 Playing!""", [], bg="medbay", portrait="anna", name="Narration")

s("INV_LEAVE", "You leave the engine room immediately, but as you exit, you hear a loud explosion behind you. Half the ship is torn apart and you're dragged into space.\n\nYou have met a tragic end.", [], bg="space", portrait="death")

# Tell Anna branch
s("TELL_ANNA",
"""You tell Anna to investigate the anomaly.
Anna's Radio: Captain, you should come check this out... *static* ...Captain!!
You: Anna? Are you okay?""",
[("1. Rush to the engine room to help Anna.", '1', "TELL_RUSH"),
 ("2. Try to contact Anna again.", '2', "TELL_CONTACT"),
 ("3. Wait for Anna to respond.", '3', "TELL_WAIT")],
bg="bridge", portrait="anna", name="Anna")

s("TELL_RUSH",
"""You rush to the engine room and find trails of blood.
You: Anna? Anna!!""",
[("1. Follow the blood trail.", '1', "TELL_RUSH_FOLLOW"),
 ("2. Call for backup.", '2', "TELL_RUSH_BACKUP"),
 ("3. Initiate an emergency lockdown.", '3', "TELL_RUSH_LOCK")],
bg="engine_room")

s("TELL_RUSH_FOLLOW", "You follow the blood trail deeper into the engine room and suddenly a creature leaps out and attacks you. You have met a tragic end.", [], bg="death")
s("TELL_RUSH_BACKUP",
"""Rasta: Capitan man, what de problem man?
You: There's been an attack in the engine room, I need help!
Rasta: Count on me man, I gat you. What we doin'?
You: Go in there and secure the area.
Rasta: On it, Capitan.
You: I will get the others ready.""",
[("1. Close the engine room while Rasta is in there.", '1', "TELL_RUSH_BACKUP_CLOSE"),
 ("2. Go to the Weaponry to arm yourself.", '2', "TELL_RUSH_BACKUP_ARM"),
 ("3. Call for help from HQ.", '3', "TELL_RUSH_BACKUP_HQ")], bg="bridge", portrait="rasta")

s("TELL_RUSH_BACKUP_CLOSE", "You close the engine room door while Rasta is inside. After a few moments, you hear a loud thud and silence.\n\nCongrats! You have eliminated the anomaly but at the cost of Rasta's life.", [], bg="engine_room")
s("TELL_RUSH_BACKUP_ARM", "You head to the Weaponry and arm yourself with a laser rifle. You return to the engine room to find Rasta fighting the creature. With your help, you manage to subdue the creature and secure the area. You and Rasta look down at the creature—suddenly it sprays black liquid everywhere. You have met a tragic end.", [], bg="death")
s("TELL_RUSH_BACKUP_HQ", "You call for help from HQ.\n\nYou have met a tragic end.", [], bg="death")
s("TELL_RUSH_LOCK", "You initiate an emergency lockdown, sealing the engine room. You lock yourself with your crew in the ship and all die of suffocation.\n\nYou have met a tragic end.", [], bg="death")

s("TELL_CONTACT",
"""You try to contact Anna again but there is no response.
You: Anna, please respond.

Suddenly, you hear a loud crash from the engine room.""",
[("1. Rush to the engine room.", '1', "TELL_CONTACT_RUSH"),
 ("2. Call for backup.", '2', "TELL_CONTACT_BACKUP"),
 ("3. Check the ship's security cameras.", '3', "TELL_CONTACT_CAM")], bg="bridge")

s("TELL_CONTACT_RUSH", "Megan: This is Megan from security. We have a situation in the engine room. Everyone stay calm.\nYou rush to the engine room and find Anna injured but alive.\nAnna: Captain... thank god you came.\nAnna: Captain, watch out!\n\nYou have met a tragic end.", [], bg="death")
s("TELL_CONTACT_BACKUP", "You call for backup.\nYou: Why is an orbital strike heading towards us?\n\nYou have met a tragic end.", [], bg="death")
s("TELL_CONTACT_CAM",
"""You access the ship's security cameras and see a creature moving through the engine room.
You: What is that thing?
You suddenly wake up in the medbay.
Anna: Captain, you forgot to take your meds again.
You: Oh... right.

MAKE SURE YOU TAKE YOUR MEDS NEXT TIME!

TY 4 Playing!""", [], bg="medbay")

s("TELL_WAIT", "You wait for Anna to respond... No answer ever comes. Silence fills the ship.\n\nYou have met a tragic end.", [], bg="death")

# Ignore branch
s("IGNORE",
"""You decide to ignore the anomaly for now.
The engines suddenly stop functioning and the ship drifts into an asteroid field.
You call on the crew to fix the engines but there is no power.
Anna: Captain... anomaly spreading... systems compromised...
You: Anna? Stay with me!""",
[("1. Attempt to manually restart the engines.", '1', "IGNORE_RESTART"),
 ("2. Order the crew to abandon ship.", '2', "IGNORE_ABANDON"),
 ("3. Search for the source of the anomaly despite ignoring it earlier.", '3', "IGNORE_SEARCH")], bg="bridge")

s("IGNORE_RESTART", "You rush to the control panel and attempt a manual restart. The engines roar back to life for a moment, but then overload.\n\nYou have met a tragic end.", [], bg="death")
s("IGNORE_ABANDON", "You order the crew to abandon ship. Escape pods launch into the void, scattering across the asteroid field. You remain behind, watching as the ship collides with an asteroid. Your sacrifice ensures some of your crew survives.\n\nCongrats, you eliminated the anomaly at the expense of your own life.", [], bg="space")
s("IGNORE_SEARCH", "As you enter the engine room, the black liquid has spread across the walls. Suddenly, a creature emerges from the liquid and attacks you in a swift motion.\n\nYou have met a tragic end.", [], bg="death")

# Safety fallback
s("NOT_FOUND", "Scene not found. Press 1 to restart.", [("1. Restart", '1', "INTRO")])

# ---------- Assets & audio ----------
def load_background(name):
    if not name:
        return None
    for ext in (".png", ".jpg", ".jpeg"):
        p = BG_DIR / (name + ext)
        if p.exists():
            return load_image_safe(p, (PORTRAIT_RECT.width, HEIGHT - 120))
    return None

def load_portrait(name):
    if not name:
        return None
    for ext in (".png", ".jpg", ".jpeg"):
        p = PORTRAITS_DIR / (name + ext)
        if p.exists():
            return load_image_safe(p, (PORTRAIT_RECT.width, PORTRAIT_RECT.height))
    return None

# background and portrait cache
bg_cache = {}
portrait_cache = {}

def get_bg(name):
    if name not in bg_cache:
        bg_cache[name] = load_background(name) or None
    return bg_cache[name]

def get_portrait(name):
    if name not in portrait_cache:
        portrait_cache[name] = load_portrait(name) or None
    return portrait_cache[name]

# Load music
if MUSIC_FILE.exists():
    try:
        mixer.music.load(str(MUSIC_FILE))
        mixer.music.set_volume(0.5)
        mixer.music.play(-1)
    except Exception as e:
        print("Could not load music:", e)

# Load typing sfx
type_sfx = None
if TYPE_SFX.exists():
    try:
        type_sfx = mixer.Sound(str(TYPE_SFX))
        type_sfx.set_volume(0.12)
    except Exception as e:
        print("Could not load type sfx:", e)

# ---------- Typewriter / state ----------
current_scene = SCENES["INTRO"]
current_display_text = current_scene.text
text_progress = 0  # characters visible
chars_per_second = 45.0  # default speed; adjustable
auto_mode = False
fast_hold = False
message_log = deque(maxlen=200)  # store fully shown scene texts
last_letter_time = 0.0
fade_alpha = 0
fading = False
fade_dir = 0  # 1 fade in, -1 fade out, 0 none
fade_speed = 800.0  # alpha per second

# Build buttons for current scene
def build_buttons_for_scene(scene):
    btns = []
    margin = 12
    # up to 3 per column (use vertical stack inside CHOICE_AREA)
    btn_w = CHOICE_AREA_RECT.width - margin * 2
    btn_h = 48
    x = CHOICE_AREA_RECT.x + margin
    y = CHOICE_AREA_RECT.y + margin
    for idx, (label, key, next_id) in enumerate(scene.choices):
        r = (x, y + idx * (btn_h + margin), btn_w, btn_h)
        btns.append(Button(r, label, key))
    if not btns:
        # Restart button
        r = (CHOICE_AREA_RECT.centerx - 80, CHOICE_AREA_RECT.y + CHOICE_AREA_RECT.height - 60, 160, 48)
        btns.append(Button(r, "Restart (1)", '1'))
    return btns

buttons = build_buttons_for_scene(current_scene)

def start_fade(direction):
    global fading, fade_dir, fade_alpha
    fading = True
    fade_dir = direction
    fade_alpha = 0 if direction == 1 else 255

def go_to_scene(scene_id):
    global current_scene, current_display_text, text_progress, buttons, last_letter_time, fading
    target = SCENES.get(scene_id, SCENES["NOT_FOUND"])
    # push current visible (fully) text into log
    message_log.append(current_scene.text)
    # set scene
    current_scene = target
    current_display_text = current_scene.text
    text_progress = 0
    buttons = build_buttons_for_scene(current_scene)
    last_letter_time = perf_counter()
    # trigger fade in
    start_fade(1)

# initialize first scene
go_to_scene("INTRO")

# ---------- Fade overlay ----------
fade_surf = pygame.Surface((WIDTH, HEIGHT))
fade_surf.fill(BLACK)

# ---------- Helpers for UI ----------
def draw_ui():
    screen.fill(DARK)

    # Background
    bg = get_bg(current_scene.bg)
    if bg:
        screen.blit(bg, (PORTRAIT_RECT.x, 40))
    else:
        # placeholder gradient
        pygame.draw.rect(screen, (25,25,40), (PORTRAIT_RECT.x, 40, PORTRAIT_RECT.width, HEIGHT - 120))

    # Portrait
    portrait = get_portrait(current_scene.portrait)
    if portrait:
        screen.blit(portrait, PORTRAIT_RECT.topleft)
    else:
        # placeholder portrait box
        pygame.draw.rect(screen, (35,35,55), PORTRAIT_RECT, border_radius=8)
        txt = FONT.render("Portrait", True, WHITE)
        screen.blit(txt, (PORTRAIT_RECT.centerx - txt.get_width()//2, PORTRAIT_RECT.centery - txt.get_height()//2))

    # Title
    title = TITLE_FONT.render("Bastion One — Psychological Horror", True, WHITE)
    screen.blit(title, TITLE_POS)

    # Text box
    pygame.draw.rect(screen, GRAY, TEXT_BOX_RECT, border_radius=10)
    pygame.draw.rect(screen, BLACK, TEXT_BOX_RECT.inflate(-6, -6), border_radius=8)

    # Name box
    pygame.draw.rect(screen, BUTTON_BG, NAME_BOX_RECT, border_radius=8)
    pygame.draw.rect(screen, BLACK, NAME_BOX_RECT.inflate(-4, -4), border_radius=6)
    speaker = current_scene.name or "Narrator"
    name_txt = NAME_FONT.render(speaker, True, WHITE)
    screen.blit(name_txt, (NAME_BOX_RECT.x + 8, NAME_BOX_RECT.y + 6))

    # Draw visible text (typewriter)
    inner_rect = TEXT_BOX_RECT.inflate(-16, -16)
    visible_text = current_display_text[:text_progress]
    draw_wrapped_text(screen, visible_text, inner_rect, FONT, WHITE)

    # Choices area
    pygame.draw.rect(screen, GRAY, CHOICE_AREA_RECT, border_radius=10)
    pygame.draw.rect(screen, BLACK, CHOICE_AREA_RECT.inflate(-6, -6), border_radius=8)
    for b in buttons:
        b.draw(screen, pygame.mouse.get_pos())

    # Controls hint
    hint = "Space=Skip  A=Auto  Shift=Fast  +/- adjust speed  L=Log"
    hint_txt = FONT.render(hint, True, WHITE)
    screen.blit(hint_txt, (40, HEIGHT - 30))

    # Speed display
    speed_txt = FONT.render(f"Text speed: {chars_per_second:.0f} cps", True, ACCENT)
    screen.blit(speed_txt, (WIDTH - 260, HEIGHT - 30))

    # If auto-mode show indicator
    if auto_mode:
        auto_txt = FONT.render("AUTO MODE", True, ACCENT)
        screen.blit(auto_txt, (WIDTH - 420, HEIGHT - 30))

# ---------- Message log UI ----------
log_open = False
def draw_log():
    # Draw modal
    pad = 60
    rect = pygame.Rect(pad, pad, WIDTH - pad*2, HEIGHT - pad*2)
    pygame.draw.rect(screen, LOG_BG, rect, border_radius=8)
    inner = rect.inflate(-12, -12)
    # Title
    t = TITLE_FONT.render("Message Log", True, WHITE)
    screen.blit(t, (inner.x, inner.y))
    # Show last N entries
    y = inner.y + 40
    for entry in reversed(message_log):
        # Draw each entry (only first 6 lines)
        lines = textwrap.wrap(entry, 90)
        for ln in lines:
            if y > inner.bottom - 30:
                break
            txt = FONT.render(ln, True, WHITE)
            screen.blit(txt, (inner.x, y))
            y += FONT.get_height() + 2
        y += 8
        if y > inner.bottom - 30:
            break
    # Close hint
    hint = FONT.render("Press L to close log", True, WHITE)
    screen.blit(hint, (inner.right - hint.get_width(), inner.bottom - 24))

# ---------- Main loop ----------
running = True
last_time = perf_counter()
while running:
    dt = clock.tick(FPS) / 1000.0
    now = perf_counter()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            break

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not log_open:
            pos = event.pos
            for b in buttons:
                if b.is_clicked(pos):
                    # find next_id by key
                    next_id = None
                    for label, key, nid in current_scene.choices:
                        if key == b.key:
                            next_id = nid
                            break
                    if not next_id and not current_scene.choices:
                        next_id = "INTRO"
                    if next_id:
                        go_to_scene(next_id)
                    break

        if event.type == pygame.KEYDOWN:
            # global toggles
            if event.key == pygame.K_SPACE:
                # Show full text
                text_progress = len(current_display_text)
            elif event.key == pygame.K_a:
                auto_mode = not auto_mode
            elif event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                fast_hold = True
            elif event.key == pygame.K_l:
                log_open = not log_open
            elif event.key == pygame.K_PLUS or event.key == pygame.K_KP_PLUS:
                chars_per_second = min(750, chars_per_second + 10)
            elif event.key == pygame.K_MINUS or event.key == pygame.K_KP_MINUS:
                chars_per_second = max(5, chars_per_second - 5)
            else:
                # choice keys '1','2','3'
                keyname = pygame.key.name(event.key)
                for label, key, nid in current_scene.choices:
                    if keyname == key:
                        go_to_scene(nid)
                        break
                # If no choices and press 1 => restart
                if not current_scene.choices and keyname == '1':
                    go_to_scene("INTRO")

        if event.type == pygame.KEYUP:
            if event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                fast_hold = False

    # Typewriter update
    effective_speed = chars_per_second * (3.0 if fast_hold else 1.0)
    if auto_mode:
        effective_speed *= 1.6

    if text_progress < len(current_display_text):
        # how many chars to reveal this frame
        to_add = effective_speed * dt
        if to_add < 1:
            # accumulate fractional progress using time
            # but for simplicity just add 1 char if enough time passed
            last_letter_time += dt
            if last_letter_time * effective_speed >= 1.0:
                add = int(last_letter_time * effective_speed)
                text_progress += add
                last_letter_time = 0.0
            # else nothing
        else:
            # add floor(to_add)
            add = max(1, int(to_add))
            text_progress += add
        # play type sfx per letter if available
        if type_sfx:
            try:
                type_sfx.play()
            except Exception:
                pass
    else:
        # fully shown - auto mode may advance after a pause
        if auto_mode:
            # after a short pause, auto-advance if there is exactly one choice (or none)
            # We'll use a simple timer
            if not hasattr(go_to_scene, "_auto_timer"):
                go_to_scene._auto_timer = now
            if now - go_to_scene._auto_timer > 1.0:
                # if there are choices, pick the first automatically
                if current_scene.choices:
                    _, _, nid = current_scene.choices[0]
                    go_to_scene(nid)
                else:
                    go_to_scene("INTRO")
                go_to_scene._auto_timer = now
        # reset letter timer
        last_letter_time = 0.0

    # Fade handling
    if fading:
        # fade in -> alpha decreases from 255 -> 0 (showing scene)
        if fade_dir == 1:
            fade_alpha -= fade_speed * dt
            if fade_alpha <= 0:
                fade_alpha = 0
                fading = False
        elif fade_dir == -1:
            fade_alpha += fade_speed * dt
            if fade_alpha >= 255:
                fade_alpha = 255
                fading = False

    # Draw UI
    draw_ui()
    if log_open:
        draw_log()

    # draw fade overlay if needed (fade alpha 0..255)
    if fade_alpha > 0:
        fade_surf.set_alpha(int(fade_alpha))
        screen.blit(fade_surf, (0,0))

    pygame.display.flip()

pygame.quit()
sys.exit()
