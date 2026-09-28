import os
import math

import branding as brand

body_font, title_font = brand.fonts()

ICON_BOX = 60       # the largest an icon may be on either axis
TAU = math.pi * 2

# Folder names become card titles a word at a time, which reads wrong for a
# name that is said as letters.
ACRONYMS = ("iss", "ai", "ml", "os", "ui", "gps", "led", "usb", "nfc")


# Each app carries its own icon.svg, so the launcher only ever parses artwork
# for an app that is installed, which costs a few hundred milliseconds each.


def icon_for(path):
  """The app's own icon.svg, or None for an app without one to draw."""
  try:
    return brand.VectorArt("%s/icon.svg" % path)
  except (OSError, ValueError):
    return None

# Apps carry no description of their own unless the module opens with a
# docstring, so anything without one falls back to this.
FALLBACK_DESCRIPTION = "No description provided by this app."

# A card is its content laid out on the background, no panel or border behind
# it. CARD_W and CARD_H are the measure the layout is built from.
CARD_W, CARD_H = 294, 152
CARD_GAP = 16
CARD_PITCH = CARD_W + CARD_GAP

# Proportions follow developer.arm.com's category card: type and icon scale
# with the card's height, the horizontal insets with its width.
PADDING_X = 6
ICON_GAP = 22
ICON_X = 11         # the icon sits nearer the edge than the text does

TITLE_SIZE = 27
TITLE_PITCH = 34
DESC_SIZE = 18
DESC_PITCH = 20

# where the cap line of each block sits below the top of the card
TITLE_CAP_Y = 16
BODY_CAP_Y = 50

# the icon's ink starts on the title's cap line
ICON_Y = TITLE_CAP_Y

# icons breathe and drift on two periods that do not divide, so the motion
# never visibly loops; a phase offset per card stops neighbours moving as one
ICON_BREATHE = 0.05         # how far the scale swings either side
ICON_BOB = 3.0              # pixels of drift, either side
ICON_BREATHE_MS = 1800
ICON_BOB_MS = 2400
ICON_PHASE = 700            # ms of offset per card

# the card is centred between the header and the top of the navigation row
CARD_TOP = int(brand.HEADER_HEIGHT + (brand.NAV_TOP - brand.HEADER_HEIGHT - CARD_H) / 2)

# the band the carousel is clipped to, keeping cards clear of the header
BAND_TOP = CARD_TOP - 4
BAND_HEIGHT = CARD_H + 8

# how quickly the carousel catches up to the selected card, in milliseconds
SCROLL_SETTLE = 90
# the most of the remaining distance one frame may take, so a long frame cannot
# swallow the slide in a single step
SCROLL_MAX_STEP = 0.4

body_text = color.rgb(163, 168, 174)


def read_description(path):
  """The opening paragraph of the app's module docstring, if it has one."""
  try:
    with open(f"{path}/__init__.py", "r") as handle:
      head = handle.read(600)
  except OSError:
    return FALLBACK_DESCRIPTION

  head = head.lstrip()
  for quote in ('"""', "'''"):
    if head.startswith(quote):
      end = head.find(quote, 3)
      if end > 0:
        # only the first paragraph; the rest is detail for source readers
        summary = head[3:end].strip().split("\n\n")[0]
        return " ".join(summary.split())
  return FALLBACK_DESCRIPTION


def wrap(text, size, width):
  """Break text into lines that fit within width."""
  lines = []
  line = ""
  for word in text.split():
    candidate = word if not line else line + " " + word
    if not line or screen.measure_text(candidate, size)[0] <= width:
      line = candidate
    else:
      lines.append(line)
      line = word
  if line:
    lines.append(line)
  return lines


class App:
  def __init__(self, collection, name, path):
    self.index = len(collection)
    self._icon = None
    self._read = False
    self.name = name
    self.path = path
    self.description = read_description(path)
    self.lines = None       # wrapped lazily, once the font is set

    collection.append(self)

  @property
  def icon(self):
    """The icon, parsed the first time the card is drawn.

    An app with no icon.svg, or one whose contours are knocked out, has none.
    """
    if self._icon is None and not self._read:
      self._read = True
      self._icon = icon_for(self.path)
    return self._icon

  def layout(self, width):
    # wrap() measures with whatever font is set, so each block is wrapped
    # in the face it will be drawn in
    screen.font = title_font
    title = wrap(self.name, TITLE_SIZE, width)
    screen.font = body_font
    body = wrap(self.description, DESC_SIZE, width)

    # cap the description at what fits under the title; the last line only
    # needs its own depth, not a whole pitch
    first = BODY_CAP_Y + (len(title) - 1) * TITLE_PITCH
    room = CARD_H - first - DESC_SIZE
    allowed = 1 + max(0, int(room // DESC_PITCH))
    if len(body) > allowed:
      body = body[:allowed]
      body[-1] = body[-1] + "..."

    self.lines = (title, body)
    return self.lines

  def draw(self, scroll):
    cx = brand.WIDTH / 2 + self.index * CARD_PITCH - scroll
    if cx + CARD_W / 2 < 0 or cx - CARD_W / 2 > brand.WIDTH:
      return

    text_x = cx - CARD_W / 2 + ICON_X + ICON_BOX + ICON_GAP
    text_width = (cx + CARD_W / 2 - PADDING_X) - text_x

    title, body = self.lines or self.layout(text_width)

    # content hangs from the card's top; a short description leaves slack at
    # the bottom
    icon = self.icon
    if icon:
      icon_x = cx - CARD_W / 2 + ICON_X
      beat = badge.ticks + self.index * ICON_PHASE
      breath = 1.0 + math.sin(beat / ICON_BREATHE_MS * TAU) * ICON_BREATHE
      drift = math.sin(beat / ICON_BOB_MS * TAU) * ICON_BOB
      # the breathing swells about the resting footprint's centre, so the
      # art stays put while it moves
      wide, high = icon.size(ICON_BOX)
      icon.draw(icon_x + wide / 2, CARD_TOP + ICON_Y + drift + high / 2,
                ICON_BOX * breath)

    # text is positioned by the top of its em box, so each cap line is
    # reached by backing off the font's cap inset
    screen.font = title_font
    screen.pen = brand.white
    cap = TITLE_CAP_Y
    for line in title:
      screen.text(line, text_x, CARD_TOP + cap - TITLE_SIZE * brand.CAP_TOP, TITLE_SIZE)
      cap += TITLE_PITCH

    # a one line title puts the body on its measured line; a wrapped one
    # pushes it down by the extra lines
    cap = BODY_CAP_Y + (len(title) - 1) * TITLE_PITCH
    screen.font = body_font
    screen.pen = body_text
    for line in body:
      screen.text(line, text_x, CARD_TOP + cap - DESC_SIZE * brand.CAP_TOP, DESC_SIZE)
      cap += DESC_PITCH


class Apps:
  def __init__(self, root):
    self.apps = []
    self.active_index = 0
    self.scroll = 0.0

    def capitalize(word):
      if word in ACRONYMS:
        return word.upper()
      if len(word) <= 1:
        return word
      return word[0].upper() + word[1:]

    for path in sorted(os.listdir(root)):
      name = " ".join([capitalize(word) for word in path.split("_")])

      if is_dir(f"{root}/{path}"):
        if path != "menu" and (file_exists(f"{root}/{path}/__init__.py") or file_exists(f"{root}/{path}/__init__.mpy")):
          App(self.apps, name, f"{root}/{path}")

  @property
  def active(self):
    return self.apps[self.active_index]

  def activate(self, index):
    self.active_index = index
    # read the card's icon now, before the slide starts, since parsing one
    # costs several frames and doing it mid slide stalls the animation
    self.apps[index].icon

  def draw_cards(self):
    # ease the carousel towards the selected card
    target = self.active_index * CARD_PITCH
    step = min(SCROLL_MAX_STEP, badge.ticks_delta / SCROLL_SETTLE)
    self.scroll += (target - self.scroll) * step
    if abs(target - self.scroll) < 0.5:
      self.scroll = target

    previous = screen.clip
    screen.clip = rect(0, BAND_TOP, brand.WIDTH, BAND_HEIGHT)
    for app in self.apps:
      app.draw(self.scroll)
    screen.clip = previous

  def draw_progress(self):
    """How far through the carousel we are, and the buttons that move it."""
    # the thumb rides the scroll, so it slides along with the cards
    brand.draw_nav(self.active_index, len(self.apps),
                   position=self.scroll / CARD_PITCH, label="RUN APP")

  def __len__(self):
    return len(self.apps)

  def __getitem__(self, i):
    return self.apps[i]
