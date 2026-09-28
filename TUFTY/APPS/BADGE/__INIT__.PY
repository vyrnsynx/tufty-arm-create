"""
Personalize your badge, add your social handles, and make it easy for others to
connect with a quick scan.

Your details come from /profile.py. Every field there is optional, so the cards
follow whatever you have filled in.

Controls:
* A and C = Move between the name card and each social card
* B, up or down = Back to the launcher
"""

import math

import profile
import qrcode

badge.mode(HIRES | VSYNC)
screen.antialias = image.X2

import branding as brand

WIDTH, HEIGHT = brand.WIDTH, brand.HEIGHT
TAU = math.pi * 2

white = brand.white
muted = brand.muted
ACCENT = brand.orange_accent    # the rule, the ring and the job title
MENU = "/system/apps/menu"
LEAVE = (BUTTON_B, BUTTON_UP, BUTTON_DOWN)

CAP_TOP = brand.CAP_TOP
CAP_HEIGHT = brand.CAP_HEIGHT

# Every line on the badge is set in the same weight; the hierarchy comes from
# size and colour.
_, bold_font = brand.fonts()

MARGIN = 24

# Content sits between the header and the highest point of the chevrons.
CONTENT_TOP = brand.HEADER_HEIGHT + 8
CONTENT_BOTTOM = int(brand.NAV_TOP) - 8
CONTENT_MID = (CONTENT_TOP + CONTENT_BOTTOM) / 2


def bluesky_handle(handle):
  """A Bluesky handle is a domain, so a bare name means the default one."""
  return handle if "." in handle else handle + ".bsky.social"


def mastodon_url(handle):
  """A Mastodon handle carries its instance: user@instance."""
  user, _, host = handle.partition("@")
  return "https://%s/@%s" % (host, user) if host else "https://mastodon.social/@" + user


# field on profile, what to call it, its mark, and the link the code opens
NETWORKS = (
    ("BLUESKY", "Bluesky", "bluesky",
     lambda h: "https://bsky.app/profile/" + bluesky_handle(h)),
    ("MASTODON", "Mastodon", "mastodon", mastodon_url),
    ("LINKEDIN", "LinkedIn", "linkedin", lambda h: "https://lnkd.in/in/" + h),
    ("GITHUB", "GitHub", "github", lambda h: "https://github.com/" + h),
    ("TWITTER", "X", "twitter", lambda h: "https://x.com/" + h),
)

# --- name card --------------------------------------------------------------
# The photo on the left, the fitted text column on the right.
PHOTO_BOX = 128             # how large the photo is drawn
PHOTO_CX = 78               # its centre

TEXT_X = 166                # the text column, to the right of the photo
NAME_SIZE, NAME_MIN = 26, 15
DETAIL_SIZE, DETAIL_MIN = 20, 14
LINE_PITCH = 0.94           # of the text size
NAME_GAP = 20               # between the name and the details


def line_pitch(size):
  # LINE_PITCH, a pixel tighter, as the fraction text() takes
  return LINE_PITCH - 1 / size

# text() clips to the rect it is given, and the height measure_text() returns
# reaches only the baseline of the last row: BASELINE is 0.975 of the size,
# while the tail on a p or a g inks to 1.20 of it. Measured on device, a name
# like "Davenport" loses 3 or 4 pixels of the descender. The drawn rect is
# deepened by this fraction of the text size to leave the tail room. Layout
# still measures with the height text() reports, so the blocks sit unmoved.
DESCENDER = 0.25

REGISTER = "Visit the Digital Badge Station to personalize your badge."


def load_photo():
  """The photo's square middle at PHOTO_BOX, or the placeholder.

  Scaled once here, filtered, so the per-frame blit is one pixel to one pixel.
  """
  try:
    photo = image.load("/system/profile.png")
  except OSError:
    photo = image.load("/system/apps/badge/no-profile.png")

  side = min(photo.width, photo.height)
  middle = rect((photo.width - side) // 2, (photo.height - side) // 2, side, side)
  plate = image(PHOTO_BOX, PHOTO_BOX)
  plate.blit(photo, middle, rect(0, 0, PHOTO_BOX, PHOTO_BOX), image.BILINEAR)
  return plate


def fit_block(text, size, smallest, width, max_rows):
  """The largest size at which text wraps into max_rows of width, and its height.

  Wraps first and only shrinks when the wrap will not fit; at the floor size
  it takes as many rows as it needs. Rows are counted from the height
  measure_text() returns: each row takes the leading, the last the full size.
  """
  screen.font = bold_font
  loose = rect(0, 0, width, HEIGHT * 4)      # tall enough never to cut a row
  while True:
    _, high = screen.measure_text(text, loose, size, line_height=line_pitch(size))
    rows = round((high - size) / (size * line_pitch(size))) + 1
    if rows <= max_rows or size <= smallest:
      return size, high
    size -= 1


class NameCard:
  """Photo, name, job title and company.

  Lines and sizes are fitted once at startup: fitting costs a measure per
  size stepped through, too much to repeat every frame.
  """

  def __init__(self):
    self.photo = load_photo()
    self.width = WIDTH - MARGIN - TEXT_X
    band = CONTENT_BOTTOM - CONTENT_TOP

    name = " ".join(p for p in (profile.FIRST_NAME, profile.LAST_NAME) if p)
    drop = 0
    while True:
      self.blocks = []
      if name:
        size, high = fit_block(name, NAME_SIZE - drop, NAME_MIN, self.width, 3)
        self.blocks.append((size, white, name, high, 0))
      for text, pen, gap in ((profile.JOB_TITLE, None, NAME_GAP),
                             (profile.COMPANY, muted, 0)):
        if not text:
          continue
        size, high = fit_block(text, DETAIL_SIZE - drop, DETAIL_MIN, self.width, 2)
        self.blocks.append((size, pen, text, high, gap))
      # if the fitted blocks together outgrow the band, step every size
      # down one and fit again
      if self.height() <= band or drop >= NAME_SIZE - NAME_MIN:
        break
      drop += 1

    # an empty profile: point at the registration table
    if not self.blocks:
      size, high = fit_block(REGISTER, DETAIL_SIZE, DETAIL_MIN, self.width, 5)
      self.blocks.append((size, muted, REGISTER, high, 0))

    self.top = CONTENT_TOP + (band - self.height()) // 2

  def height(self):
    return sum(high + gap for _, _, _, high, gap in self.blocks)

  def draw(self, dx=0):
    # the photo, centred in the band on the left
    cx = int(PHOTO_CX + dx)
    cy = int(CONTENT_MID)
    screen.blit(self.photo, cx - PHOTO_BOX // 2, cy - PHOTO_BOX // 2)

    # the text blocks, top to bottom
    screen.font = bold_font
    y = self.top
    for size, pen, text, high, gap in self.blocks:
      y += gap
      screen.pen = ACCENT if pen is None else pen
      screen.text(text, rect(TEXT_X + dx, y, self.width,
                             high + size * DESCENDER), size,
                  line_height=line_pitch(size))
      y += high


# --- social cards -------------------------------------------------------------
# The network's mark on the left, the code on the right, a captioned arrow
# between them.
ICON_BOX = 98               # the mark, filling the left half of the card
MARK_GAP = 16               # between the mark and the code beside it
ICON_BREATHE = 0.06         # how far the scale swings either side
ICON_BOB = 5.0              # pixels of drift, vertically
BREATHE_MS = 1800
BOB_MS = 2400

CAPTION = "Follow me"
CAPTION_SIZE = 20
CAPTION_GAP = 10
CAPTION_LIFT = 17           # above the code's bottom edge

# the caption nudges towards the code twice per cycle, then rests. The arrow
# is drawn as a shape; the face has no glyph for one.
CAPTION_SWAY = 6.0
CAPTION_BOUNCE_MS = 300
CAPTION_BOUNCES = 2
CAPTION_CYCLE_MS = 1500
ARROW_W, ARROW_H = 8, 5
ARROW_STROKE = 2
ARROW_GAP = 10
ARROW_DROP = 2              # the chevron sits below the type's middle

# The code's size and position are fixed whatever QR version a URL needs; the
# module pitch takes up the difference, rounded per module so the block lands
# exactly on size. The border left over is the quiet zone, never under the
# four modules a scanner needs.
QR_PLATE = 144
QR_BLOCK = 120
QR_NUDGE = 10               # further right than the margin would put it

# a floor: qrcode raises the correction level itself when the URL leaves room
QR_ECC = qrcode.ECC_LOW

screen.font = bold_font
caption_width = screen.measure_text(CAPTION, CAPTION_SIZE)[0]


class SocialCard:
  """One network: its mark, the handle, and a code that opens the profile."""

  def __init__(self, mark, handle, url):
    self.art = brand.VectorArt("social/%s.svg" % mark)
    self.url = url(handle)
    self.code = self._build_code()      # up front: building it mid slide stutters

  def _build_code(self):
    """Render the QR code once into a transparent plate, gradient filled."""
    code = qrcode.QRCode(QR_ECC)
    code.set_text(self.url)
    modules = code.get_size()[0]
    if not modules:
      raise ValueError("%d characters will not fit a code" % len(self.url))

    step = QR_BLOCK / modules
    edge = (QR_PLATE - QR_BLOCK) // 2
    plate = image(QR_PLATE, QR_PLATE)
    plate.pen = color.rgb(0, 0, 0, 0)
    plate.clear()
    plate.pen = brand.orange_gradient(0, QR_PLATE)
    # each module's edges round to whole pixels, so the block lands exactly
    # on QR_BLOCK
    for y in range(modules):
      top = edge + int(round(y * step))
      depth = edge + int(round((y + 1) * step)) - top
      for x in range(modules):
        if code.get_module(x, y):
          left = edge + int(round(x * step))
          plate.rectangle(left, top,
                          edge + int(round((x + 1) * step)) - left, depth)
    return plate

  def draw(self, dx=0):
    # the code, centred in the band on the right
    side = self.code.width
    code_x = WIDTH - MARGIN - side + QR_NUDGE
    screen.blit(self.code,
                rect(int(code_x + dx), int(CONTENT_MID - side / 2), side, side))

    # the caption's foot aligns with the code's bottom edge; the mark takes
    # the middle of what is left above it
    caption_y = CONTENT_MID + side / 2 - CAPTION_SIZE * CAP_HEIGHT - CAPTION_LIFT
    icon_middle = (CONTENT_TOP + caption_y - CAPTION_GAP) / 2

    # the mark breathes and drifts on two periods that do not divide, so the
    # motion never visibly loops
    t = badge.ticks
    scale = 1.0 + math.sin(t / BREATHE_MS * TAU) * ICON_BREATHE
    drift = math.sin(t / BOB_MS * TAU) * ICON_BOB
    centre_x = MARGIN + (code_x - MARK_GAP - MARGIN) / 2
    self.art.draw(centre_x + dx, icon_middle + drift, ICON_BOX * scale)

    # caption and arrow are placed and swayed as one block
    block = caption_width + ARROW_GAP + ARROW_W
    beat = t % CAPTION_CYCLE_MS
    sway = 0.0
    if beat < CAPTION_BOUNCE_MS * CAPTION_BOUNCES:
      # abs() so every push goes the same way
      sway = abs(math.sin(beat / CAPTION_BOUNCE_MS * math.pi)) * CAPTION_SWAY
    left = centre_x + dx + sway - block / 2

    screen.font = bold_font
    screen.pen = white
    screen.text(CAPTION, int(left), caption_y - CAPTION_SIZE * CAP_TOP, CAPTION_SIZE)

    # arrow pointing at the code, centred on the caption's middle
    brand.chevron(left + block - ARROW_W / 2,
                  caption_y + CAPTION_SIZE * CAP_HEIGHT / 2 + ARROW_DROP, 1,
                  ARROW_W, ARROW_H, ARROW_STROKE)


# --- the cards, and moving between them ---------------------------------------
CARDS = [NameCard()]
for field, label, mark, url in NETWORKS:
  handle = getattr(profile, field, "")
  if not handle:
    continue
  try:
    CARDS.append(SocialCard(mark, handle, url))
  except ValueError as reason:
    # a URL too long for the largest code qrcode builds: skip the card so
    # the badge still starts
    print("%s card skipped: %s" % (label, reason))


# the card shown last time, clamped in case there are fewer cards now
state = {"card": 0}
State.load("badge", state)

card = min(len(CARDS) - 1, max(0, state["card"]))
leaving = None          # the card sliding out, while the next slides in
came_from = 1           # 1 if the new card entered from the right
slide_start = 0

SLIDE_MS = 220          # how long a card takes to slide into place


def go_to(next_card):
  """Start a card sliding in from the side it came from."""
  global card, leaving, came_from, slide_start
  if next_card == card:
    return
  leaving = CARDS[card]
  came_from = 1 if next_card > card else -1
  slide_start = badge.ticks
  card = next_card
  state["card"] = card
  State.save("badge", state)


# "on_exit" is returned by launch(), which is how main.py hears where to go
on_exit = None

while on_exit is None:
  if badge.pressed(BUTTON_A):
    go_to(max(0, card - 1))
  if badge.pressed(BUTTON_C):
    go_to(min(len(CARDS) - 1, card + 1))
  if any(badge.pressed(button) for button in LEAVE):
    on_exit = MENU
    break

  brand.draw_background()

  # while a slide is running, draw the old card leaving and offset the new
  dx = 0
  if leaving is not None:
    step = (badge.ticks - slide_start) / SLIDE_MS
    if step >= 1.0:
      leaving = None
    else:
      eased = 1.0 - (1.0 - step) ** 3      # quick away, gentle arrival
      dx = came_from * WIDTH * (1.0 - eased)
      leaving.draw(dx - came_from * WIDTH)

  CARDS[card].draw(dx)
  brand.draw_nav(card, len(CARDS), label="SHOW APPS")
  brand.draw_header()
  badge.update()
