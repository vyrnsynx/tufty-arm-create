"""The scrolling backdrop: layers of art, each moving at its own speed.

A layer tiles horizontally, so the art only has to be as wide as its pattern,
and the slower a layer runs the further away it reads. A world's front layer is
drawn over the sprites, so the cricket can pass behind it.
"""

GROUND = 120        # the play area's height, which the near layers sit on


class Layer:
  def __init__(self, path, y=None, spread=1.0, slower=8, front=False):
    self.sprite = image.load(path)
    self.pitch = self.sprite.width * spread
    self.slower = slower
    self.front = front
    # a layer without a y of its own stands on the ground
    self.y = GROUND - self.sprite.height if y is None else y

  def draw(self, offset):
    x = -((offset / self.slower) % self.pitch)
    while x < screen.width:
      screen.blit(self.sprite, vec2(x, self.y))
      x += self.pitch


class World:
  def __init__(self, name, layers):
    self.name = name
    self.behind = [layer for layer in layers if not layer.front]
    self.infront = [layer for layer in layers if layer.front]

  def draw(self, offset):
    for layer in self.behind:
      layer.draw(offset)

  def draw_front(self, offset):
    for layer in self.infront:
      layer.draw(offset)


# Every world is a background, a cloud and a grass, and they only differ in
# how the middle and near layers are handled. The purple one's clouds are a
# full width plane of floating icons rather than a tile, and its near layer is
# a bank the cricket flies behind.
SETTINGS = (
    ("cubicles", {"y": 8, "spread": 2.0}, {"slower": 4}),
    ("pcb-blue", {"y": 8, "spread": 2.0}, {"slower": 4}),
    ("pcb-green", {"y": 8, "spread": 2.0}, {"slower": 4}),
    ("cloud-purple", {"y": 0, "slower": 5}, {"slower": 3, "front": True}),
)


def load():
  """Every world, read up front so changing scene costs nothing mid game."""
  worlds = []
  for name, cloud, grass in SETTINGS:
    worlds.append(World(name, (
        Layer("assets/%s/background.png" % name, y=0),
        Layer("assets/%s/cloud.png" % name, **cloud),
        Layer("assets/%s/grass.png" % name, **grass),
    )))
  return worlds
