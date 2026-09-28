import math
import random

# every animation, and how many frames its sheet holds
FRAMES = {
    "dance": 6,
    "clean": 11,
    "eat": 12,
    "run": 5,
    "sleep": 12,
    "dig": 5,
    "idle": 14,
    "lick": 4,
    "tail": 4,
    "dead": 14,
    "notify": 4,
}

sheets = {name: image.load("assets/squirrel-sprites/%s.png" % name).spritesheet(count, 1)
          for name, count in FRAMES.items()}


def frame(mood):
  """One frame of a mood, for the screens that draw him outside the game."""
  return sheets[mood].sprite(round(badge.ticks / 100) % FRAMES[mood], 0)


# our little friend: where he is, how he feels, and which frame of which
# animation that adds up to
class Tufty:
  def __init__(self, y):
    self._happy = 100
    self._hunger = 100
    self._clean = 100
    self._animation = None
    self._mood = None
    self._mood_changed_at = (badge.ticks / 1000)
    self._action = None
    self._action_changed_at = None
    self._position_changed_at = (badge.ticks / 1000)
    self._position = (80, y + 2)
    self._direction = 1
    self._target = 80
    self._speed = 3
    self.set_mood("idle")

  def load(self, state):
    self._happy = state.get("happy", 0)
    self._hunger = state.get("hunger", 0)
    self._clean = state.get("clean", 0)

  def save(self):
    return {
      "happy": self._happy,
      "hunger": self._hunger,
      "clean": self._clean,
    }

  def draw(self):
    x, y = self._position

    if self._action:
      action_time = (badge.ticks / 1000) - self._action_changed_at
      sprite = sheets[self._action].sprite(round(action_time * 10) % FRAMES[self._action], 0)
    else:
      sprite = frame(self._mood)

    # the cloud says something needs doing, so it follows his needs
    if self.alive() and min(self._happy, self._hunger, self._clean) < 30:
      cloud = frame("notify")
    else:
      cloud = None

    width, height = sprite.width, sprite.height

    # invert pet if they are walking left
    width *= -self._direction

    floating = math.sin(badge.ticks / 250) * 5 + 5 if self._mood == "dead" else 0

    # the patch of ground he stands on, drawing in tighter the further he
    # floats off it. His cell leaves 15 empty rows under the art, hence y - 15,
    # and the edge is hard like the art it sits under.
    lift = max(0.0, 1.0 - floating / 20)
    antialias = screen.antialias
    screen.antialias = image.OFF
    screen.pen = color.rgb(0, 0, 0, 70)
    screen.shape(shape.ellipse(x, y - 15, 14 * lift, 4 * lift))
    screen.antialias = antialias

    x -= abs(width / 2)
    y -= height + floating

    screen.alpha = 150 if self._mood == "dead" else 255
    screen.blit(sprite, rect(x, y, width, height))
    screen.alpha = 255

    if cloud:
      # drawn at its own size over the middle of his cell; blitted into his
      # frame it would stretch and flip with him
      screen.blit(cloud, rect(x + (abs(width) - cloud.width) / 2, y,
                              cloud.width, cloud.height))

  def move_to(self, target):
    self._target = target
    self._position_changed_at = (badge.ticks / 1000)

  def move_to_center(self):
    self._target = 80
    self._position_changed_at = (badge.ticks / 1000)

  def move_to_random(self):
    self.move_to(random.randint(20, 140))

  def time_since_last_position_change(self):
    return (badge.ticks / 1000) - self._position_changed_at

  def set_mood(self, mood):
    self._mood = mood
    self._mood_changed_at = (badge.ticks / 1000)

  def do_action(self, action):
    self._action = action
    self._action_changed_at = (badge.ticks / 1000)

  def set_speed(self, speed):
    self._speed = speed

  def current_action(self):
    return self._action

  def alive(self):
    return self._happy > 0 and self._clean > 0 and self._hunger > 0

  def happy(self, amount=0):
    self._happy = clamp(self._happy + amount, 0, 100)
    return self._happy

  def clean(self, amount=0):
    self._clean = clamp(self._clean + amount, 0, 100)
    return self._clean

  def hunger(self, amount=0):
    self._hunger = clamp(self._hunger + amount, 0, 100)
    return self._hunger

  def update(self):
    x, y = self._position

    if abs(x - self._target) > self._speed and not self._action:
      self._direction = 1 if x > self._target else -1
      x -= (self._speed * self._direction)
      self._position = (x, y)
      if abs(x - self._target) <= self._speed and self._mood == "run":
        self.random_idle()

    # an action runs for four seconds, then he goes back to idling
    if self._action:
      if (badge.ticks / 1000) - self._action_changed_at > 4:
        self._action = None

  def random_idle(self):
    idles = ["dig", "idle", "lick", "tail"]
    self.set_mood(random.choice(idles))

  def time_since_last_mood_change(self):
    return (badge.ticks / 1000) - self._mood_changed_at
