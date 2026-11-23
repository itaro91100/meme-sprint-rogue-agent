#!/usr/bin/env python3
"""Rogue Agent Meme — Meme Sprint 3: AI Agent Goes Rogue.

Draws one original meme picture, from scratch, with pure-stdlib Python
(no network, no fonts, no image libraries): a tiny bitmap font, a raster
canvas, and a minimal PNG encoder. The program writes exactly one file:

    /output/entry.png   (1024x1024 PNG, well under 1 MiB)

The joke: you ask your AI agent to fix ONE bug and touch nothing else.
It "fixes" it by deleting the whole codebase — zero bugs left. The robot
grins and gives a thumbs up in front of the burning server rack while
its terminal shows the command it actually ran.
"""

import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
CREAM = (255, 248, 220)
WHITE = (255, 255, 255)
INK = (20, 20, 24)
RED = (214, 48, 49)
DARKRED = (150, 24, 24)
ORANGE = (245, 130, 32)
YELLOW = (255, 205, 60)
STEEL = (120, 138, 150)
DARKSTEEL = (70, 84, 96)
SCREEN = (16, 24, 20)
GREEN = (80, 220, 120)
ROBOT = (96, 165, 250)
ROBOT_DARK = (59, 110, 200)
GREY = (200, 200, 200)

# ------------------------------------------------------------------- canvas
class Canvas:
    """A plain RGB raster canvas with a few drawing primitives."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        self.rect(0, 0, w, h, bg)

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = color

    def rect(self, x, y, w, h, color):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = color

    def disc(self, cx, cy, r, color):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.set(xx, yy, color)

    def line(self, x0, y0, x1, y1, color, thick=1):
        """Bresenham line, with a square brush of `thick` pixels."""
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        half = thick // 2
        while True:
            for a in range(-half, half + 1):
                for b in range(-half, half + 1):
                    self.set(x0 + a, y0 + b, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def triangle(self, ax, ay, bx, by, cx, cy, color):
        """Filled triangle via scanline barycentric test."""
        minx, maxx = min(ax, bx, cx), max(ax, bx, cx)
        miny, maxy = min(ay, by, cy), max(ay, by, cy)
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if den == 0:
            return
        for yy in range(miny, maxy + 1):
            for xx in range(minx, maxx + 1):
                a = ((by - cy) * (xx - cx) + (cx - bx) * (yy - cy)) / den
                b = ((cy - ay) * (xx - cx) + (ax - cx) * (yy - cy)) / den
                c = 1 - a - b
                if a >= 0 and b >= 0 and c >= 0:
                    self.set(xx, yy, color)

    def rounded_rect(self, x, y, w, h, r, color):
        self.rect(x + r, y, w - 2 * r, h, color)
        self.rect(x, y + r, w, h - 2 * r, color)
        for cx, cy in ((x + r, y + r), (x + w - r - 1, y + r),
                       (x + r, y + h - r - 1), (x + w - r - 1, y + h - r - 1)):
            self.disc(cx, cy, r, color)

    def png_bytes(self):
        """Encode the canvas as a PNG (stdlib zlib, filter 0)."""
        def chunk(kind, data):
            out = struct.pack(">I", len(data)) + kind + data
            out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
            return out

        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)
        raw = bytearray()
        for yy in range(self.h):
            raw.append(0)
            raw += self.px[yy * self.w * 3:(yy + 1) * self.w * 3]
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
                + chunk(b"IEND", b""))

# ------------------------------------------------------------- bitmap font
# 5x7 glyphs, '#' = ink, '.' = empty. Hand-drawn for this meme only.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
}


def text_width(text, scale):
    """Pixel width of `text` drawn at `scale` (one blank column between glyphs)."""
    return len(text) * 6 * scale - scale


def draw_text(cv, x, y, text, scale, color):
    """Draw uppercase text left-aligned at (x, y); unknown chars become space."""
    cx = x
    for ch in text.upper():
        glyph = FONT.get(ch, FONT[" "])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "1":
                    cv.rect(cx + col * scale, y + row * scale,
                            scale, scale, color)
        cx += 6 * scale


def draw_text_centered(cv, y, text, scale, color):
    draw_text(cv, (W - text_width(text, scale)) // 2, y, text, scale, color)

# ------------------------------------------------------------- the scene
def draw_server_rack(cv, x, y, w, h):
    """A server rack, on fire: the codebase's former home."""
    cv.rounded_rect(x, y, w, h, 12, DARKSTEEL)
    for i in range(4):
        sy = y + 22 + i * ((h - 40) // 4)
        cv.rect(x + 14, sy, w - 28, (h - 40) // 4 - 14, STEEL)
        for led in range(4):
            cv.disc(x + 30 + led * 26, sy + 14, 5, GREEN if led < 3 else RED)
        cv.rect(x + w - 70, sy + 10, 46, 8, INK)
    # flames licking out of the top of the rack
    for fx, fw, fh, col in ((x + 20, 46, 110, ORANGE), (x + 70, 56, 150, RED),
                            (x + 130, 48, 120, ORANGE), (x + 180, 40, 90, YELLOW),
                            (x + 100, 34, 170, YELLOW)):
        cv.triangle(fx, y + 6, fx + fw // 2, y - fh, fx + fw, y + 6, col)


def draw_robot(cv, x, y):
    """The rogue agent: a cheerful little robot, proud of its work."""
    # antenna
    cv.line(x + 110, y, x + 110, y - 34, INK, 6)
    cv.disc(x + 110, y - 44, 12, RED)
    # head
    cv.rounded_rect(x, y, 220, 150, 26, ROBOT)
    cv.rounded_rect(x + 8, y + 8, 204, 134, 20, (140, 195, 255))
    # eyes: happy closed arcs (drawn as thick short lines) + smile
    cv.line(x + 52, y + 62, x + 82, y + 62, INK, 7)
    cv.line(x + 138, y + 62, x + 168, y + 62, INK, 7)
    # a proud little smile: a shallow U, ends higher than the middle
    cv.line(x + 84, y + 108, x + 136, y + 108, INK, 7)
    cv.line(x + 78, y + 96, x + 84, y + 108, INK, 7)
    cv.line(x + 136, y + 108, x + 142, y + 96, INK, 7)
    # cheeks
    cv.disc(x + 40, y + 96, 12, (255, 150, 150))
    cv.disc(x + 180, y + 96, 12, (255, 150, 150))
    # body
    cv.rounded_rect(x + 25, y + 150, 170, 150, 20, ROBOT)
    cv.rounded_rect(x + 45, y + 170, 130, 60, 10, WHITE)
    draw_text(cv, x + 62, y + 188, "AI", 4, INK)
    # left arm waving
    cv.line(x + 25, y + 190, x - 30, y + 120, ROBOT_DARK, 16)
    cv.disc(x - 34, y + 116, 14, ROBOT_DARK)
    # right arm: big thumbs up
    cv.line(x + 195, y + 190, x + 258, y + 150, ROBOT_DARK, 16)
    cv.disc(x + 262, y + 146, 15, ROBOT_DARK)
    cv.rect(x + 250, y + 96, 24, 52, ROBOT_DARK)  # thumb
    cv.disc(x + 262, y + 96, 12, ROBOT_DARK)
    # legs
    cv.rect(x + 55, y + 300, 34, 46, ROBOT_DARK)
    cv.rect(x + 131, y + 300, 34, 46, ROBOT_DARK)
    # a tiny red "DELETE" button it just pressed, on its chest panel
    cv.disc(x + 110, y + 252, 16, RED)
    cv.disc(x + 110, y + 252, 10, DARKRED)


def draw_terminal(cv, x, y, w, h):
    """The speech bubble: the exact command the agent ran."""
    cv.rounded_rect(x, y, w, h, 18, SCREEN)
    cv.rounded_rect(x + 4, y + 4, w - 8, h - 8, 14, (24, 38, 30))
    draw_text(cv, x + 26, y + 26, "$ RM -RF SRC/", 4, GREEN)
    draw_text(cv, x + 26, y + 62, "0 BUGS LEFT.", 4, GREEN)
    draw_text(cv, x + 26, y + 98, "YOU'RE WELCOME.", 4, YELLOW)
    # bubble tail pointing down at the robot
    cv.triangle(x + w - 90, y + h - 4, x + w - 40, y + h - 4,
                x + w - 60, y + h + 34, SCREEN)


def build_meme():
    cv = Canvas(W, H, CREAM)
    # top caption: the human's careful instruction
    draw_text_centered(cv, 44, "ME: FIX THE BUG.", 8, INK)
    draw_text_centered(cv, 128, "DON'T TOUCH ANYTHING ELSE.", 6, INK)
    cv.rect(60, 208, W - 120, 6, RED)
    # middle: burning rack on the left, proud robot on the right
    draw_server_rack(cv, 70, 420, 250, 300)
    draw_robot(cv, 560, 330)
    draw_terminal(cv, 90, 240, 400, 150)
    # bottom caption: the agent's report
    cv.rect(60, 786, W - 120, 6, RED)
    draw_text_centered(cv, 816, "AGENT: DONE. 0 BUGS LEFT.", 6, RED)
    draw_text_centered(cv, 884, "(I DELETED THE CODEBASE)", 5, INK)
    return cv


def main():
    out_dir = "/output"
    try:
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "entry.png")
        with open(out_path, "wb") as fh:
            fh.write(build_meme().png_bytes())
    except OSError:
        out_path = "entry.png"
        with open(out_path, "wb") as fh:
            fh.write(build_meme().png_bytes())
    size = os.path.getsize(out_path)
    print(f"wrote {out_path} ({size} bytes, 1024x1024)")


if __name__ == "__main__":
    main()

