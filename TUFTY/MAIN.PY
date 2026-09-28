import sys

MENU = "/system/apps/menu"
BADGE = "/system/apps/badge"

# the import paths every app relies on, set once. launch() adds the app's own
# folder in front and removes it again afterwards.
sys.path.insert(0, "/")             # profile.py and secrets.py, the owner's own
sys.path.insert(0, "/system")       # shared modules, svg among them

# compiling svg costs about 250ms. Imported here it stays in sys.modules:
# launch() only unloads the modules an app imported itself.
import svg                          # noqa: F401

display.backlight(0.75)

# Eat the wakeup button press to prevent it leaking into the app
badge.poll()

# The badge comes up on its own. It hands back the launcher's path when someone
# asks for it.
app_to_launch = launch(BADGE)

while app_to_launch is not None:

  # Don't pass one app's button presses into the next
  while badge.pressed() or badge.held() or badge.released():
    badge.poll()

  app_to_launch = launch(app_to_launch)

# Catch any exit and reset back to the badge
reset()
