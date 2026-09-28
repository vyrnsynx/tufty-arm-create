"""
Keep your cricket hopping through an endless datacenter. One button. No mercy.
How far can you go?

Controls:
* B = Flap
"""

import math

badge.mode(LORES | VSYNC)

import world

from badgeware import State
from cricket import Cricket
from obstacle import Obstacle, SPEED as SCROLL

LEVEL_EVERY = 5     # pipes passed before the level, and the scene, turn over
FASTER = 1.1        # how much quicker each level runs than the one before
DISSOLVE_MS = 700   # how long the scene takes to come apart after he goes
CHANGE_MS = 1000    # how long one world takes to fade into the next

TITLE = "Cricket Hop"
HOP = 7             # pixels a letter of the title rises
HOP_MS = 260        # how long one letter is up for
WAVE_MS = 90        # how far behind each letter follows the one before
REST_MS = 1600      # from the start of one pass of the wave to the next

# Behind the title a demo cricket flies the game by itself, and the worlds
# take the screen in turns.
TITLE_WORLD_MS = 8000       # ms a world holds the title before the next fades in
DEMO_AIM = 8                # the demo flaps this far below the gap's centre

worlds = world.load()
title_font = font.futile
text_font = font.match

# colours taken from the cricket's own art
TITLE_INK = color.rgb(109, 254, 249)
TEXT_INK = color.rgb(255, 255, 255)
SHADOW = color.rgb(3, 1, 35, 220)

score = {"highscore": 0}
State.load("cricket_hop", score)

offset = 0.0        # how far the world has scrolled

# the world on screen, the one it is fading up from, and when that started
showing = None
leaving = None
changed_at = 0

# the title screen always opens on the same scene
title_scene = next(w for w in worlds if w.name == "pcb-green")


def shadow_text(text, x, y, ink=TEXT_INK, transform=None):
  if transform is None:
    transform = mat3()
  screen.pen = SHADOW
  screen.text(text, x + 2, y + 2, transform=transform)
  screen.pen = ink
  screen.text(text, x, y, transform=transform)


def center_text(text, y, ink=TEXT_INK):
  w, _ = screen.measure_text(text)
  shadow_text(text, 80 - (w / 2), y, ink)


def hop_rise(n):
  """How far the nth letter of the title has hopped."""
  beat = (badge.ticks - n * WAVE_MS) % REST_MS
  return math.sin(beat / HOP_MS * math.pi) * HOP if beat < HOP_MS else 0


def breath():
  """Pulsing alpha for the prompt, cycling 115 to 255."""
  return int(115 + 140 * (math.sin(badge.ticks / 380) * 0.5 + 0.5))


def demo_target():
  """The centre of the gap ahead of the demo cricket, or mid air without one."""
  ahead = [o for o in Obstacle.obstacles if o.x + 32 > 10]
  if not ahead:
    return 60
  gap = min(ahead, key=lambda o: o.x)
  return gap.gap_y + gap.gap_height / 2


def draw_title(y):
  """The title, with a hop running along it letter by letter."""
  screen.font = title_font
  x = (160 - screen.measure_text(TITLE)[0]) / 2

  for n, letter in enumerate(TITLE):
    shadow_text(letter, x, y, TITLE_INK, mat3().translate(0, -hop_rise(n)))
    x += screen.measure_text(letter)[0]


def level_at(passed):
  """The level after this many pipes, counting from one."""
  return passed // LEVEL_EVERY + 1


def scene(passed):
  """The world in play, which changes with the level and cycles round."""
  return worlds[(level_at(passed) - 1) % len(worlds)]


def changing():
  """How far the fade to the world coming in has got, or None between changes."""
  if leaving is None:
    return None
  part = (badge.ticks - changed_at) / CHANGE_MS
  return part if part < 1 else None


def draw_world(wanted, moving, faster=1.0):
  global offset, showing, leaving, changed_at

  if moving:
    offset += SCROLL * faster * (badge.ticks_delta / 1000)

  if wanted is not showing:
    leaving, showing, changed_at = showing, wanted, badge.ticks

  # black fill behind the art, so nothing flashes through the seams
  screen.pen = color.rgb(0, 0, 0)
  screen.rectangle(0, 0, 160, 120)

  part = changing()
  if part is None:
    leaving = None
    showing.draw(offset)
  else:
    # the art is opaque, so the world coming in only has to rise over the one
    # going out
    leaving.draw(offset)
    screen.alpha = int(255 * part)
    showing.draw(offset)
    screen.alpha = 255


def snap_world(wanted):
  """Open on a world with no fade, so a screen does not drag the last one in."""
  global showing, leaving
  showing, leaving = wanted, None


def draw_front():
  """The near layers, which the cricket passes behind."""
  part = changing()
  if part is None:
    showing.draw_front(offset)
  else:
    # these sit over the scene, so both sides of the change are mixed
    screen.alpha = int(255 * (1 - part))
    leaving.draw_front(offset)
    screen.alpha = int(255 * part)
    showing.draw_front(offset)
    screen.alpha = 255


def titles():
  """The title screen, until B lets the cricket go.

  Behind the type a demo cricket plays the game by itself, flapping whenever
  it sinks below the next gap, while the worlds take the screen in turns.
  """
  snap_world(title_scene)
  showing_n = worlds.index(title_scene)
  world_due = badge.ticks + TITLE_WORLD_MS

  demo = Cricket()
  Obstacle.obstacles = []
  Obstacle.next_spawn_time = badge.ticks + 500
  demo.jump()

  while True:
    if badge.ticks >= world_due:
      showing_n += 1
      world_due = badge.ticks + TITLE_WORLD_MS
    draw_world(worlds[showing_n % len(worlds)], True)

    # the demo flight, put back on its wings once a death has played out
    if not demo.is_dead():
      if demo.velocity > 0 and demo.pos[1] + 16 > demo_target() + DEMO_AIM:
        demo.jump()
      if badge.ticks > Obstacle.next_spawn_time:
        Obstacle.spawn()
    elif demo.is_done_dying():
      demo = Cricket()
      Obstacle.obstacles = []
      Obstacle.next_spawn_time = badge.ticks + 500
      demo.jump()

    demo.update()
    for obstacle in Obstacle.obstacles:
      obstacle.update()
      obstacle.draw()
    demo.draw()
    draw_front()

    # the type reads over a knockback light enough to watch the game through
    screen.pen = color.rgb(0, 0, 0, 110)
    screen.rectangle(0, 0, 160, 120)

    draw_title(23)

    screen.font = text_font
    center_text("TAP B TO FLAP", 56)
    center_text("SLIP THROUGH THE GAPS", 67)
    center_text("HIGHEST SCORE %d" % score["highscore"], 84, TITLE_INK)

    # the prompt breathes
    center_text("PRESS B TO START", 101, color.rgb(255, 255, 255, breath()))

    screen.crt(2, 28)
    badge.update()

    if badge.pressed(BUTTON_B):
      return


def dissolve(cricket):
  """The scene comes apart after he does, on the way back to the titles."""
  started = badge.ticks

  while badge.ticks - started < DISSOLVE_MS:
    part = (badge.ticks - started) / DISSOLVE_MS

    draw_world(scene(cricket.score), False)
    for obstacle in Obstacle.obstacles:
      obstacle.draw()
    cricket.draw()

    screen.glitch(round(2 + part * 22))
    screen.chromatic(round(1 + part * 4))
    screen.pen = color.rgb(0, 0, 0, int(part * 255))
    screen.rectangle(0, 0, 160, 120)

    screen.crt(2, 28)
    badge.update()


def draw_final(cricket):
  """What he scored, sat over his death, and the way on once it has played."""
  heading = "NEW BEST!" if cricket.score > score["highscore"] else "YOU SCORED"

  screen.font = title_font
  center_text(heading, 28)
  center_text("%d" % cricket.score, 48, TITLE_INK)

  # blink the prompt, half a second on and half a second off
  if cricket.is_done_dying() and int(badge.ticks / 500) % 2:
    screen.font = text_font
    center_text("PRESS B TO CONTINUE", 101)


def play():
  """One run, from the first flap to the button press after he goes. Gives the score."""
  cricket = Cricket()
  Obstacle.obstacles = []
  Obstacle.next_spawn_time = badge.ticks + 500
  snap_world(scene(0))

  # an opening jump, giving a moment to react
  cricket.jump()

  while True:
    flying = not cricket.is_dead()
    level = level_at(cricket.score)
    faster = FASTER ** (level - 1)

    if flying and badge.pressed(BUTTON_B):
      cricket.jump()

    cricket.update()

    if flying and badge.ticks > Obstacle.next_spawn_time:
      Obstacle.spawn(faster)

    # the world only moves while he is still in the game
    draw_world(scene(cricket.score), flying, faster)

    for obstacle in Obstacle.obstacles:
      if flying:
        obstacle.update(faster)
      obstacle.draw()

    cricket.draw()
    draw_front()

    screen.crt(2, 28)

    # the score and level go on after the filter, on a bar of their own, so
    # they stay sharp whatever is scrolling past behind
    if flying:
      screen.pen = color.rgb(0, 0, 0, 150)
      screen.rectangle(0, 0, 160, 15)
      screen.font = text_font
      screen.pen = TEXT_INK
      screen.text("Score: %d" % cricket.score, 3, 0)
      reading = "Level: %d" % level
      screen.text(reading, 157 - screen.measure_text(reading)[0], 0)
    else:
      draw_final(cricket)

    badge.update()

    # the press only counts once the death has finished playing, so mashing B
    # at the moment he hits something cannot skip past his score
    if not flying and cricket.is_done_dying() and badge.pressed(BUTTON_B):
      dissolve(cricket)
      return cricket.score


while True:
  titles()
  final = play()

  if final > score["highscore"]:
    score["highscore"] = final
    State.save("cricket_hop", score)
