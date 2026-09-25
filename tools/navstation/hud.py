"""HUD gorunumu: renk paleti, vektor ikonlar, gosterge kartlari ve butonlar.

Yalniz cizim yapar; telemetri veya seri port bilmez. Degerler ui.py'den
hazir metin ve olcek olarak gelir.
"""

import math
import tkinter as tk

BG = "#060a0f"
PANEL = "#0c131b"
PANEL_HI = "#111c27"
EDGE = "#1d2d3d"
EDGE_HI = "#2e4a63"
FG = "#dff6ff"
DIM = "#4f6477"
DIM_DARK = "#2a3947"
ACCENT = "#28e0ff"
OK = "#3dffa0"
WARN = "#ffb62e"
DANGER = "#ff3b5c"
SKY_HIGH = "#12407a"
SKY_LOW = "#2d82d4"
GROUND_NEAR = "#8d5a2a"
GROUND_FAR = "#5a3517"
PLANE = "#ffc93c"

MONO = "Menlo"
TITLE_FONT = (MONO, 16, "bold")
LABEL_FONT = (MONO, 10, "bold")
SMALL_FONT = (MONO, 9, "bold")
VALUE_FONT = (MONO, 24, "bold")
VALUE_FONT_SMALL = (MONO, 14, "bold")
UNIT_FONT = (MONO, 11, "bold")
BUTTON_FONT = (MONO, 11, "bold")

# 3S LiPo: hucre basina 3.3 V bos, 4.2 V dolu kabul ediliyor.
BATTERY_EMPTY_V = 9.9
BATTERY_FULL_V = 12.6


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def battery_colour(fraction: float) -> str:
    if fraction > 0.5:
        return OK
    if fraction > 0.2:
        return WARN
    return DANGER


def temperature_colour(celsius: float) -> str:
    if celsius < 45:
        return OK
    if celsius < 65:
        return WARN
    return DANGER


def chamfer(c: tk.Canvas, x0: float, y0: float, x1: float, y1: float,
            cut: float, **kwargs) -> int:
    """Sag ust ve sol alt kosesi kesik dikdortgen; oyun arayuzlerindeki panel."""
    return c.create_polygon(
        x0, y0, x1 - cut, y0, x1, y0 + cut, x1, y1, x0 + cut, y1, x0, y1 - cut,
        **kwargs)


def pill(c: tk.Canvas, x: float, y: float, text: str, colour: str,
         filled: bool = False, font=LABEL_FONT) -> float:
    """Sol kenari x'te duran etiket rozeti; sag kenarin x'ini dondurur."""
    label = c.create_text(x + 12, y, text=text, anchor="w", font=font,
                          fill=BG if filled else colour)
    _, _, right, _ = c.bbox(label)
    frame = chamfer(c, x, y - 12, right + 12, y + 12, 6,
                    fill=colour if filled else PANEL, outline=colour)
    c.tag_lower(frame, label)
    return right + 12


def _rotate(cx: float, cy: float, px: float, py: float, deg: float) -> tuple[float, float]:
    # Ekran koordinatinda y asagi baktigi icin pozitif aci saat yonunde doner.
    a = math.radians(deg)
    return (cx + px * math.cos(a) - py * math.sin(a),
            cy + px * math.sin(a) + py * math.cos(a))


def _rotated(cx, cy, points, deg):
    out = []
    for px, py in points:
        out.extend(_rotate(cx, cy, px, py, deg))
    return out


# -- ikonlar --------------------------------------------------------------
#
# Hepsi ayni imzayi tasir: (tuval, merkez x, merkez y, boyut, renk, seviye).
# Seviye ikonun canli kismidir: dolum orani veya aci. None ise ikon bos cizilir.


def icon_thermometer(c, x, y, s, colour, level):
    tube_w = s * 0.13
    top = y - s * 0.44
    bulb_y = y + s * 0.28
    bulb_r = s * 0.17
    c.create_oval(x - tube_w, top - tube_w, x + tube_w, top + tube_w,
                  outline=colour, width=2)
    c.create_rectangle(x - tube_w, top, x + tube_w, bulb_y, outline=colour, width=2)
    c.create_rectangle(x - tube_w + 2, top, x + tube_w - 2, bulb_y, fill=PANEL, outline="")
    c.create_oval(x - bulb_r, bulb_y - bulb_r, x + bulb_r, bulb_y + bulb_r,
                  outline=colour, width=2, fill=colour if level is not None else PANEL)
    if level is not None:
        column_top = bulb_y - clamp01(level) * (bulb_y - top)
        c.create_rectangle(x - tube_w * 0.45, column_top, x + tube_w * 0.45, bulb_y,
                           fill=colour, outline="")
    for i in range(3):
        ty = top + (i + 1) * (bulb_y - top) / 4
        c.create_line(x + tube_w + 3, ty, x + tube_w + 8, ty, fill=colour)


def icon_battery(c, x, y, s, colour, level):
    x0, x1 = x - s * 0.42, x + s * 0.34
    y0, y1 = y - s * 0.22, y + s * 0.22
    c.create_rectangle(x0, y0, x1, y1, outline=colour, width=2)
    c.create_rectangle(x1, y - s * 0.09, x1 + s * 0.08, y + s * 0.09,
                       fill=colour, outline="")
    if level is None:
        return
    lit = math.ceil(clamp01(level) * 4)
    seg_w = (x1 - x0 - 6) / 4
    for i in range(lit):
        sx = x0 + 4 + i * seg_w
        c.create_rectangle(sx, y0 + 4, sx + seg_w - 2, y1 - 4, fill=colour, outline="")


def icon_altitude(c, x, y, s, colour, level):
    base = y + s * 0.32
    c.create_polygon(x - s * 0.46, base, x - s * 0.16, y - s * 0.12,
                     x - s * 0.02, y + s * 0.06, x + s * 0.16, y - s * 0.3,
                     x + s * 0.46, base, fill=PANEL, outline=colour, width=2)
    c.create_line(x - s * 0.46, base, x + s * 0.46, base, fill=colour, width=2)
    # Tepedeki kar cizgisi daglari okunur kilar.
    c.create_line(x + s * 0.08, y - s * 0.18, x + s * 0.16, y - s * 0.12,
                  x + s * 0.24, y - s * 0.18, fill=colour, width=2)


def icon_gauge(c, x, y, s, colour, level):
    r = s * 0.42
    c.create_arc(x - r, y - r, x + r, y + r, start=-40, extent=260,
                 style="arc", outline=colour, width=2)
    for i in range(6):
        a = math.radians(220 - i * 52)
        c.create_line(x + r * 0.72 * math.cos(a), y - r * 0.72 * math.sin(a),
                      x + r * 0.92 * math.cos(a), y - r * 0.92 * math.sin(a),
                      fill=colour)
    frac = 0.5 if level is None else clamp01(level)
    a = math.radians(220 - frac * 260)
    c.create_line(x, y, x + r * 0.7 * math.cos(a), y - r * 0.7 * math.sin(a),
                  fill=colour, width=2)
    c.create_oval(x - 3, y - 3, x + 3, y + 3, fill=colour, outline="")


def icon_pitch(c, x, y, s, colour, level):
    deg = -(level or 0.0)
    c.create_line(x - s * 0.46, y, x + s * 0.46, y, fill=DIM_DARK, dash=(2, 3))
    body = [(-s * 0.4, 0), (s * 0.36, 0)]
    c.create_line(*_rotated(x, y, body, deg), fill=colour, width=3, capstyle="round")
    fin = [(-s * 0.4, 0), (-s * 0.32, -s * 0.2), (-s * 0.2, 0)]
    c.create_polygon(*_rotated(x, y, fin, deg), fill=colour, outline="")
    wing = [(-s * 0.02, 0), (s * 0.1, s * 0.12)]
    c.create_line(*_rotated(x, y, wing, deg), fill=colour, width=3)
    nx, ny = _rotate(x, y, s * 0.4, 0, deg)
    c.create_oval(nx - 3, ny - 3, nx + 3, ny + 3, fill=colour, outline="")


def icon_roll(c, x, y, s, colour, level):
    deg = level or 0.0
    c.create_line(x - s * 0.46, y, x + s * 0.46, y, fill=DIM_DARK, dash=(2, 3))
    wings = [(-s * 0.46, 0), (s * 0.46, 0)]
    c.create_line(*_rotated(x, y, wings, deg), fill=colour, width=3, capstyle="round")
    fin = [(0, 0), (0, -s * 0.24)]
    c.create_line(*_rotated(x, y, fin, deg), fill=colour, width=3)
    r = s * 0.1
    c.create_oval(x - r, y - r, x + r, y + r, fill=PANEL, outline=colour, width=2)


def icon_compass(c, x, y, s, colour, level):
    r = s * 0.42
    c.create_oval(x - r, y - r, x + r, y + r, outline=colour, width=2)
    for i in range(8):
        a = math.radians(i * 45)
        inner = r * (0.72 if i % 2 else 0.6)
        c.create_line(x + inner * math.sin(a), y - inner * math.cos(a),
                      x + r * math.sin(a), y - r * math.cos(a), fill=colour)
    deg = level or 0.0
    north = [(0, -r * 0.8), (r * 0.18, 0), (-r * 0.18, 0)]
    south = [(0, r * 0.8), (r * 0.18, 0), (-r * 0.18, 0)]
    fill = DANGER if level is not None else colour
    c.create_polygon(*_rotated(x, y, north, deg), fill=fill, outline="")
    c.create_polygon(*_rotated(x, y, south, deg), fill=colour, outline="")


def icon_gyro(c, x, y, s, colour, level):
    r = s * 0.36
    c.create_arc(x - r, y - r, x + r, y + r, start=30, extent=290,
                 style="arc", outline=colour, width=2)
    tip_x = x + r * math.cos(math.radians(30))
    tip_y = y - r * math.sin(math.radians(30))
    c.create_polygon(tip_x - 7, tip_y - 5, tip_x + 5, tip_y - 7, tip_x + 1, tip_y + 5,
                     fill=colour, outline="")
    ry = r * 0.4
    c.create_oval(x - r * 0.9, y - ry, x + r * 0.9, y + ry, outline=DIM, width=1)
    c.create_oval(x - 3, y - 3, x + 3, y + 3, fill=colour, outline="")


def icon_accel(c, x, y, s, colour, level):
    ox, oy = x - s * 0.18, y + s * 0.2
    for dx, dy in ((s * 0.5, 0), (0, -s * 0.52), (-s * 0.26, s * 0.2)):
        c.create_line(ox, oy, ox + dx, oy + dy, fill=colour, width=2, arrow="last",
                      arrowshape=(7, 8, 3))
    c.create_oval(ox - 3, oy - 3, ox + 3, oy + 3, fill=colour, outline="")


# -- widget'lar -----------------------------------------------------------


class Tile(tk.Canvas):
    """Ikonlu gosterge karti: baslik, buyuk deger, birim, yan bilgi, seviye cubugu."""

    WIDTH = 290
    HEIGHT = 80
    BAR_SEGMENTS = 22

    def __init__(self, parent: tk.Widget, title: str, icon, value_font=VALUE_FONT):
        super().__init__(parent, width=self.WIDTH, height=self.HEIGHT,
                         bg=BG, highlightthickness=0)
        self.title = title
        self.icon = icon
        self.value_font = value_font
        self._content: tuple | None = None
        self._live = True
        self.reset()

    def reset(self) -> None:
        self._live = True
        self.show("--", colour=DIM)

    def show(self, value: str, unit: str = "", sub: str = "", colour: str = ACCENT,
             fraction: float | None = None, level: float | None = None) -> None:
        content = (value, unit, sub, colour, fraction, level)
        if content != self._content:
            self._content = content
            self._draw()

    def set_live(self, live: bool) -> None:
        # Bayat linkte kart soluklasir ama son deger okunur kalir.
        if live != self._live:
            self._live = live
            self._draw()

    def _draw(self) -> None:
        value, unit, sub, colour, fraction, level = self._content
        if not self._live:
            colour = DIM
        value_fill = FG if self._live and value != "--" else DIM
        w, h = self.WIDTH, self.HEIGHT

        self.delete("all")
        chamfer(self, 1, 1, w - 1, h - 1, 12, fill=PANEL, outline=EDGE)
        self.create_line(1, 14, 1, h - 14, fill=colour, width=3)
        self.create_line(w - 12, 1, w - 1, 12, fill=colour, width=2)

        icon_box = 58
        self.create_rectangle(10, 10, 10 + icon_box, h - 10, fill=PANEL_HI, outline=EDGE)
        self.icon(self, 10 + icon_box / 2, h / 2, icon_box * 0.9, colour, level)

        text_x = icon_box + 22
        self.create_text(text_x, 10, text=self.title, anchor="nw",
                         font=SMALL_FONT, fill=DIM)
        if sub:
            self.create_text(w - 18, 10, text=sub, anchor="ne",
                             font=SMALL_FONT, fill=colour)
        baseline = h - 18 if fraction is not None else h - 12
        item = self.create_text(text_x, baseline, text=value, anchor="sw",
                                font=self.value_font, fill=value_fill)
        if unit:
            right = self.bbox(item)[2]
            self.create_text(right + 5, baseline - 4, text=unit, anchor="sw",
                             font=UNIT_FONT, fill=DIM)

        if fraction is not None:
            self._draw_bar(text_x, w - 18, h - 13, clamp01(fraction), colour)

    def _draw_bar(self, x0: float, x1: float, y: float, fraction: float,
                  colour: str) -> None:
        seg = (x1 - x0) / self.BAR_SEGMENTS
        lit = round(fraction * self.BAR_SEGMENTS)
        for i in range(self.BAR_SEGMENTS):
            sx = x0 + i * seg
            self.create_rectangle(sx, y, sx + seg - 2, y + 5,
                                  fill=colour if i < lit else DIM_DARK, outline="")


class HudButton(tk.Frame):
    """Duz, cerceveli buton. macOS tk.Button'i renk kabul etmedigi icin Label'dan.

    configure(text=..., state=...) tk.Button gibi calisir; pencere kodu
    ikisini ayirt etmek zorunda kalmaz.
    """

    def __init__(self, parent: tk.Widget, text: str, command, tone: str = ACCENT,
                 state: str = "normal"):
        super().__init__(parent, bg=tone, padx=1, pady=1)
        self._command = command
        self._tone = tone
        self._state = state
        self._hover = False
        self._label = tk.Label(self, text=text, font=BUTTON_FONT, padx=16, pady=7)
        self._label.pack(fill="both", expand=True)
        for widget in (self, self._label):
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<ButtonRelease-1>", self._on_click)
        self._paint()

    def configure(self, cnf=None, **kwargs):
        if "text" in kwargs:
            text = kwargs.pop("text")
            if self._label.cget("text") != text:
                self._label.configure(text=text)
        if "state" in kwargs:
            state = kwargs.pop("state")
            if state != self._state:
                self._state = state
                self._paint()
        if cnf or kwargs:
            return super().configure(cnf, **kwargs)
        return None

    config = configure

    @property
    def enabled(self) -> bool:
        return self._state != "disabled"

    def _paint(self) -> None:
        if not self.enabled:
            tk.Frame.configure(self, bg=EDGE)
            self._label.configure(bg=PANEL, fg=DIM_DARK, cursor="arrow")
            return
        tk.Frame.configure(self, bg=self._tone)
        if self._hover:
            self._label.configure(bg=self._tone, fg=BG, cursor="hand2")
        else:
            self._label.configure(bg=PANEL, fg=self._tone, cursor="hand2")

    def _on_enter(self, _event) -> None:
        self._hover = True
        self._paint()

    def _on_leave(self, _event) -> None:
        self._hover = False
        self._paint()

    def _on_click(self, _event) -> None:
        if self.enabled:
            self._command()
