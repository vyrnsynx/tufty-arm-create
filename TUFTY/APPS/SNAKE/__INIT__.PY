"""
Keep moving, keep growing, and don't hit your tail. How long can you survive?

The snake always creeps forward and traces its own path exactly. Touching a wall
or your own body ends the run.

Controls:
* A = Steer left
* C = Steer right
* B = Start / restart
"""

import math
import micropython
import random

import branding as brand


# High resolution, unlocked framerate.
screen.pen = color.rgb(0, 0, 0)
badge.mode(HIRES)
screen.antialias = image.X2

CX, CY = screen.width / 2, screen.height / 2

_, bold_font = brand.fonts()

# Point sizes for Lato.
TITLE_SIZE = 62
HEADING_SIZE = 36

# Text is placed by its cap line rather than its em box.
CAP_TOP = brand.CAP_TOP
CAP_MID = brand.CAP_MID

# Shared artwork sitting behind the grid, drawn at its own size: it is cut to
# the screen, so the play area shows the part of it that lies under the bar.
BACKDROP = brand.backdrop()

# Apples are Arm line art, drawn as shapes at whatever size they are placed.
# Sizing by the longest side keeps each one's own aspect.
APPLE_SIZE = 30
APPLE_SWELL = 0.12          # how far the apple breathes either side of that
APPLE_NAMES = ("ai", "automotive", "edge_ai", "laptops")

APPLE_ICONS = [brand.VectorArt("assets/%s.svg" % n) for n in APPLE_NAMES]

# Palette drawn from the Arm design system: cyan snake, orange apple, white text.
ARM_CYAN = brand.cyan
ARM_DARK_BLUE = brand.dark_blue
ARM_WHITE = brand.white

BACKGROUND = color.rgb(0, 0, 0)
SNAKE = color.rgb(2, 234, 234)
EYE = ARM_DARK_BLUE
TEXT = ARM_WHITE

HUD_H = 44                  # height of the top HUD bar; play area starts below

# a level every LEVEL_APPLES apples, each quicker. The turn rate scales with
# the speed so the turning circle stays the same size.
LEVEL_APPLES = 10
SPEED_STEP = 0.011
SPEED_MAX = 0.155

# Movement, in units per millisecond so motion is framerate independent.
SPEED = 0.075                # forward pixels per ms at level 1
TURN = 0.0045                # radians per ms
SPACING = 4.0                # distance between recorded path points
START_POINTS = 14            # body length, in path points
GROW_POINTS = 3              # points added per apple
MAX_DT = 50                  # clamp long frames so a stall can't teleport us

# Snake body outline half-widths (a slender body with a subtly bulbous head).
BODY_HALF = 2.6
HEAD_EXTRA = 2.1
WALL_MARGIN = 4             # play-area inset used for collision
EAT_RADIUS = 15             # from head centre; tracks the apple's half width
NECK_SKIP = 8                # body points near the head ignored for self-collision

# Bloom post-process: bloom(threshold, intensity, radius, strength). A fixed
# ~18ms for the whole screen, regardless of radius or threshold.
BLOOM_ARGS = (60, 255, 7.5, 3.0)
# The glow reaches 24px from the centreline, so the box has to stand further off
# than that or it slices the halo and the box edge shows.
BLOOM_PAD = 30

_sqrt = math.sqrt


@micropython.native
def build_ribbon(head, path, buf, body_half, head_extra):
  # Write the closed body outline into the preallocated `buf` (2n vec2). For
  # centreline point i the left vertex goes to buf[i] and the right vertex to
  # buf[2n-1-i], so one pass fills both sides of the ribbon. Existing vec2
  # objects are mutated rather than reallocated. Hot path, hence native.
  n = len(path) + 1
  total = n + n
  for i in range(n):
    if i == 0:
      cur = head
      a = head
    else:
      cur = path[i - 1]
      a = head if i == 1 else path[i - 2]
    b = path[i] if i < n - 1 else cur

    cx = cur.x
    cy = cur.y
    tx = a.x - b.x
    ty = a.y - b.y
    length = _sqrt(tx * tx + ty * ty)
    if length > 0.0:
      nx = -ty / length
      ny = tx / length
    else:
      nx = 0.0
      ny = 0.0

    # Width profile: pointed nose, a bulge behind it, tapered tail.
    nose = (i + 0.3) * 0.5
    if nose > 1.0:
      nose = 1.0
    tail = (n - 1 - i) * 0.25 + 0.25
    if tail > 1.0:
      tail = 1.0
    d = i - 3
    if d < 0:
      d = -d
    bulge = 1.0 - d / 3.0
    if bulge < 0.0:
      bulge = 0.0
    m = nose if nose < tail else tail
    half = (body_half + head_extra * bulge) * m

    ox = nx * half
    oy = ny * half
    lp = buf[i]
    lp.x = cx + ox
    lp.y = cy + oy
    rp = buf[total - 1 - i]
    rp.x = cx - ox
    rp.y = cy - oy


class Snake:
  def __init__(self):
    self.reset()

  def reset(self):
    self.heading = -math.pi / 2
    self.head = vec2(CX, CY + 40)
    self.target_points = START_POINTS
    self._buf = []  # reused ribbon vertex buffer (list of vec2)
    # Seed the trailing path so the snake starts at full length.
    dx = -math.cos(self.heading) * SPACING
    dy = -math.sin(self.heading) * SPACING
    self.path = [vec2(self.head.x + dx * i, self.head.y + dy * i)
                 for i in range(1, self.target_points + 1)]

  def update(self, dt):
    turn = TURN * (speed() / SPEED)
    if badge.held(BUTTON_A):
      self.heading -= turn * dt
    if badge.held(BUTTON_C):
      self.heading += turn * dt

    rate = speed()
    step = rate * dt
    self.head = vec2(self.head.x + math.cos(self.heading) * step,
                     self.head.y + math.sin(self.heading) * step)

    # Record a new path point once we've travelled far enough from the last.
    front = self.path[0]
    if (self.head.x - front.x) ** 2 + (self.head.y - front.y) ** 2 >= SPACING * SPACING:
      self.path.insert(0, vec2(self.head.x, self.head.y))

    while len(self.path) > self.target_points:
      self.path.pop()

  def grow(self):
    self.target_points += GROW_POINTS

  def wander(self, dt):
    # Attract-mode autopilot: look ahead and, when nearing a wall, steer
    # back toward the centre; otherwise drift gently.
    dx, dy = math.cos(self.heading), math.sin(self.heading)
    ax = self.head.x + dx * 46
    ay = self.head.y + dy * 46
    m = WALL_MARGIN + 34
    if (ax < m or ax > screen.width - m
            or ay < m or ay > screen.height - m):
      # Turn toward the centre, choosing the shorter way round.
      cross = dx * (CY - self.head.y) - dy * (CX - self.head.x)
      rate = TURN * dt * 1.6
      self.heading += rate if cross > 0 else -rate
    else:
      self.heading += math.sin(badge.ticks / 800.0) * TURN * dt * 0.25

  def glow(self):
    """Bloom only the box the body occupies.

    bloom() costs in proportion to the pixels covered: full screen is ~18ms,
    this box 1-3ms. window() is used over clip(), which has a ~7ms floor.
    """
    # find the body's bounding box
    x0 = x1 = self.head.x
    y0 = y1 = self.head.y
    for p in self.path:
      if p.x < x0:
        x0 = p.x
      elif p.x > x1:
        x1 = p.x
      if p.y < y0:
        y0 = p.y
      elif p.y > y1:
        y1 = p.y

    x0 = max(0, int(x0) - BLOOM_PAD)
    y0 = max(0, int(y0) - BLOOM_PAD)
    x1 = min(screen.width, int(x1) + BLOOM_PAD)
    y1 = min(screen.height, int(y1) + BLOOM_PAD)
    if x1 > x0 and y1 > y0:
      screen.window(rect(x0, y0, x1 - x0, y1 - y0)).bloom(*BLOOM_ARGS)

  def hit_wall(self):
    return (self.head.x < WALL_MARGIN or self.head.x > screen.width - WALL_MARGIN
            or self.head.y < HUD_H + WALL_MARGIN or self.head.y > screen.height - WALL_MARGIN)

  def hit_self(self):
    limit = (BODY_HALF * 2) ** 2
    for point in self.path[NECK_SKIP:]:
      if (self.head.x - point.x) ** 2 + (self.head.y - point.y) ** 2 < limit:
        return True
    return False

  def draw(self):
    n = len(self.path) + 1
    if n < 2:
      return

    # Reuse the ribbon buffer; only grow/shrink it when the length changes.
    total = n + n
    buf = self._buf
    while len(buf) < total:
      buf.append(vec2(0.0, 0.0))
    if len(buf) > total:
      del buf[total:]

    build_ribbon(self.head, self.path, buf, BODY_HALF, HEAD_EXTRA)

    screen.pen = SNAKE
    screen.shape(shape.custom(buf))

    self._draw_head(self.head, self.path[0])

  def _draw_head(self, nose, behind):
    dx, dy = nose.x - behind.x, nose.y - behind.y
    length = math.sqrt(dx * dx + dy * dy)
    if length == 0:
      return
    dx, dy = dx / length, dy / length
    nx, ny = -dy, dx

    # Two subtle eyes set back from the nose, one either side of the spine.
    ex = nose.x - dx * 3.0
    ey = nose.y - dy * 3.0
    screen.pen = EYE
    for side in (-1, 1):
      screen.shape(shape.circle(ex + nx * 1.9 * side, ey + ny * 1.9 * side, 1.2))


class Apple:
  def __init__(self):
    self.position = vec2(CX, CY)
    self.index = -1             # respawn steps this on, so the first is 0
    self.respawn(None)

  def respawn(self, snake):
    # Keep the whole apple clear of the walls and the HUD bar.
    m = WALL_MARGIN + APPLE_SIZE // 2
    x0, x1 = m, screen.width - m
    y0, y1 = HUD_H + m, screen.height - m
    # each apple is the next icon in turn, so all four come round
    self.index = (self.index + 1) % len(APPLE_ICONS)
    self.icon = APPLE_ICONS[self.index]
    for _ in range(30):
      candidate = vec2(random.randint(x0, x1), random.randint(y0, y1))
      if snake is None:
        self.position = candidate
        return
      dx = candidate.x - snake.head.x
      dy = candidate.y - snake.head.y
      if dx * dx + dy * dy > 60 * 60:
        self.position = candidate
        return
    self.position = candidate

  def draw(self):
    # the apple pulses in size; EAT_RADIUS stays fixed so the target does not
    swell = 1.0 + math.sin(badge.ticks / 300.0) * APPLE_SWELL
    self.icon.draw(self.position.x, self.position.y, APPLE_SIZE * swell)


HUD_LABEL_RGB = (152, 163, 171)
INTRO_LABEL = color.rgb(*HUD_LABEL_RGB)

# --- intro screen ---------------------------------------------------------
# Title at the top, attract-mode snake through the middle, call to action low,
# controls along the bottom. Key caps are rounded rects shaded like the real
# buttons: base shadow, lit face, gloss on the top half.
KEY_EDGE = ARM_CYAN
KEY_GREEN = (149, 214, 0)   # brand.green, as a tuple so the breathing alpha can ride it
KEY_RADIUS = 0.34           # corner radius as a fraction of the half width
KEY_LIFT = 3                # how far the shadow sits below the cap
KEY_SHADOW = color.rgb(0, 0, 0, 160)
KEY_TOP = (44, 74, 96)      # face gradient, lit edge
KEY_BOTTOM = (9, 20, 32)    # ... and the shaded one
KEY_GLOSS = color.rgb(255, 255, 255, 60)

TITLE_CAP_Y = 46
# Wobble: a bob, and a squash on each axis out of phase with it.
TITLE_BOB = 4.0
TITLE_SQUASH = 0.04

CTA_CAP_Y = 168
CTA_SIZE = 25
CTA_KEY_R = 18
CTA_GAP = 11

STRIP_Y = 213
STRIP_KEY_R = 13
STRIP_SIZE = 15


def draw_key(cx, cy, r, label, edge):
  """A shaded key cap centred on cx, cy, labelled with its button letter.

  Each rounded rect is built fresh: stroke() consumes the shape it is called
  on, and the face gradient is positioned in screen space so it has to be made
  where the cap sits.
  """
  d = r * 2
  x, y = cx - r, cy - r
  rad = r * KEY_RADIUS

  # drop shadow under the cap
  screen.pen = KEY_SHADOW
  screen.shape(shape.rounded_rectangle(x, y + KEY_LIFT, d, d, rad))

  # the face, lit from above
  screen.pen = brush.gradient(
      brush.LINEAR, 0, y, 0, y + d,
      ((0.0, color.rgb(KEY_TOP[0], KEY_TOP[1], KEY_TOP[2])),
       (1.0, color.rgb(KEY_BOTTOM[0], KEY_BOTTOM[1], KEY_BOTTOM[2]))))
  screen.shape(shape.rounded_rectangle(x, y, d, d, rad))

  # gloss across the top half
  screen.pen = KEY_GLOSS
  screen.shape(shape.rounded_rectangle(x + 2, y + 2, d - 4, d * 0.42, rad * 0.8))

  # coloured outline
  screen.pen = edge
  screen.shape(shape.rounded_rectangle(x, y, d, d, rad).stroke(2))

  # the letter, centred on the cap
  size = r * 1.15
  screen.font = bold_font
  screen.pen = TEXT
  w, _ = screen.measure_text(label, size)
  screen.text(label, cx - w / 2, cy - size * CAP_MID, size)


# --- game over screen -----------------------------------------------------
# A scoreboard: the run dimmed behind, the figures in a ruled 2x2 grid with each
# cell centred in its column, label over value as the bar does during play.
GO_DIM = color.rgb(0, 0, 0, 135)

GO_HEADING_CAP = 32

GO_COL_CX = (100, 220)      # centre of each column
GO_ROW_CAP = (85, 141)      # cap line of each row's label
GO_VALUE_DROP = 14          # value cap sits this far under its label
GO_LABEL_SIZE = 14
GO_VALUE_SIZE = 30

GO_RULE = color.rgb(40, 62, 80)
GO_RULE_X = 160             # divider between the columns
GO_RULE_TOP, GO_RULE_BOT = 68, 191
GO_RULE_Y = 130             # divider between the rows
GO_RULE_L, GO_RULE_R = 44, 276

GO_PROMPT = "PRESS ANY KEY"
GO_PROMPT_CAP = 200
GO_PROMPT_SIZE = 17

# --- in game HUD ----------------------------------------------------------
# Three groups across the bar, each a small label over its value. The eaten
# count shows the apple in play beside a multiplier.
HUD_GROUND = color.rgb(0, 0, 0, 150)
HUD_LABEL_SIZE = 14
HUD_VALUE_SIZE = 18
HUD_LABEL_CAP = 11          # cap line of the label row
HUD_VALUE_CAP = 24          # ... and of the value row, clear of the meter
HUD_MARGIN = 12

# below about 30px the line art strokes fall under a pixel, so the icon is
# drawn full size beside the readout
HUD_APPLE = 30
HUD_ICON_GAP = 7
HUD_ICON_CY = 21            # the icon spans both rows, centred on them

# level progress, a strip along the bar's bottom edge; its colour steps with
# the level
METER_H = 4
METER_EMPTY = color.rgb(16, 38, 56)
METER_LAPS = (SNAKE, brand.green, brand.orange_accent)

run_started = None
run_ended = None

# channel split when an apple is eaten, decaying over IMPACT_MS. Applied at
# the end of the frame so it covers the HUD too. chromatic() costs a flat
# ~6ms, so it is skipped once the effect has faded.
IMPACT_MS = 220
IMPACT_MAX = 7.0
impact_at = None


def draw_impact():
  if impact_at is None:
    return
  age = badge.ticks - impact_at
  if 0 <= age < IMPACT_MS:
    screen.chromatic(IMPACT_MAX * (1.0 - age / IMPACT_MS))


def elapsed():
  """Time on the current run, counting up."""
  if run_started is None:
    return "00:00"
  end = badge.ticks if run_ended is None else run_ended
  t = (end - run_started) // 1000
  return "%02d:%02d" % (t // 60 % 100, t % 60)


def level():
  return score // LEVEL_APPLES + 1


def speed():
  return min(SPEED_MAX, SPEED + (level() - 1) * SPEED_STEP)


def draw_top_bar():
  screen.pen = HUD_GROUND
  screen.rectangle(0, 0, screen.width, HUD_H)

  label_y = HUD_LABEL_CAP - HUD_LABEL_SIZE * CAP_TOP
  value_y = HUD_VALUE_CAP - HUD_VALUE_SIZE * CAP_TOP
  screen.font = bold_font

  # LEVEL against the left margin
  screen.pen = INTRO_LABEL
  screen.text("LEVEL", HUD_MARGIN, label_y, HUD_LABEL_SIZE)
  screen.pen = TEXT
  screen.text("%02d" % level(), HUD_MARGIN, value_y, HUD_VALUE_SIZE)

  # EATEN centred: the apple in play standing beside the count
  icon = apple.icon
  iw, _ = icon.size(HUD_APPLE)
  count = "x%02d" % score
  cw, _ = screen.measure_text(count, HUD_VALUE_SIZE)
  lw2, _ = screen.measure_text("EATEN", HUD_LABEL_SIZE)
  tx = iw + HUD_ICON_GAP
  gx = CX - (tx + max(cw, lw2)) / 2

  icon.draw(gx + iw / 2, HUD_ICON_CY, HUD_APPLE)
  screen.pen = INTRO_LABEL
  screen.text("EATEN", gx + tx, label_y, HUD_LABEL_SIZE)
  screen.pen = TEXT
  screen.text(count, gx + tx, value_y, HUD_VALUE_SIZE)

  # TIME against the right margin
  stamp = elapsed()
  sw, _ = screen.measure_text(stamp, HUD_VALUE_SIZE)
  lw, _ = screen.measure_text("TIME", HUD_LABEL_SIZE)
  right = screen.width - HUD_MARGIN
  screen.pen = INTRO_LABEL
  screen.text("TIME", right - lw, label_y, HUD_LABEL_SIZE)
  screen.pen = TEXT
  screen.text(stamp, right - sw, value_y, HUD_VALUE_SIZE)

  # progress to the next level, along the bar's bottom edge
  done = (score % LEVEL_APPLES) / LEVEL_APPLES
  screen.pen = METER_EMPTY
  screen.rectangle(0, HUD_H - METER_H, screen.width, METER_H)
  screen.pen = METER_LAPS[(level() - 1) % len(METER_LAPS)]
  screen.rectangle(0, HUD_H - METER_H, screen.width * done, METER_H)


snake = Snake()
apple = Apple()
score = 0


def breath():
  """Pulsing alpha for prompts, cycling 115 to 255."""
  return int(115 + 140 * (math.sin(badge.ticks / 380.0) * 0.5 + 0.5))


def ground(top):
  """Black behind the HUD bar, the artwork under the play area."""
  screen.pen = BACKGROUND
  screen.clear()
  here = rect(0, top, screen.width, screen.height - top)
  screen.blit(BACKDROP, here, here)


def draw_wordmark():
  """SNAKE, bobbing and squashing about its cap line."""
  t = badge.ticks
  bob = math.sin(t / 520.0) * TITLE_BOB
  sx = 1.0 + math.sin(t / 760.0) * TITLE_SQUASH
  sy = 1.0 + math.sin(t / 760.0 + 1.9) * TITLE_SQUASH

  screen.font = bold_font
  wide, _ = screen.measure_text("SNAKE", TITLE_SIZE)
  screen.pen = brand.orange_gradient(CX - wide / 2, wide)
  screen.text("SNAKE", CX - wide / 2, TITLE_CAP_Y - TITLE_SIZE * CAP_TOP,
              TITLE_SIZE,
              transform=mat3().translate(CX, TITLE_CAP_Y + bob)
              .scale(sx, sy).translate(-CX, -TITLE_CAP_Y))


def draw_start_line():
  """PRESS B TO START, with the key cap set into the sentence."""
  alpha = breath()
  screen.font = bold_font
  head, tail = "PRESS", "TO START"
  # measure the parts, then centre the whole line and walk across it
  hw, _ = screen.measure_text(head, CTA_SIZE)
  tw, _ = screen.measure_text(tail, CTA_SIZE)
  x = CX - (hw + CTA_GAP + CTA_KEY_R * 2 + CTA_GAP + tw) / 2
  y = CTA_CAP_Y - CTA_SIZE * CAP_MID

  screen.pen = color.rgb(255, 255, 255, alpha)
  screen.text(head, x, y, CTA_SIZE)
  x += hw + CTA_GAP
  draw_key(x + CTA_KEY_R, CTA_CAP_Y, CTA_KEY_R, "B",
           color.rgb(KEY_GREEN[0], KEY_GREEN[1], KEY_GREEN[2], alpha))
  x += CTA_KEY_R * 2 + CTA_GAP
  screen.pen = color.rgb(255, 255, 255, alpha)
  screen.text(tail, x, y, CTA_SIZE)


def draw_steer_line():
  """Use A & C to steer, with the key caps set into the sentence."""
  screen.font = bold_font
  lead, amp, tail = "Use ", " & ", " to steer"
  # measure the parts, then centre the whole line and walk across it
  lw, _ = screen.measure_text(lead, STRIP_SIZE)
  aw, _ = screen.measure_text(amp, STRIP_SIZE)
  tw, _ = screen.measure_text(tail, STRIP_SIZE)
  step = STRIP_KEY_R * 2
  x = CX - (lw + step + aw + step + tw) / 2
  y = STRIP_Y - STRIP_SIZE * CAP_MID

  screen.pen = INTRO_LABEL
  screen.text(lead, x, y, STRIP_SIZE)
  x += lw
  draw_key(x + STRIP_KEY_R, STRIP_Y, STRIP_KEY_R, "A", KEY_EDGE)
  x += step
  screen.pen = INTRO_LABEL
  screen.text(amp, x, y, STRIP_SIZE)
  x += aw
  draw_key(x + STRIP_KEY_R, STRIP_Y, STRIP_KEY_R, "C", KEY_EDGE)
  x += step
  screen.pen = INTRO_LABEL
  screen.text(tail, x, y, STRIP_SIZE)


def draw_figures():
  """The run's stats as a 2x2 grid over the dimmed screen."""
  # dim the run behind the figures
  screen.pen = GO_DIM
  screen.rectangle(0, 0, screen.width, screen.height)

  # GAME OVER heading
  screen.font = bold_font
  wide, _ = screen.measure_text("GAME OVER", HEADING_SIZE)
  screen.pen = brand.orange_gradient(CX - wide / 2, wide)
  screen.text("GAME OVER", CX - wide / 2,
              GO_HEADING_CAP - HEADING_SIZE * CAP_TOP, HEADING_SIZE)

  # rules between the grid's cells
  screen.pen = GO_RULE
  screen.rectangle(GO_RULE_X, GO_RULE_TOP, 1, GO_RULE_BOT - GO_RULE_TOP)
  screen.rectangle(GO_RULE_L, GO_RULE_Y, GO_RULE_R - GO_RULE_L, 1)

  # the four readings, each centred in its cell, label over value
  screen.font = bold_font
  for n, (label, value) in enumerate((("LEVEL", "%02d" % level()),
                                      ("EATEN", "%02d" % score),
                                      ("LENGTH", "%d" % (len(snake.path) + 1)),
                                      ("TIME", elapsed()))):
    cx = GO_COL_CX[n % 2]
    cap = GO_ROW_CAP[n // 2]

    screen.pen = INTRO_LABEL
    wide, _ = screen.measure_text(label, GO_LABEL_SIZE)
    screen.text(label, cx - wide / 2, cap - GO_LABEL_SIZE * CAP_TOP, GO_LABEL_SIZE)

    screen.pen = TEXT
    wide, _ = screen.measure_text(value, GO_VALUE_SIZE)
    screen.text(value, cx - wide / 2,
                cap + GO_VALUE_DROP - GO_VALUE_SIZE * CAP_TOP, GO_VALUE_SIZE)

  # the pulsing prompt below the grid
  screen.pen = color.rgb(255, 255, 255, breath())
  wide, _ = screen.measure_text(GO_PROMPT, GO_PROMPT_SIZE)
  screen.text(GO_PROMPT, CX - wide / 2,
              GO_PROMPT_CAP - GO_PROMPT_SIZE * CAP_TOP, GO_PROMPT_SIZE)


def titles():
  """The snake wandering under the wordmark, until B lets it loose."""
  snake.reset()

  while True:
    ground(0)
    step = min(badge.ticks_delta, MAX_DT)
    snake.wander(step)
    snake.update(step)
    snake.draw()
    snake.glow()

    draw_wordmark()
    draw_start_line()
    draw_steer_line()
    badge.update()

    if badge.pressed(BUTTON_B):
      return


def play():
  """One run, until a wall or its own tail."""
  global score, run_started, run_ended, impact_at

  snake.reset()
  apple.respawn(snake)
  score = 0
  run_started, run_ended, impact_at = badge.ticks, None, None

  while True:
    ground(HUD_H)
    snake.update(min(badge.ticks_delta, MAX_DT))

    # eat the apple when the head is within EAT_RADIUS of it
    dx = snake.head.x - apple.position.x
    dy = snake.head.y - apple.position.y
    if dx * dx + dy * dy < EAT_RADIUS * EAT_RADIUS:
      snake.grow()
      score += 1
      apple.respawn(snake)
      impact_at = badge.ticks

    snake.draw()
    snake.glow()
    apple.draw()
    draw_top_bar()
    # last, so the split carries the HUD with it
    draw_impact()
    badge.update()

    if snake.hit_wall() or snake.hit_self():
      run_ended = badge.ticks
      return


def game_over():
  """The figures over where it came to rest, until any button clears them."""
  while True:
    ground(0)
    snake.draw()
    snake.glow()
    apple.draw()
    draw_figures()
    draw_impact()
    badge.update()

    if badge.pressed(BUTTON_A) or badge.pressed(BUTTON_B) or badge.pressed(BUTTON_C):
      return


while True:
  titles()
  play()
  game_over()
