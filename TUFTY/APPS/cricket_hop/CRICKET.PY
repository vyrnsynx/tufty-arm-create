from obstacle import Obstacle

# the sheet holds the flap on its top row and the whole death on its bottom one
sheet = image.load("assets/cricket.png").spritesheet(14, 2)

FLAP = tuple(sheet.sprite(n, 0) for n in range(2))
DYING = tuple(sheet.sprite(n, 1) for n in range(13))

# wings beat faster on the way up than on the way down
FLAP_UP_MS = 70
FLAP_DOWN_MS = 140
DEATH_MS = 70       # per frame of the death sequence


class Cricket:
  def __init__(self):
    self.pos = (10, 50)
    self.score = 0
    # velocity is in pixels/second and gravity in pixels/second^2 so the
    # game plays the same however fast the display refreshes. these values
    # reproduce the original feel from when the badge ran at 30fps
    # (-4px/frame jump, +9px/frame/s gravity).
    self.velocity = 0
    self.gravity = 270
    self.last_update = None
    self.died_at = None

  def update(self):
    if self.is_dead():
      return

    if self.last_update:
      time_delta = (badge.ticks - self.last_update) / 1000
      self.velocity = self.velocity + (self.gravity * time_delta)

      self.pos = (self.pos[0], self.pos[1] + self.velocity * time_delta)

      # off the bottom of the screen and he is gone
      if self.pos[1] > 92:
        self.die()

      # a bang on the ceiling only costs him his climb
      if self.pos[1] <= 0:
        self.pos = (self.pos[0], 0)
        self.velocity = 0

    self.last_update = badge.ticks

    cricket_bounds = self.bounds()
    for obstacle in Obstacle.obstacles:
      # his hit box against the top and bottom of this obstacle
      for obstacle_bounds in obstacle.bounds():
        x1 = max(obstacle_bounds[0], cricket_bounds[0])
        y1 = max(obstacle_bounds[1], cricket_bounds[1])
        x2 = min(
            obstacle_bounds[0] + obstacle_bounds[2], cricket_bounds[0] + cricket_bounds[2])
        y2 = min(
            obstacle_bounds[1] + obstacle_bounds[3], cricket_bounds[1] + cricket_bounds[3])

        if x1 < x2 and y1 < y2:  # true if the two bounds overlap
          self.die()

      # a point for each obstacle behind him, counted once
      if not obstacle.passed and obstacle.x < self.pos[0] - 16:
        obstacle.passed = True
        self.score += 1

  def is_dead(self):
    return self.died_at is not None

  def is_done_dying(self):
    return (badge.ticks - self.died_at) > len(DYING) * DEATH_MS

  def die(self):
    if not self.died_at:
      self.died_at = badge.ticks

  def jump(self):
    self.velocity = -120

  def bounds(self):
    # be a little generous with crickets bounding box for collisions. the
    # art inks x 5..25 and y 5..27 of its 32 pixel square
    return (self.pos[0] + 5, self.pos[1] + 5, 21, 22)

  def draw(self):
    if self.is_dead():
      step = int((badge.ticks - self.died_at) / DEATH_MS)
      frame = DYING[min(step, len(DYING) - 1)]
    else:
      beat = FLAP_UP_MS if self.velocity < 0 else FLAP_DOWN_MS
      frame = FLAP[int(badge.ticks / beat) % len(FLAP)]

    # whole pixels, so the art lands on the grid it was drawn on
    screen.blit(frame, vec2(round(self.pos[0]), round(self.pos[1])))
