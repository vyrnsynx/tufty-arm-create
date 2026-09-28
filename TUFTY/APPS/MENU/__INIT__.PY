
badge.mode(HIRES | VSYNC)
screen.antialias = image.X2

import branding as brand

from app import Apps

# Aeonik, the Arm brand typeface
brand_font = font.load("/system/assets/fonts/AeonikFono-Regular.af")


apps = Apps("/system/apps")

active = 0

# the launcher fades up from black as it opens
FADE_MS = 250
opened_at = badge.ticks


# "on_exit" will be called if callable, else returned verbatim by `launch`
on_exit = None

while on_exit is None:
  # step through the carousel one card at a time
  if badge.pressed(BUTTON_C) or badge.pressed(BUTTON_DOWN):
    active = min(len(apps) - 1, active + 1)
  if badge.pressed(BUTTON_A) or badge.pressed(BUTTON_UP):
    active = max(0, active - 1)

  apps.activate(active)

  if badge.pressed(BUTTON_B):
    on_exit = apps.active.path
    break

  screen.font = brand_font

  brand.draw_background()
  brand.draw_header()

  # draw the app cards and how far through them we are
  apps.draw_cards()
  apps.draw_progress()

  part = (badge.ticks - opened_at) / FADE_MS
  if part < 1.0:
    screen.pen = color.rgb(0, 0, 0, int(255 * (1.0 - part)))
    screen.rectangle(screen.clip)

  badge.update()

# Hand back the default mode so apps that don't set one still get the low
# resolution screen they expect.
badge.mode(LORES | VSYNC)
