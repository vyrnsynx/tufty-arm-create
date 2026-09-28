"""
Meet Tufty, your new pet squirrel. Keep Tufty happy, well-fed, and out of
trouble!

Controls:
* A = Play with him
* B = Feed him
* C = Clean up after him
* Up = Run his day faster
* Down = Show what he needs
"""

badge.mode(LORES | VSYNC)

import clock
import tufty
import ui
from badgeware import State

# how much faster the day runs with UP held
WARP = 100

# how long each need takes to empty, in Tufty's own hours, so they keep their
# pace against his day however fast it is set to run
HAPPY_HOURS = 12
HUNGER_HOURS = 8
CLEAN_HOURS = 16

stats_shown = False


def draw(hour, minute):
  ui.background(clock.look(hour, minute))
  pet.draw()

  # the buttons, on a strip wiped clear of whatever was there last frame
  screen.pen = color.rgb(0, 0, 0)
  screen.rectangle(0, 106, 160, 14)

  if pet.alive():
    ui.draw_button(7, 106, "play", pet.current_action() == "dance")
    ui.draw_button(57, 106, "feed", pet.current_action() == "eat")
    ui.draw_button(107, 106, "clean", pet.current_action() == "clean")
  else:
    ui.draw_button(57, 106, "reset", False)

  ui.draw_glitch(min(pet.hunger(), pet.clean(), pet.happy()))
  ui.draw_scanlines(ui.SCENE)

  # the readouts go on after the filter, so the scanlines do not cross them
  ui.draw_clock(hour, minute)
  if stats_shown:
    ui.draw_stats((("fed", pet.hunger()),
                   ("clean", pet.clean()),
                   ("happy", pet.happy())))

  ui.draw_header()


def titles():
  """Hold on the title screen until B lets him out."""
  while True:
    screen.pen = color.rgb(0, 0, 0)
    screen.clear()
    ui.draw_intro(tufty.frame("dance"))
    ui.draw_scanlines()
    ui.draw_header()
    badge.update()

    if badge.pressed(BUTTON_B):
      return


def play():
  """Look after him until he goes."""
  global stats_shown

  while pet.alive():
    # move his day on, 100x faster while UP is held
    speed = WARP if badge.held(BUTTON_UP) else 1
    passed = clock.advance(badge.ticks_delta / 1000 * speed)

    # DOWN shows his stats and hides them again
    if badge.pressed(BUTTON_DOWN):
      stats_shown = not stats_shown

    hour, minute = clock.now()

    # he turns in for the night by himself, and nothing rouses him early
    if clock.phase(hour) == "night":
      pet.set_mood("sleep")
    else:
      # every need falls away as his day goes by
      pet.happy(-(passed / (HAPPY_HOURS * 60)) * 100)
      pet.hunger(-(passed / (HUNGER_HOURS * 60)) * 100)
      pet.clean(-(passed / (CLEAN_HOURS * 60)) * 100)

      # play with him, feed him, clean him
      if badge.pressed(BUTTON_A):
        pet.happy(30)
        pet.do_action("dance")

      if badge.pressed(BUTTON_B):
        pet.hunger(30)
        pet.do_action("eat")

      if badge.pressed(BUTTON_C):
        pet.clean(30)
        pet.do_action("clean")

      # left to himself he crosses to a new spot and finds something to do
      if pet.time_since_last_position_change() > 20:
        pet.set_mood("run")
        pet.move_to_random()

      if pet.time_since_last_mood_change() > 8:
        pet.random_idle()

    pet.update()
    draw(hour, minute)
    badge.update()


def game_over():
  """He is gone. Hold the scene until B asks for another."""
  # nothing of him is kept, so the badge opens on the titles next time
  State.delete("tufty")

  pet.set_mood("dead")
  pet.set_speed(1)
  pet.move_to_center()

  while True:
    clock.advance(badge.ticks_delta / 1000)
    pet.update()
    draw(*clock.now())
    badge.update()

    if badge.pressed(BUTTON_B):
      return


def save_state():
  saved = pet.save()
  saved["clock"] = clock.reading()
  State.save("tufty", saved)


def get_state():
  """His stats and clock as they were saved, or None if no Tufty is waiting."""
  state = {}
  State.load("tufty", state)
  return state or None


def on_exit():
  # nobody is out while the titles are up, so there is nothing to keep
  if pet is None:
    return

  if pet.alive():
    save_state()
  else:
    State.delete("tufty")


saved = get_state()
pet = None

while True:
  # a Tufty already in hand skips the titles
  if not saved:
    titles()

  # 95 is the ground he stands on
  pet = tufty.Tufty(95)
  if saved:
    # and picks his day up where he left it
    pet.load(saved)
    clock.resume(saved["clock"])
    saved = None

  save_state()
  play()
  game_over()
  pet = None
