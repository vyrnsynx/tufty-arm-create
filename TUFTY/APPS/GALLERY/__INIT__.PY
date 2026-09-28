"""
Explore the Arm Developer Gallery. Find the hidden surprise to unlock your next Arm Create experience.

Controls:
* A and C = Move along the carousel, or between images with one open
* B = Open the card in hand, or close it again
"""

import os

badge.mode(HIRES | VSYNC)

import branding as brand

screen.font = brand.fonts()[1]
screen.antialias = image.X2

WIDTH, HEIGHT = screen.width, screen.height
CX, CY = WIDTH / 2, HEIGHT / 2
FULL = rect(0, 0, WIDTH, HEIGHT)

# The artwork comes in an English and a Simplified Chinese set, chosen by
# LANGUAGE in secrets.py. A badge with no secrets.py, no LANGUAGE in it, or a
# language there is no set for reads English.
try:
  import secrets
  LANGUAGE = getattr(secrets, "LANGUAGE", "en")
except ImportError:
  LANGUAGE = "en"
if not is_dir("images/" + LANGUAGE):
  LANGUAGE = "en"
IMAGE_DIR = "images/" + LANGUAGE

# the shared background artwork
BACKDROP = brand.backdrop()

CARD_W, CARD_H = 132, 99
CARD_PITCH = 152
CARD_LIFT = 1.15            # how much larger the card in hand is drawn
CARD_DIM = 90               # how far back the cards either side are held
DEPTH_FALL = 0.72           # how much smaller a card gets per place out
DEPTH_SINK = 7              # pixels a card sinks per place out, arcing the row

# tween durations; BACK_OUT moves overshoot a little and settle
SCROLL_S = 0.36
ZOOM_S = 0.36
SLIDE_S = 0.30

# the full screen slide: the leaver settles back and dims as the next comes over
SLIDE_SETTLE = 0.08
SLIDE_DIM = 0.6

# Left alone, the gallery strolls by itself: a card every few seconds, every
# fourth one opened full screen for a moment. Any press takes over again.
ATTRACT_AFTER = 8000        # ms without a press before it starts
ATTRACT_STEP = 4000         # ms between its own moves
ATTRACT_OPENS = 4           # it opens every fourth card it lands on
ATTRACT_HOLD = 3500         # ms an opened card stays up

TITLE_Y = 186
TITLE_SIZE = 27

DOT_Y = 24                  # one dot a card, over the carousel
DOT_R = 3.0
DOT_PITCH = 13
DOT_DIM = 70                # how far back the cards not in hand are marked

SHADOW = color.rgb(0, 0, 0, 110)


def sequence(file):
  """The img-N number the artwork is named with, so 10 follows 9."""
  try:
    return int(file.split("img-")[1].split("_")[0])
  except (IndexError, ValueError):
    return 0


# list the pngs, skipping dotfiles and macOS sidecar files
image_files = [
    file for file in os.listdir(IMAGE_DIR)
    if not file.startswith(("__", ".")) and file.endswith(".png")
]
image_files.sort(key=sequence)

if not image_files:
  fatal_error("No images found!", "Enter disk mode and copy your PNGs to /apps/gallery/images")


def center_text(text, y, size=TITLE_SIZE):
  w, _ = screen.measure_text(text, size)
  screen.text(text, CX - w / 2, y, size)


files = []
for file in image_files:
  # the filename ends with the subject, after the img-N part
  files.append({
      "title": file.rsplit(".", 1)[0].rsplit("_", 1)[-1].replace("-", " "),
      "image": image.load("%s/%s" % (IMAGE_DIR, file)),
  })


index = 0                   # the card in hand, counted on past the ends
scrolling = tween(0.0, 0.0, SCROLL_S, tween.BACK_OUT)
scrolled_at = badge.ticks

landing_at = None           # when the move under way settles

attract_due = badge.ticks + ATTRACT_AFTER
strolled = 0                # cards attract mode has taken since the last press


def rouse():
  """A real press: put attract mode back to sleep."""
  global attract_due, strolled
  attract_due = badge.ticks + ATTRACT_AFTER
  strolled = 0


def wrapped(n):
  """Any card number brought into the range the gallery holds."""
  return n % len(files)


def scroll():
  """Where the carousel has slid to, which lags the card in hand."""
  return scrolling.at((badge.ticks - scrolled_at) / 1000)


def move(way):
  """Take the next card along, from wherever the carousel has got to."""
  global index, scrolling, scrolled_at, landing_at
  index += way
  scrolling = tween(scroll(), float(index), SCROLL_S, tween.BACK_OUT)
  scrolled_at = badge.ticks
  landing_at = badge.ticks + int(SCROLL_S * 1000)


def card_rect(offset):
  """Where a card sits, `offset` places from the middle of the carousel.

  Cards shrink and sink as they move out from the middle, so the row reads
  as an arc with the card in hand lifted off it.
  """
  scale = CARD_LIFT * DEPTH_FALL ** abs(offset)
  w, h = CARD_W * scale, CARD_H * scale
  return rect(CX + offset * CARD_PITCH - w / 2,
              CY + DEPTH_SINK * abs(offset) - h / 2, w, h)


def draw_card(n, where, alpha=255):
  # a drop shadow thrown further the higher the card is lifted, then the
  # artwork scaled into its rect. Filtering costs the same as nearest and
  # keeps the artwork's fine detail from sparkling as cards change size.
  art = files[wrapped(n)]["image"]
  lift = where.w / CARD_W
  screen.pen = SHADOW
  screen.rectangle(where.x + 3 * lift, where.y + 4 * lift, where.w, where.h)
  screen.alpha = alpha
  screen.blit(art, rect(0, 0, art.width, art.height), where, image.BILINEAR)
  screen.alpha = 255


def draw_carousel(fade=1.0):
  """The cards either side of where the carousel has slid to.

  They are drawn from the outside in, so the card in hand sits over its
  neighbours as it grows past them.
  """
  screen.blit(BACKDROP, FULL)

  at = scroll()
  middle = round(at)
  for step in (-2, 2, -1, 1, 0):
    offset = middle + step - at
    near = max(0.0, 1.0 - abs(offset))
    draw_card(middle + step, card_rect(offset),
              int((CARD_DIM + (255 - CARD_DIM) * near) * fade))


def draw_chrome(fade=1.0):
  """The dots and the title, which go with the carousel as it opens a card."""
  ink = int(255 * fade)

  # one dim dot per card, centred as a row over the carousel
  left = CX - (len(files) - 1) * DOT_PITCH / 2
  screen.pen = color.rgb(255, 255, 255, int(DOT_DIM * fade))
  for n in range(len(files)):
    screen.shape(shape.circle(left + n * DOT_PITCH, DOT_Y, DOT_R))

  # the bright dot rides the carousel, sliding along with the artwork
  screen.pen = color.rgb(255, 255, 255, ink)
  screen.shape(shape.circle(left + (scroll() % len(files)) * DOT_PITCH,
                            DOT_Y, DOT_R + 1))

  # the title on a dark pill; half again the type's size clears descenders
  title = files[wrapped(index)]["title"]
  w, _ = screen.measure_text(title, TITLE_SIZE)
  screen.pen = color.rgb(0, 0, 0, int(120 * fade))
  screen.shape(shape.rounded_rectangle(CX - w / 2 - 12, TITLE_Y,
                                       w + 24, TITLE_SIZE * 1.5, 9))
  screen.pen = color.rgb(255, 255, 255, ink)
  center_text(title, TITLE_Y)


def browse():
  """The carousel, until B opens the card in hand.

  Gives back True when attract mode wants the card in hand opened.
  """
  global landing_at, attract_due, strolled
  while True:
    draw_carousel()
    draw_chrome()
    badge.update()

    # the pulse fires as the move under way settles
    if landing_at is not None and badge.ticks >= landing_at:
      landing_at = None

    if badge.pressed(BUTTON_A):
      rouse()
      move(-1)
    if badge.pressed(BUTTON_C):
      rouse()
      move(1)
    if badge.pressed(BUTTON_B):
      rouse()
      return False

    # left alone, stroll on to the next card
    if badge.ticks >= attract_due:
      move(1)
      strolled += 1
      attract_due = badge.ticks + ATTRACT_STEP
      if strolled % ATTRACT_OPENS == 0:
        return True


def zoom(opening):
  """The card growing to fill the screen, or dropping back into the carousel."""
  card = card_rect(index - scroll())
  growing = (tween(card, FULL, ZOOM_S, tween.BACK_OUT) if opening
             else tween(FULL, card, ZOOM_S, tween.BACK_OUT))

  started = badge.ticks
  while True:
    gone = (badge.ticks - started) / 1000
    part = min(1.0, gone / ZOOM_S)

    fade = 1.0 - part if opening else part
    draw_carousel(fade)
    draw_chrome(fade)
    draw_card(index, growing.at(gone))
    badge.update()

    if part >= 1.0:
      return


def draw_full(n, shift):
  art = files[wrapped(n)]["image"]
  screen.blit(art, rect(0, 0, art.width, art.height),
              rect(shift, 0, WIDTH, HEIGHT))


def slide(way):
  """The next card along, sliding in over the one leaving."""
  global index

  going, coming = index, index + way
  art = files[wrapped(going)]["image"]
  sliding = tween(0.0, float(WIDTH), SLIDE_S, tween.CUBIC_OUT)

  started = badge.ticks
  while True:
    gone = (badge.ticks - started) / 1000
    shift = sliding.at(gone)
    part = min(1.0, gone / SLIDE_S)

    screen.pen = color.rgb(0, 0, 0)
    screen.clear()

    # the leaver settles back and dims in place
    back = 1.0 - SLIDE_SETTLE * part
    w, h = WIDTH * back, HEIGHT * back
    screen.alpha = int(255 * (1.0 - SLIDE_DIM * part))
    screen.blit(art, rect(0, 0, art.width, art.height),
                rect((WIDTH - w) / 2, (HEIGHT - h) / 2, w, h), image.BILINEAR)
    screen.alpha = 255

    # while the next slides in over it
    draw_full(coming, way * (WIDTH - shift))
    badge.update()

    if gone >= SLIDE_S:
      break

  index = coming
  # park the carousel on the new index, so it has nothing to catch up on
  # when it comes back into view
  global scrolling, scrolled_at
  scrolling = tween(float(index), float(index), SCROLL_S, tween.BACK_OUT)
  scrolled_at = badge.ticks


def view():
  """One card, full screen, until B closes it."""
  while True:
    draw_full(index, 0)
    badge.update()

    if badge.pressed(BUTTON_A):
      rouse()
      slide(-1)
    if badge.pressed(BUTTON_C):
      rouse()
      slide(1)
    if badge.pressed(BUTTON_B):
      rouse()
      return


def hold():
  """An attract-opened card, up until its time is spent.

  A press hands the card over as though it had been opened by hand, so the
  first touch of a strolling gallery only wakes it.
  """
  until = badge.ticks + ATTRACT_HOLD
  while badge.ticks < until:
    draw_full(index, 0)
    badge.update()

    if (badge.pressed(BUTTON_A) or badge.pressed(BUTTON_B)
        or badge.pressed(BUTTON_C)):
      rouse()
      return False
  return True


while True:
  opened = browse()
  zoom(True)
  if opened and hold():
    # attract mode closes what it opened and strolls on
    zoom(False)
    attract_due = badge.ticks + ATTRACT_STEP
    continue
  view()
  zoom(False)
