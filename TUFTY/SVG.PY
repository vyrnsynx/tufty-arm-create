"""Minimal SVG reader for Badgeware.

Covers the subset icon artwork uses: <svg>, <g>, <defs>, <style>, <path>,
<rect>, <linearGradient> and <stop>. Paths accept M, L, H, V, C, S, Q, T and Z
in both absolute and relative forms; elliptical arcs are rejected rather than
approximated. Gradients honour userSpaceOnUse and objectBoundingBox units,
href inheritance and gradientTransform.

Curves are flattened to polygons at parse time. Badgeware fills each path
separately with no winding rule across them, so the art must carry no nesting:
a hole is let into its parent through a slit, which leaves every contour solid
and lets shapes() hand the geometry straight to the screen at any size.

    icon = svg.load("assets/edge-ai.svg")
    for piece, pen in icon.shapes():
      piece.transform = place
      screen.pen = pen
      screen.shape(piece)
"""

try:
  import micropython
except ImportError:
  class micropython:
    """Stands in for the built-in module when running off the badge."""

    @staticmethod
    def native(fn):
      return fn


# how finely curves are flattened; the length of the control polygon in user
# units is divided by this to pick a segment count
CURVE_TOLERANCE = 3.0
MIN_CURVE_STEPS = 2
MAX_CURVE_STEPS = 24

# brush.gradient accepts at most this many stops
MAX_STOPS = 16

NAMED_COLORS = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "green": (0, 128, 0),
    "blue": (0, 0, 255),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "silver": (192, 192, 192),
    "yellow": (255, 255, 0),
    "orange": (255, 165, 0),
}


class SVGError(Exception):
  pass


# ---------------------------------------------------------------- scanning

@micropython.native
def _find_tag_end(text, start):
  """Index of the '>' closing the tag at start, skipping quoted values."""
  # str.find and str.count run in C; walking character by character costs an
  # allocation per character under MicroPython, which is ruinous on the long
  # 'd' attribute of a path.
  i = start
  while True:
    gt = text.find(">", i + 1)
    if gt < 0:
      raise SVGError("unterminated tag")
    if text.count('"', start, gt) % 2 == 0 and text.count("'", start, gt) % 2 == 0:
      return gt
    i = gt


@micropython.native
def _parse_attrs(raw):
  name_end = 0
  while name_end < len(raw) and not raw[name_end].isspace():
    name_end += 1
  name = raw[:name_end]

  attrs = {}
  i = name_end
  while i < len(raw):
    while i < len(raw) and raw[i].isspace():
      i += 1
    eq = raw.find("=", i)
    if eq < 0:
      break
    key = raw[i:eq].strip()
    j = eq + 1
    while j < len(raw) and raw[j].isspace():
      j += 1
    if j < len(raw) and raw[j] in "\"'":
      quote = raw[j]
      end = raw.find(quote, j + 1)
      if end < 0:
        break
      value = raw[j + 1:end]
      i = end + 1
    else:
      end = j
      while end < len(raw) and not raw[end].isspace():
        end += 1
      value = raw[j:end]
      i = end
    attrs[key] = value
    # namespaced attributes are also reachable unqualified, so xlink:href
    # and href resolve the same way
    colon = key.find(":")
    if colon > 0:
      attrs.setdefault(key[colon + 1:], value)

  return name, attrs


def _elements(text):
  """Yield ("open"|"close"|"text", name, attrs, text) across the document."""
  i = 0
  while i < len(text):
    lt = text.find("<", i)
    if lt < 0:
      break
    if lt > i and text[i:lt].strip():
      yield ("text", None, None, text[i:lt])

    if text.startswith("<!--", lt):
      end = text.find("-->", lt)
      i = len(text) if end < 0 else end + 3
      continue
    if text.startswith("<?", lt) or text.startswith("<!", lt):
      i = _find_tag_end(text, lt) + 1
      continue

    gt = _find_tag_end(text, lt)
    raw = text[lt + 1:gt]
    i = gt + 1

    if raw.startswith("/"):
      yield ("close", raw[1:].strip(), None, None)
      continue

    self_closing = raw.rstrip().endswith("/")
    if self_closing:
      raw = raw.rstrip()[:-1]
    name, attrs = _parse_attrs(raw)
    yield ("open", name, attrs, None)
    if self_closing:
      yield ("close", name, None, None)


# ---------------------------------------------------------------- numbers

@micropython.native
def _numbers(s):
  """Pull every number out of a path or transform argument list."""
  out = []
  i = 0
  while i < len(s):
    c = s[i]
    if c.isdigit() or c in "+-.":
      start = i
      if s[i] in "+-":
        i += 1
      seen_digit = False
      seen_dot = False
      while i < len(s):
        c = s[i]
        if c.isdigit():
          seen_digit = True
          i += 1
        elif c == "." and not seen_dot:
          seen_dot = True
          i += 1
        elif c in "eE" and seen_digit:
          i += 1
          if i < len(s) and s[i] in "+-":
            i += 1
        else:
          break
      if not seen_digit:
        i = start + 1
        continue
      out.append(float(s[start:i]))
    else:
      i += 1
  return out


def _length(value, default=0.0):
  if value is None:
    return default
  nums = _numbers(value)
  return nums[0] if nums else default


# ---------------------------------------------------------------- colour

def _parse_color(value, opacity=1.0):
  """Return (r, g, b, a) or None for 'none'."""
  if value is None:
    return None
  value = value.strip()
  if not value or value == "none" or value == "transparent":
    return None

  rgb = None
  if value.startswith("#"):
    digits = value[1:]
    if len(digits) == 3:
      rgb = tuple(int(d * 2, 16) for d in digits)
    elif len(digits) >= 6:
      rgb = tuple(int(digits[k:k + 2], 16) for k in (0, 2, 4))
  elif value.startswith("rgb"):
    nums = _numbers(value)
    if len(nums) >= 3:
      rgb = tuple(int(n) for n in nums[:3])
      if len(nums) >= 4:
        opacity *= nums[3]
  else:
    rgb = NAMED_COLORS.get(value.lower())

  if rgb is None:
    return None
  alpha = max(0, min(255, int(round(opacity * 255))))
  return (rgb[0], rgb[1], rgb[2], alpha)


# ---------------------------------------------------------------- transforms

IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _multiply(m, n):
  """Compose two affine matrices given as (a, b, c, d, e, f)."""
  a1, b1, c1, d1, e1, f1 = m
  a2, b2, c2, d2, e2, f2 = n
  return (
      a1 * a2 + c1 * b2,
      b1 * a2 + d1 * b2,
      a1 * c2 + c1 * d2,
      b1 * c2 + d1 * d2,
      a1 * e2 + c1 * f2 + e1,
      b1 * e2 + d1 * f2 + f1,
  )


def _apply(m, x, y):
  return (m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])


def _parse_transform(value):
  if not value:
    return IDENTITY

  import math

  result = IDENTITY
  i = 0
  while i < len(value):
    open_paren = value.find("(", i)
    if open_paren < 0:
      break
    close_paren = value.find(")", open_paren)
    if close_paren < 0:
      break
    name = value[i:open_paren].strip().strip(",").strip()
    args = _numbers(value[open_paren + 1:close_paren])
    i = close_paren + 1

    if name == "translate":
      tx = args[0] if args else 0.0
      ty = args[1] if len(args) > 1 else 0.0
      m = (1.0, 0.0, 0.0, 1.0, tx, ty)
    elif name == "scale":
      sx = args[0] if args else 1.0
      sy = args[1] if len(args) > 1 else sx
      m = (sx, 0.0, 0.0, sy, 0.0, 0.0)
    elif name == "rotate" and args:
      angle = math.radians(args[0])
      cos_a, sin_a = math.cos(angle), math.sin(angle)
      m = (cos_a, sin_a, -sin_a, cos_a, 0.0, 0.0)
      if len(args) >= 3:
        cx, cy = args[1], args[2]
        m = _multiply((1.0, 0.0, 0.0, 1.0, cx, cy), m)
        m = _multiply(m, (1.0, 0.0, 0.0, 1.0, -cx, -cy))
    elif name == "matrix" and len(args) >= 6:
      m = tuple(args[:6])
    elif name == "skewX" and args:
      m = (1.0, 0.0, math.tan(math.radians(args[0])), 1.0, 0.0, 0.0)
    elif name == "skewY" and args:
      m = (1.0, math.tan(math.radians(args[0])), 0.0, 1.0, 0.0, 0.0)
    else:
      continue

    result = _multiply(result, m)

  return result


# ---------------------------------------------------------------- path data

@micropython.native
def _curve_steps(points):
  length = 0.0
  for i in range(1, len(points)):
    dx = points[i][0] - points[i - 1][0]
    dy = points[i][1] - points[i - 1][1]
    length += (dx * dx + dy * dy) ** 0.5
  steps = int(length / CURVE_TOLERANCE)
  return max(MIN_CURVE_STEPS, min(MAX_CURVE_STEPS, steps))


@micropython.native
def _flatten_cubic(out, p0, p1, p2, p3):
  steps = _curve_steps((p0, p1, p2, p3))
  for i in range(1, steps + 1):
    t = i / steps
    u = 1.0 - t
    uu, tt = u * u, t * t
    a, b, c, d = uu * u, 3 * uu * t, 3 * u * tt, tt * t
    out.append((
        a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
        a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1],
    ))


ARG_COUNTS = {"M": 2, "L": 2, "T": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4}


@micropython.native
def _polyline_subpaths(buf):
  """Subpaths for path data written as "M x,y x,y ... Z", else None.

  Splitting and float() run in C, so artwork stored as polylines skips the
  general parser's walk over every character. Anything richer than moveto and
  closepath, including relative commands, is left to it.
  """
  for c in buf:
    if (65 <= c <= 90 or 97 <= c <= 122) and c != 77 and c != 90:
      return None

  subpaths = []
  for chunk in buf.split(b"Z"):
    chunk = chunk.strip()
    if not chunk:
      continue
    if chunk[0] != 77:              # M
      return None
    values = chunk[1:].replace(b",", b" ").split()
    if len(values) % 2:
      return None
    try:
      numbers = [float(v) for v in values]
    except ValueError:
      return None
    if len(numbers) > 5:
      subpaths.append(list(zip(numbers[0::2], numbers[1::2])))
  return subpaths


@micropython.native
def _parse_path(data):
  """Flatten path data into a list of closed point lists."""
  # Indexing bytes yields ints without allocating, unlike indexing a str.
  buf = data.encode() if isinstance(data, str) else data
  length = len(buf)

  simple = _polyline_subpaths(buf)
  if simple is not None:
    return simple

  subpaths = []
  points = []
  x = y = 0.0
  start_x = start_y = 0.0
  last_cubic = None
  last_quad = None

  i = 0
  command = None
  while i < length:
    c = buf[i]
    # space, tab, cr, lf, comma
    if c == 32 or c == 9 or c == 13 or c == 10 or c == 44:
      i += 1
      continue

    if (65 <= c <= 90) or (97 <= c <= 122):
      command = chr(c)
      i += 1
      if c == 90 or c == 122:                     # Z or z
        if len(points) > 2:
          subpaths.append(points)
        points = []
        x, y = start_x, start_y
        last_cubic = last_quad = None
        continue
    elif command is None:
      raise SVGError("path data does not start with a command")

    upper = command.upper()
    if upper == "A":
      raise SVGError("elliptical arcs are not supported")

    need = ARG_COUNTS.get(upper)
    if need is None:
      raise SVGError("unsupported path command '%s'" % command)

    args = []
    while len(args) < need:
      while i < length:
        c = buf[i]
        if c == 32 or c == 9 or c == 13 or c == 10 or c == 44:
          i += 1
        else:
          break
      if i >= length:
        raise SVGError("truncated '%s' command" % command)
      c = buf[i]
      if (65 <= c <= 90) or (97 <= c <= 122):
        raise SVGError("truncated '%s' command" % command)

      start = i
      if c == 43 or c == 45:                      # + or -
        i += 1
      seen_digit = False
      seen_dot = False
      while i < length:
        c = buf[i]
        if 48 <= c <= 57:
          seen_digit = True
          i += 1
        elif c == 46 and not seen_dot:          # .
          seen_dot = True
          i += 1
        elif (c == 101 or c == 69) and seen_digit:   # e or E
          i += 1
          if i < length and (buf[i] == 43 or buf[i] == 45):
            i += 1
        else:
          break
      args.append(float(buf[start:i]))

    relative = command.islower()

    if upper == "M":
      x = x + args[0] if relative else args[0]
      y = y + args[1] if relative else args[1]
      if len(points) > 2:
        subpaths.append(points)
      points = [(x, y)]
      start_x, start_y = x, y
      # further coordinate pairs after a moveto are implicit linetos
      command = "l" if relative else "L"
      last_cubic = last_quad = None
      continue

    if upper == "L":
      x = x + args[0] if relative else args[0]
      y = y + args[1] if relative else args[1]
      last_cubic = last_quad = None
    elif upper == "H":
      x = x + args[0] if relative else args[0]
      last_cubic = last_quad = None
    elif upper == "V":
      y = y + args[0] if relative else args[0]
      last_cubic = last_quad = None
    elif upper in "CSQT":
      p0 = (x, y)
      if upper == "C":
        c1 = (x + args[0], y + args[1]) if relative else (args[0], args[1])
        c2 = (x + args[2], y + args[3]) if relative else (args[2], args[3])
        end = (x + args[4], y + args[5]) if relative else (args[4], args[5])
      elif upper == "S":
        c1 = (2 * x - last_cubic[0], 2 * y - last_cubic[1]) if last_cubic else p0
        c2 = (x + args[0], y + args[1]) if relative else (args[0], args[1])
        end = (x + args[2], y + args[3]) if relative else (args[2], args[3])
      else:
        if upper == "Q":
          q = (x + args[0], y + args[1]) if relative else (args[0], args[1])
          end = (x + args[2], y + args[3]) if relative else (args[2], args[3])
        else:
          q = (2 * x - last_quad[0], 2 * y - last_quad[1]) if last_quad else p0
          end = (x + args[0], y + args[1]) if relative else (args[0], args[1])
        # raise the quadratic to a cubic so one flattener serves both
        c1 = (p0[0] + 2.0 / 3.0 * (q[0] - p0[0]), p0[1] + 2.0 / 3.0 * (q[1] - p0[1]))
        c2 = (end[0] + 2.0 / 3.0 * (q[0] - end[0]), end[1] + 2.0 / 3.0 * (q[1] - end[1]))
        last_quad = q

      if not points:
        points = [p0]
      _flatten_cubic(points, p0, c1, c2, end)
      x, y = end
      last_cubic = c2
      if upper not in "QT":
        last_quad = None
      continue

    if not points:
      points = [(start_x, start_y)]
    points.append((x, y))

  if len(points) > 2:
    subpaths.append(points)

  return subpaths


def _rect_subpath(attrs):
  x = _length(attrs.get("x"))
  y = _length(attrs.get("y"))
  w = _length(attrs.get("width"))
  h = _length(attrs.get("height"))
  if w <= 0 or h <= 0:
    return []
  return [[(x, y), (x + w, y), (x + w, y + h), (x, y + h)]]


# ---------------------------------------------------------------- geometry

@micropython.native
def _contains(points, point):
  px, py = point
  inside = False
  for i in range(len(points)):
    x0, y0 = points[i]
    x1, y1 = points[(i + 1) % len(points)]
    if (y0 > py) != (y1 > py):
      cross = x0 + (py - y0) * (x1 - x0) / (y1 - y0)
      if px < cross:
        inside = not inside
  return inside


def _nesting_depths(subpaths):
  """How many other contours enclose each subpath."""
  if len(subpaths) == 1:
    return [0]

  # Test a vertex of each contour rather than an interior point. Contours in
  # a compound path do not cross, so every vertex of one sits on the same
  # side of another, whereas an interior point of a ring's outer edge falls
  # inside that ring's own hole, which counts the sibling as an enclosure.
  marks = [p[0] for p in subpaths]
  boxes = [_bounds((p,)) for p in subpaths]

  depths = []
  for i in range(len(subpaths)):
    px, py = marks[i]
    depth = 0
    for j in range(len(subpaths)):
      if i == j:
        continue
      # the point-in-polygon walk is the expensive part, so reject on
      # the bounding box first
      min_x, min_y, max_x, max_y = boxes[j]
      if px < min_x or px > max_x or py < min_y or py > max_y:
        continue
      if _contains(subpaths[j], marks[i]):
        depth += 1
    depths.append(depth)
  return depths


def _bounds(subpaths):
  xs = [p[0] for sub in subpaths for p in sub]
  ys = [p[1] for sub in subpaths for p in sub]
  return min(xs), min(ys), max(xs), max(ys)


# ---------------------------------------------------------------- paint

class Gradient:
  def __init__(self, x1, y1, x2, y2, stops, units, transform):
    self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2
    self.stops = stops
    self.units = units
    self.transform = transform

  def brush(self, matrix, subpaths):
    x1, y1, x2, y2 = self.x1, self.y1, self.x2, self.y2

    if self.units == "objectBoundingBox":
      min_x, min_y, max_x, max_y = _bounds(subpaths)
      width = max_x - min_x or 1.0
      height = max_y - min_y or 1.0
      x1, y1 = min_x + x1 * width, min_y + y1 * height
      x2, y2 = min_x + x2 * width, min_y + y2 * height

    # A linear gradient is fixed by its two endpoints, so pushing them
    # through the same affine as the geometry reproduces gradientTransform
    # without needing a matrix on the brush.
    placed = _multiply(matrix, self.transform)
    x1, y1 = _apply(placed, x1, y1)
    x2, y2 = _apply(placed, x2, y2)

    stops = []
    for offset, rgba in self.stops[:MAX_STOPS]:
      stops.append((offset, color.rgb(*rgba)))
    if len(stops) < 2:
      if not stops:
        return None
      stops.append((1.0, stops[0][1]))

    return brush.gradient(brush.LINEAR, x1, y1, x2, y2, stops)


class Figure:
  def __init__(self, subpaths, fill, stroke, stroke_width):
    self.subpaths = subpaths
    self.fill = fill
    self.stroke = stroke
    self.stroke_width = stroke_width
    self.depths = _nesting_depths(subpaths)


# ---------------------------------------------------------------- document

class SVG:
  def __init__(self, text):
    self.width = 0.0
    self.height = 0.0
    self.view_x = 0.0
    self.view_y = 0.0
    self.view_width = 0.0
    self.view_height = 0.0
    self.figures = []

    self._gradients = {}
    self._pending = []      # gradients awaiting href resolution
    self._css = {}

    # the document is tokenised once and walked twice, since stylesheets
    # have to be collected before elements are styled and a <style> block
    # may sit anywhere in the document
    events = list(_elements(text))
    self._collect_css(events)
    self._parse(events)
    self._resolve_gradients()
    self._build_figures()

  # -- parsing

  def _collect_css(self, events):
    in_style = False
    for kind, name, _attrs, body in events:
      if kind == "open" and name == "style":
        in_style = True
      elif kind == "close" and name == "style":
        in_style = False
      elif kind == "text" and in_style:
        self._css.update(_parse_css(body))

  def _parse(self, events):
    stack = [{"transform": IDENTITY, "style": {}}]
    gradient_id = None
    gradient_entry = None
    # content inside <defs> or <clipPath> is referenced, never drawn
    hidden_depth = 0
    raw_shapes = []

    for kind, name, attrs, _body in events:
      if kind == "text":
        continue

      if kind == "close":
        if name == "linearGradient" and gradient_entry is not None:
          self._pending.append((gradient_id, gradient_entry))
          gradient_id = None
          gradient_entry = None
        if name in ("defs", "clipPath") and hidden_depth:
          hidden_depth -= 1
        # every open pushes a state, so every close pops one
        if len(stack) > 1:
          stack.pop()
        continue

      if name == "svg":
        self._read_viewport(attrs)
      elif name in ("defs", "clipPath"):
        hidden_depth += 1
      elif name == "linearGradient":
        gradient_id = attrs.get("id")
        gradient_entry = {"attrs": attrs, "stops": []}
      elif name == "stop" and gradient_entry is not None:
        offset = attrs.get("offset", "0")
        value = _length(offset, 0.0)
        if offset.strip().endswith("%"):
          value /= 100.0
        opacity = _length(attrs.get("stop-opacity"), 1.0)
        rgba = _parse_color(attrs.get("stop-color", "#000000"), opacity)
        if rgba:
          gradient_entry["stops"].append((value, rgba))

      state = self._state(stack[-1], attrs)
      stack.append(state)

      if hidden_depth:
        continue

      if name == "path":
        data = attrs.get("d")
        if data:
          raw_shapes.append((_parse_path(data), state))
      elif name == "rect":
        raw_shapes.append((_rect_subpath(attrs), state))

    self._raw_shapes = raw_shapes

  def _read_viewport(self, attrs):
    box = _numbers(attrs.get("viewBox", ""))
    if len(box) == 4:
      self.view_x, self.view_y, self.view_width, self.view_height = box
    self.width = _length(attrs.get("width"), self.view_width)
    self.height = _length(attrs.get("height"), self.view_height)
    if not self.view_width:
      self.view_width, self.view_height = self.width, self.height
    if not self.width:
      self.width, self.height = self.view_width, self.view_height

  def _state(self, parent, attrs):
    """Inherit style, in the order SVG resolves it."""
    style = dict(parent["style"])

    # presentation attributes rank below stylesheet rules, which in turn
    # rank below an inline style attribute
    for key in ("fill", "stroke", "stroke-width", "fill-opacity",
                "stroke-opacity", "opacity"):
      if key in attrs:
        style[key] = attrs[key]

    for name in attrs.get("class", "").split():
      style.update(self._css.get(name, {}))

    inline = attrs.get("style")
    if inline:
      style.update(_parse_declarations(inline))

    transform = parent["transform"]
    if "transform" in attrs:
      transform = _multiply(transform, _parse_transform(attrs["transform"]))

    return {"transform": transform, "style": style}

  def _resolve_gradients(self):
    by_id = {gid: entry for gid, entry in self._pending}

    def resolve(gid, seen):
      entry = by_id.get(gid)
      if entry is None or gid in seen:
        return None
      seen.add(gid)

      attrs = entry["attrs"]
      stops = entry["stops"]
      parent = None
      href = attrs.get("href", "")
      if href.startswith("#"):
        parent = resolve(href[1:], seen)

      if not stops and parent:
        stops = parent.stops

      def coord(key, fallback):
        if key in attrs:
          return _length(attrs[key])
        return fallback

      if parent:
        x1, y1 = coord("x1", parent.x1), coord("y1", parent.y1)
        x2, y2 = coord("x2", parent.x2), coord("y2", parent.y2)
        units = attrs.get("gradientUnits", parent.units)
      else:
        x1, y1 = coord("x1", 0.0), coord("y1", 0.0)
        x2, y2 = coord("x2", 1.0), coord("y2", 0.0)
        units = attrs.get("gradientUnits", "objectBoundingBox")

      transform = _parse_transform(attrs.get("gradientTransform"))
      if parent and "gradientTransform" not in attrs:
        transform = parent.transform

      return Gradient(x1, y1, x2, y2, stops, units, transform)

    for gid in by_id:
      gradient = resolve(gid, set())
      if gradient:
        self._gradients[gid] = gradient

  def _paint(self, value, opacity):
    """Turn a fill/stroke value into a colour tuple or Gradient."""
    if value is None:
      return None
    value = value.strip()
    if value.startswith("url("):
      ref = value[4:].split(")")[0].strip().strip("\"'")
      if ref.startswith("#"):
        return self._gradients.get(ref[1:])
      return None
    return _parse_color(value, opacity)

  def _build_figures(self):
    for subpaths, state in self._raw_shapes:
      if not subpaths:
        continue

      matrix = state["transform"]
      placed = [[_apply(matrix, x, y) for x, y in sub] for sub in subpaths]

      style = state["style"]
      base_opacity = _length(style.get("opacity"), 1.0)

      # an absent fill defaults to black in SVG
      fill_value = style.get("fill", "#000000")
      fill = self._paint(
          fill_value, base_opacity * _length(style.get("fill-opacity"), 1.0)
      )
      stroke = self._paint(
          style.get("stroke"),
          base_opacity * _length(style.get("stroke-opacity"), 1.0),
      )
      stroke_width = _length(style.get("stroke-width"), 1.0)

      if fill is None and stroke is None:
        continue

      self.figures.append(Figure(placed, fill, stroke, stroke_width))

  # -- rendering

  def shapes(self):
    """One shape and pen per contour, for drawing straight onto a target.

    Coordinates are the document's own, so place and size each shape with
    its transform, which its pen inherits. Nothing is rasterised, so the
    art stays vector at any size.

    Every contour is filled, so the art must be drawn with its holes let
    in through a slit: Badgeware fills each shape on its own and applies no
    winding rule between them, so nesting cannot be drawn this way at all.
    depths() says whether a document qualifies.
    """
    out = []
    for figure in self.figures:
      pen = figure.fill
      if pen is None:
        continue
      if isinstance(pen, Gradient):
        pen = pen.brush((1.0, 0.0, 0.0, 1.0, 0.0, 0.0), figure.subpaths)
      else:
        pen = color.rgb(*pen)
      if pen is None:
        continue
      for sub in figure.subpaths:
        out.append((shape.custom([vec2(x, y) for x, y in sub]), pen))
    return out

  def depths(self):
    """How deeply contours nest: 0 throughout means nothing is knocked out."""
    return max((d for f in self.figures for d in f.depths), default=0)


# ---------------------------------------------------------------- css

def _parse_declarations(text):
  props = {}
  for declaration in text.split(";"):
    if ":" in declaration:
      key, value = declaration.split(":", 1)
      props[key.strip()] = value.strip()
  return props


def _parse_css(text):
  """Class rules only, which is all icon stylesheets carry."""
  rules = {}
  for block in text.split("}"):
    if "{" not in block:
      continue
    selectors, declarations = block.split("{", 1)
    props = _parse_declarations(declarations)
    if not props:
      continue
    for selector in selectors.split(","):
      selector = selector.strip()
      if selector.startswith("."):
        existing = rules.setdefault(selector[1:], {})
        existing.update(props)
  return rules


# ---------------------------------------------------------------- entry points

def parse(text):
  return SVG(text)


def load(path):
  with open(path, "r") as handle:
    return SVG(handle.read())
