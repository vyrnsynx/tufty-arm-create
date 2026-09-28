import math

import svg

# Arm design system palette
black = color.rgb(0, 0, 0)
dark_blue = color.rgb(0, 43, 73)        # --arm-dark-blue
cyan = color.rgb(0, 193, 222)           # --arm-light-blue
green = color.rgb(149, 214, 0)          # the lime end of the icon gradients
blue = color.rgb(0, 145, 189)           # brand blue, Pantone 313 C
white = color.rgb(255, 255, 255)
orange_accent = color.rgb(255, 174, 45)  # the far end of the line art gradient
muted = color.rgb(163, 168, 174)        # type that is present but secondary
divider = color.rgb(78, 78, 78)         # the rule in the Arm Developer lockup

WIDTH, HEIGHT = 320, 240

# The lockup is the wordmark, a rule, then "Developer", sized so the label's
# caps stand exactly as tall as the mark and the two sit on a shared baseline.
# Measured on device: the mark inks 0.95 of its height from y, Lato's caps run
# 0.625 of the text size and its baseline falls 0.975 of the size below y.
MARK_INK = 0.95
CAP_TOP = 0.35
CAP_HEIGHT = 0.625
CAP_MID = CAP_TOP + CAP_HEIGHT / 2      # for centring type on a line
BASELINE = 0.975

WORDMARK_X, WORDMARK_Y = 14, 12
WORDMARK_HEIGHT = 16

LOCKUP_SIZE = int(WORDMARK_HEIGHT * MARK_INK / CAP_HEIGHT)
LOCKUP_Y = WORDMARK_Y + int(WORDMARK_HEIGHT * MARK_INK - LOCKUP_SIZE * BASELINE)

# The rule stands equally clear of the ink at both ends: the mark's last
# column is its full width, and Lato sets D two columns right of the text
# position. Its place depends on the mark's aspect, so it is computed with
# the art in draw_header().
GAP = 10
LABEL_BEARING = 2
DIVIDER_Y, DIVIDER_HEIGHT = 8, 24

# the single dimmed level used for secondary UI
KNOCKBACK = 64          # 25% of 255

BATTERY_X, BATTERY_Y = 289, 7
BATTERY_W, BATTERY_H = 23, 12
BATTERY_LOW = 15        # percent, under which the indicator blinks
BATTERY_BLINK = 500     # ms per half cycle

# The orange ramp Arm's line art is filled with. A gradient is positioned in
# screen space, so each use spans the width it covers; alpha dims it. A shape
# drawn through a matrix passes that matrix's inverse here, which keeps the
# ramp lying across the screen.
def orange_gradient(x, width, alpha=255, matrix=None):
  stops = ((0.0, color.rgb(242, 100, 25, alpha)),
           (1.0, color.rgb(255, 174, 45, alpha)))
  if matrix is None:
    return brush.gradient(brush.LINEAR, x, 0, x + width, 0, stops)
  return brush.gradient(brush.LINEAR, x, 0, x + width, 0, stops, matrix)


white_dim = color.rgb(255, 255, 255, KNOCKBACK)

HEADER_HEIGHT = 40
WASH_RECT = rect(0, HEADER_HEIGHT, WIDTH, HEIGHT - HEADER_HEIGHT)

# The navigation row: a chevron over button A and another over C, with a track
# between them showing how far along a set of cards we are. Measured against
# the hardware at HIRES: A sits under 60, B under 160, C under 260, evenly
# spaced and centred on the screen. The example in badgeware-docs
# guides/buttons.md is illustrative, not to scale.
NAV_A_X = 52
NAV_C_X = 252
NAV_W = 9           # tip to open end
NAV_H = 6           # half the height of the opening
NAV_STROKE = 2
NAV_GAP = 8
NAV_Y = 217         # the track's top, with the chevrons centred on it
NAV_HEIGHT = 3
NAV_TOP = NAV_Y + NAV_HEIGHT / 2 - NAV_H    # the highest the row's ink reaches
# one gradient spans the whole row, so the chevrons, track and thumb each
# sample it where they sit and read as one element
NAV_LEFT = NAV_A_X - NAV_W / 2
NAV_SPAN = (NAV_C_X + NAV_W / 2) - NAV_LEFT

nav_full = None     # the row's gradients, built with the first draw_nav()
nav_dim = None
nav_label_pens = {}     # the label's gradient at each breathe step

# an optional label under button B, naming the one action the chevrons do not
NAV_LABEL_SIZE = 14
NAV_LABEL_TOP = 227     # cap top, below the lifted row
NAV_LABEL_NUDGE = -7    # measured: centred on B needs this much left
NAV_LABEL_PULSE_MS = 2400
NAV_LABEL_FLOOR = 120   # the breathe's dimmest alpha


def chevron(cx, mid, facing, w=NAV_W, h=NAV_H, stroke=NAV_STROKE):
  """A chevron outline centred on cx, mid, facing -1 for left or 1 for right.

  One polygon, not two strokes: overlapping shapes compound a transparent
  fill where they cross, so a dimmed chevron would read brighter at the tip.
  """
  tip_x = cx + facing * w / 2
  open_x = cx - facing * w / 2
  length = (w * w + h * h) ** 0.5
  half = stroke / 2

  # offsets from the centreline to the outer edge; they turn with facing
  mitre = facing * half * length / h
  px = facing * half * h / length
  py = -half * w / length

  screen.shape(shape.custom([
      vec2(open_x + px, mid - h + py),
      vec2(tip_x + mitre, mid),
      vec2(open_x + px, mid + h - py),
      vec2(open_x - px, mid + h + py),
      vec2(tip_x - mitre, mid),
      vec2(open_x - px, mid - h - py),
  ]))


def draw_nav(index, count, position=None, label=None):
  """The navigation row: chevrons over A and C, a progress track between.

  Each chevron fades once there is nothing further its way. `position` is an
  optional fractional index for a thumb that rides a slide. `label` names
  button B, set under its position at the row's centre.
  """
  global nav_full, nav_dim
  if nav_full is None:
    nav_full = orange_gradient(NAV_LEFT, NAV_SPAN)
    nav_dim = orange_gradient(NAV_LEFT, NAV_SPAN, KNOCKBACK)

  mid = NAV_Y + NAV_HEIGHT / 2
  reach = NAV_W / 2

  # the chevrons, dimmed at either end of the range
  screen.pen = nav_full if index > 0 else nav_dim
  chevron(NAV_A_X, mid, -1)
  screen.pen = nav_full if index < count - 1 else nav_dim
  chevron(NAV_C_X, mid, 1)

  if label is not None:
    _, bold = fonts()
    prior = screen.font
    screen.font = bold
    wide = screen.measure_text(label, NAV_LABEL_SIZE)[0]
    # the label breathes gently between full strength and its floor; the
    # gradient is cached per dimming step, too dear to build every frame
    breathe = 0.5 - 0.5 * math.cos(badge.ticks / NAV_LABEL_PULSE_MS * math.pi * 2)
    alpha = int(NAV_LABEL_FLOOR + breathe * (255 - NAV_LABEL_FLOOR)) & ~7
    pen = nav_label_pens.get(alpha)
    if pen is None:
      pen = nav_label_pens[alpha] = orange_gradient(NAV_LEFT, NAV_SPAN, alpha)
    screen.pen = pen
    screen.text(label, int((WIDTH - wide) / 2) + NAV_LABEL_NUDGE,
                NAV_LABEL_TOP - CAP_TOP * NAV_LABEL_SIZE, NAV_LABEL_SIZE)
    screen.font = prior

  if count < 2:
    return

  # the track between the chevrons, and the thumb along it
  start = NAV_A_X + reach + NAV_GAP
  track = (NAV_C_X - reach - NAV_GAP) - start
  width = max(20, track / count)
  offset = (track - width) * (index if position is None else position) / (count - 1)

  screen.pen = nav_dim
  screen.shape(shape.rounded_rectangle(start, NAV_Y, track, NAV_HEIGHT, NAV_HEIGHT / 2))
  screen.pen = nav_full
  screen.shape(shape.rounded_rectangle(start + offset, NAV_Y, width, NAV_HEIGHT,
                                       NAV_HEIGHT / 2))


class VectorArt:
  """Line art held as shapes, drawn from its own geometry at any size.

  Every contour in the file must be solid, holes let into their parent
  through a slit, since badgeware fills each shape on its own with no winding
  rule between them. svg.depths() reports whether a file qualifies, and one
  that does not is refused.
  """

  def __init__(self, path):
    doc = svg.load(path)
    if doc.depths():
      raise ValueError("%s has knocked out contours" % path)
    self.shapes = doc.shapes()
    self.view = (doc.view_x, doc.view_y, doc.view_width, doc.view_height)

  def size(self, box):
    """How wide and tall the art sits with its longest side at box."""
    scale = box / max(self.view[2], self.view[3])
    return self.view[2] * scale, self.view[3] * scale

  def draw(self, cx, cy, box):
    """Place the art centred on cx, cy with its longest side at box."""
    wide, high = self.size(box)
    place = mat3() \
        .translate(cx - wide / 2, cy - high / 2) \
        .scale(wide / self.view[2], high / self.view[3]) \
        .translate(-self.view[0], -self.view[1])
    for piece, pen in self.shapes:
      piece.transform = place
      screen.pen = pen
      screen.shape(piece)

# The mark, the faces and the backdrop load on first use (135ms and 184KB
# between them), so importing this file for the palette alone stays cheap.
wordmark = None
divider_x = 0                   # settled with the mark, which sets its place
label_font = None
title_font = None
body_font = None                # the card body sits at the weight of the lockup
washes = None


def fonts():
  """Lato regular and bold, the two weights the UI sets its type in."""
  global label_font, title_font, body_font
  if label_font is None:
    label_font = font.load("/system/assets/fonts/lato-400.af")
    title_font = font.load("/system/assets/fonts/lato-900.af")
    body_font = label_font
  return label_font, title_font


def backdrop():
  """The shared background artwork, read the first time something asks."""
  global washes
  if washes is None:
    washes = image.load("/system/assets/background.png")
  return washes


def draw_background():
  """Black, with the supplied artwork under everything below the header."""
  screen.pen = black
  screen.clear()
  # the header keeps its own black ground, so the wash starts below it
  screen.blit(backdrop(), WASH_RECT)


def draw_header():
  global wordmark, divider_x
  if wordmark is None:
    # the mark never moves, so its placement is baked into the shapes once
    mark = svg.load("/system/assets/armmark.svg")
    step = WORDMARK_HEIGHT / mark.view_height
    place = mat3() \
        .translate(WORDMARK_X, WORDMARK_Y) \
        .scale(step, step) \
        .translate(-mark.view_x, -mark.view_y)
    wordmark = []
    for piece, _ in mark.shapes():
      piece.transform = place
      wordmark.append(piece)

    aspect = mark.view_width / mark.view_height
    divider_x = WORDMARK_X + int(WORDMARK_HEIGHT * aspect) + 1 + GAP

  label, _ = fonts()

  # black band across the top
  screen.pen = black
  screen.rectangle(0, 0, WIDTH, HEADER_HEIGHT)

  # the wordmark; drawn small, so its curves need antialiasing to hold shape
  antialias = screen.antialias
  screen.antialias = image.X2
  screen.pen = white
  screen.shapes(wordmark)
  screen.antialias = antialias

  # the rule between the mark and the label
  screen.pen = divider
  screen.rectangle(divider_x, DIVIDER_Y, 1, DIVIDER_HEIGHT)

  # "Developer", sharing the mark's baseline
  brand = screen.font
  screen.font = label
  screen.pen = cyan
  screen.text("Developer", divider_x + 1 + GAP - LABEL_BEARING, LOCKUP_Y,
              LOCKUP_SIZE)
  screen.font = brand

  draw_battery()


def draw_battery():
  # charging animates the fill sweeping up instead of showing a level
  charging = badge.is_charging()
  if charging:
    level = (badge.ticks / 20) % 100
  else:
    level = badge.battery_level()

  if charging:
    screen.pen = white
  elif level < BATTERY_LOW:
    # blink between full and knocked back once there is little left
    blink = (badge.ticks // BATTERY_BLINK) % 2 == 0
    screen.pen = white if blink else white_dim
  else:
    screen.pen = white_dim

  # cell outline and terminal nub. stroke() consumes the shape it is called
  # on; a positive thickness insets it, keeping the cell exactly BATTERY_W
  screen.shape(shape.rectangle(BATTERY_X, BATTERY_Y, BATTERY_W, BATTERY_H).stroke(1))
  screen.shape(shape.rectangle(BATTERY_X + BATTERY_W, BATTERY_Y + 4, 2, 4))

  # the fill, proportional to the level
  width = ((BATTERY_W - 6) / 100) * level
  screen.shape(shape.rectangle(BATTERY_X + 3, BATTERY_Y + 3, width, BATTERY_H - 6))
