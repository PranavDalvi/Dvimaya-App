import math
from PIL import Image, ImageDraw

# ---- Minimal Hilbert Curve Implementation ----


def graycode(x):
    return x ^ (x >> 1)


def igraycode(x):
    if x == 0:
        return x
    m = int(math.ceil(math.log(x, 2)))+1
    i, j = x, 1
    while j < m:
        i = i ^ (x >> j)
        j += 1
    return i


def bits(n, width):
    return [(n >> i) & 1 for i in reversed(range(width))]


def bits2int(bits):
    n = 0
    for p, i in enumerate(reversed(bits)):
        n += i * 2**p
    return n


def rrot(x, i, width):
    i = i % width
    return ((x >> i) | (x << (width - i))) & (2**width - 1)


def lrot(x, i, width):
    i = i % width
    return ((x << i) | (x >> (width - i))) & (2**width - 1)


def tsb(x, width):
    i = 0
    while x & 1 and i <= width:
        x = x >> 1
        i += 1
    return i


def setbit(x, w, i, b):
    if b:
        return x | 2**(w-i-1)
    else:
        return x & ~2**(w-i-1)


def bitrange(x, width, start, end):
    return (x >> (width - end)) & ((2**(end-start)) - 1)


def entropy(data, blocksize, offset, symbols=256):
    if len(data) < blocksize:
        raise ValueError("Data length must be larger than block size.")
    if offset < blocksize // 2:
        start = 0
    elif offset > len(data) - blocksize // 2:
        start = len(data) - blocksize // 2
    else:
        start = offset - blocksize // 2
    hist = {}
    for i in data[start:start + blocksize]:
        hist[i] = hist.get(i, 0) + 1
    base = min(blocksize, symbols)
    entropy_value = 0
    for i in hist.values():
        p = i / float(blocksize)
        entropy_value += (p * math.log(p, base))
    return -entropy_value


def transform(entry, direction, width, x):
    return rrot((x ^ entry), direction+1, width)


def itransform(entry, direction, width, x):
    return lrot(x, direction+1, width) ^ entry


def direction_fn(x, n):
    if x == 0:
        return 0
    elif x % 2 == 0:
        return tsb(x-1, n) % n
    else:
        return tsb(x, n) % n


def entry_fn(x):
    if x == 0:
        return 0
    else:
        return graycode(2 * ((x - 1) // 2))


def hilbert_point(dimension, order, h):
    hwidth = order*dimension
    e, d = 0, 0
    p = [0]*dimension
    for i in range(order):
        w = bitrange(h, hwidth, i*dimension, i*dimension+dimension)
        l = graycode(w)
        l = itransform(e, d, dimension, l)
        for j in range(dimension):
            b = bitrange(l, dimension, j, j+1)
            p[j] = setbit(p[j], order, i, b)
        e = e ^ lrot(entry_fn(w), d+1, dimension)
        d = (d + direction_fn(w, dimension) + 1) % dimension
    return p


class Hilbert:
    def __init__(self, dimension, order):
        self.dimension, self.order = dimension, order

    @classmethod
    def fromSize(cls, dimension, size):
        x = math.log(size, 2)
        if not float(x)/dimension == int(x)/dimension:
            raise ValueError(
                "Size does not fit Hilbert curve of dimension %s." % dimension)
        return Hilbert(dimension, int(x/dimension))

    def __len__(self):
        return 2**(self.dimension*self.order)

    def __getitem__(self, idx):
        if idx >= len(self):
            raise IndexError
        return self.point(idx)

    def dimensions(self):
        return [int(math.ceil(len(self)**(1/float(self.dimension))))]*self.dimension

    def point(self, idx):
        return hilbert_point(self.dimension, self.order, idx)

# ---- Visualization Logic ----


class _Color:
    def __init__(self, data, block):
        self.data, self.block = data, block
        s = list(set(data))
        s.sort()
        self.symbol_map = {v: i for (i, v) in enumerate(s)}

    def __len__(self):
        return len(self.data)

    def point(self, x):
        if self.block and (self.block[0] <= x < self.block[1]):
            return self.block[2]
        else:
            return self.getPoint(x)


class ColorGradient(_Color):
    def getPoint(self, x):
        c = self.data[x] / 255.0
        return [
            int(255 * c),
            int(255 * c),
            int(255 * c)
        ]


class ColorHilbert(_Color):
    def getPoint(self, x):
        c = self.data[x]
        if c == 0x00:
            return [0, 0, 0]
        elif 0x01 <= c <= 0x1F:
            return [77, 175, 74]
        elif 0x20 <= c <= 0x7E:
            return [16, 114, 184]
        elif 0x7F <= c < 0xFF:
            return [228, 26, 28]
        elif c == 0xFF:
            return [255, 255, 255]


class ColorClass(_Color):
    def getPoint(self, x):
        c = self.data[x]
        if c == 0x00:
            return [0, 0, 0]  # Black for 0x00
        elif 0x01 <= c <= 0x1F:
            return [77, 175, 74]  # Green for low
        elif 0x20 <= c <= 0x7E:
            return [16, 114, 184]  # Blue for ASCII
        elif 0x7F <= c < 0xFF:
            return [228, 26, 28]  # Red for high
        elif c == 0xFF:
            return [255, 255, 255]  # White for 0xFF


class ColorEntropy(_Color):
    def getPoint(self, x):
        e = entropy(self.data, 32, x, len(self.symbol_map))

        def curve(v):
            f = (4 * v - 4 * v ** 2) ** 4
            return max(f, 0)

        r = curve(e - 0.5) if e > 0.5 else 0
        b = e ** 2
        return [int(255 * r), 0, int(255 * b)]


def drawmap_unrolled(size, csource, output):
    mapcurve = Hilbert.fromSize(2, size ** 2)
    c = Image.new("RGB", (size, size * 4))
    cd = ImageDraw.Draw(c)
    step = len(csource) / float(len(mapcurve) * 4)
    for quad in range(4):
        for i, p in enumerate(mapcurve):
            off = (i + (quad * size ** 2))
            color = csource.point(int(off * step))
            x, y = tuple(p)
            cd.point((x, y + (size * quad)), fill=tuple(color))
    c.save(output)


def drawmap_square(size, csource, output):
    mapcurve = Hilbert.fromSize(2, size ** 2)
    c = Image.new("RGB", mapcurve.dimensions())
    cd = ImageDraw.Draw(c)
    step = len(csource) / float(len(mapcurve))
    for i, p in enumerate(mapcurve):
        color = csource.point(int(i * step))
        cd.point(tuple(p), fill=tuple(color))
    c.save(output)


def visualize_bin(
    input_bytes,
    output_filename,
    color_mode="hilbert",      # "class", "hilbert", "entropy", "gradient"
    image_size=256,          # e.g. 256
    image_type="unrolled",   # "unrolled" or "square"
    block=None,
):
    """
    Visualize binary data as an image.

    Args:
        input_bytes (bytes): The data to visualize.
        output_filename (str): Path to save the PNG.
        color_mode (str): Color mode.
        image_size (int): Image width.
        image_type (str): "unrolled" or "square".
        block (tuple or None): Optional block (unused in most cases).
    """
    if color_mode == "class":
        csource = ColorClass(input_bytes, block)
    elif color_mode == "hilbert":
        csource = ColorHilbert(input_bytes, block)
    elif color_mode == "gradient":
        csource = ColorGradient(input_bytes, block)
    else:
        csource = ColorEntropy(input_bytes, block)

    if image_type == "unrolled":
        drawmap_unrolled(image_size, csource, output_filename)
    elif image_type == "square":
        drawmap_square(image_size, csource, output_filename)
