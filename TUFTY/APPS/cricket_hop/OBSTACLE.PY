import random

sprites = image.load("assets/obstacles.png").spritesheet(2, 1)

# The obstacles travel at this, and the scenery's scroll advances at it too,
# so one constant keeps the scene in step.
SPEED = 30          # pixels a second at level one
EVERY = 2500        # milliseconds between obstacles at level one


class Obstacle:
  obstacles = []
  next_spawn_time = None

  @staticmethod
  def spawn(faster=1.0):
    Obstacle.obstacles.append(Obstacle())
    # they come round quicker as they move quicker, so the gap between them
    # stays the same distance apart however fast the game is running
    Obstacle.next_spawn_time = badge.ticks + EVERY / faster

    # anything off the left hand side is done with
    Obstacle.obstacles = [o for o in Obstacle.obstacles if o.x > -32]

  def __init__(self):
    self.x = screen.width
    self.gap_height = 50
    self.gap_y = random.randrange(10, screen.height - self.gap_height - 20, 5)

    # so the point it is worth is only counted once
    self.passed = False

  def update(self, faster=1.0):
    self.x -= SPEED * faster * (badge.ticks_delta / 1000)

  def bounds(self):
    # be a little generous with obstacle bounding boxes for collisions
    return (
        (self.x, 0, 32, self.gap_y - 6),
        (self.x, self.gap_y + self.gap_height + 6,
            32, 120 - self.gap_y - self.gap_height - 6)
    )

  def draw(self):
    screen.blit(sprites.sprite(0, 0),
                rect(self.x, self.gap_y - 72, 32, 32))
    screen.blit(sprites.sprite(0, 0),
                rect(self.x, self.gap_y - 48, 32, 32))
    screen.blit(sprites.sprite(1, 0),
                rect(self.x, self.gap_y - 32, 32, 32))  # spikes, yikes!

    screen.blit(sprites.sprite(1, 0),
                rect(self.x, self.gap_y + self.gap_height, 32, -32))  # spikes, yikes!
    screen.blit(sprites.sprite(0, 0),
                rect(self.x, self.gap_y + self.gap_height + 32, 32, -32))
    screen.blit(sprites.sprite(0, 0),
                rect(self.x, self.gap_y + self.gap_height + 48, 32, -32))
