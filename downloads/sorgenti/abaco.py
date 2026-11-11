#!/usr/bin/env python3
"""
Abaco colorato – un piccolo soroban interattivo fatto con Tkinter.

Ogni asta rappresenta una cifra; le ultime DECIMALS aste (dopo la virgola)
sono i decimali: decimi, centesimi, millesimi.
  • la pallina in alto (sopra la sbarra) vale 5
  • le 4 palline in basso valgono 1 ciascuna
Una pallina "conta" quando è spinta contro la sbarra centrale.

Comandi:
  • clic su una pallina          → la sposta (insieme a quelle che spinge)
  • rotella del mouse su un'asta → +1 / −1 in quella posizione (con riporto)
  • Spazio = conta (a passi di 0,1) · R = casuale · Esc = azzera · I = imposta numero
"""

import math
import random
from decimal import Decimal, InvalidOperation
import tkinter as tk
import tkinter.font as tkfont
from tkinter import simpledialog

# ─────────────────────────── Configurazione ────────────────────────────
W, H = 1120, 700
RODS = 10
DECIMALS = 3                      # quante aste dopo la virgola
INT_RODS = RODS - DECIMALS
MAX_VALUE = 10 ** RODS - 1        # valore interno, in millesimi (10^-DECIMALS)
COUNT_STEP = 10 ** (DECIMALS - 1)  # "Conta" avanza di 0,1

# Cornice e area interna
FX0, FY0, FX1, FY1 = 70, 150, W - 70, 560
FT = 30
IX0, IY0, IX1, IY1 = FX0 + FT, FY0 + FT, FX1 - FT, FY1 - FT
BEAM_Y0, BEAM_Y1 = IY0 + 92, IY0 + 112

# Palline
BW, BH = 74, 36
SPACING = (IX1 - IX0) / RODS

ROD_COLORS = [
    "#ff5e7e",  # rosa
    "#ff8c42",  # arancio
    "#ffd23f",  # giallo
    "#7bd389",  # verde
    "#3bceac",  # acqua
    "#4cc9f0",  # azzurro
    "#4895ef",  # blu
    "#9b5de5",  # viola
    "#f15bb5",  # magenta
    "#ff99c8",  # rosa chiaro
]

_INT_LABELS = ["1", "10", "100", "1K", "10K", "100K", "1M", "10M", "100M"]
PLACE_LABELS = _INT_LABELS[:INT_RODS][::-1] + ["0," + "0" * k + "1" for k in range(DECIMALS)]

BG_TOP, BG_BOTTOM = "#1a1c33", "#0d0e1c"
INNER_TOP, INNER_BOTTOM = "#2b3052", "#1a1d33"
DEC_TOP, DEC_BOTTOM = "#3a2b55", "#221a38"        # sfondo della parte decimale
COMMA_COLOR = "#ffd23f"
WOOD, WOOD_DARK, WOOD_LIGHT = "#8a5530", "#5c3519", "#b77b48"


# ─────────────────────────── Utilità colore ────────────────────────────
def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(c)))) for c in rgb)


def blend(c1, c2, t):
    a, b = _rgb(c1), _rgb(c2)
    return _hex(tuple(a[i] + (b[i] - a[i]) * t for i in range(3)))


def lighten(c, t):
    return blend(c, "#ffffff", t)


def darken(c, t):
    return blend(c, "#000000", t)


def rounded_rect(cv, x0, y0, x1, y1, r, **kw):
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


def bead_shape(cx, cy, w, h):
    """Forma a doppio cono arrotondato (tipica pallina da soroban)."""
    hw, hh = w / 2, h / 2 * 1.18  # compensa l'arrotondamento dello spline
    k = w * 0.22
    return [cx - hw, cy,
            cx - hw + k, cy - hh, cx + hw - k, cy - hh,
            cx + hw, cy,
            cx + hw - k, cy + hh, cx - hw + k, cy + hh]


def pick_font(cands):
    fams = set(tkfont.families())
    for f in cands:
        if f in fams:
            return f
    return "TkDefaultFont"


def format_value(v):
    """Valore interno (in 10^-DECIMALS) → stringa all'italiana, es. 1.234,507"""
    ip, dp = divmod(v, 10 ** DECIMALS)
    s = f"{ip:,}".replace(",", ".")
    return f"{s},{dp:0{DECIMALS}d}" if DECIMALS else s


def parse_value(text):
    """Stringa (es. '3,14', '1.234,5', '2.5') → valore interno, o None se non valida."""
    s = text.strip().replace(" ", "")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    try:
        d = Decimal(s)
    except InvalidOperation:
        return None
    if not d.is_finite() or d < 0:
        return None
    scaled = d.scaleb(DECIMALS)
    if scaled != scaled.to_integral_value():   # troppe cifre decimali
        return None
    v = int(scaled)
    return v if v <= MAX_VALUE else None


# ─────────────────────────── Oggetti ────────────────────────────
class Bead:
    def __init__(self, rod, kind, index, y):
        self.rod = rod          # indice asta (0 = più a sinistra)
        self.kind = kind        # "h" (cielo, vale 5) oppure "e" (terra, vale 1)
        self.index = index      # per le palline di terra: 0 = vicina alla sbarra
        self.y = y
        self.target = y
        self.tag = f"bead_{rod}_{kind}_{index}"


class CanvasButton:
    def __init__(self, app, x, y, w, h, text, color, command):
        cv = app.cv
        self.cv, self.color, self.command = cv, color, command
        self.tag = f"btn_{id(self)}"
        self.shadow = rounded_rect(cv, x - w / 2 + 2, y - h / 2 + 4, x + w / 2 + 2, y + h / 2 + 4,
                                   16, fill=darken(BG_BOTTOM, 0.5), outline="")
        self.body = rounded_rect(cv, x - w / 2, y - h / 2, x + w / 2, y + h / 2, 16,
                                 fill=color, outline=lighten(color, 0.35), width=2, tags=self.tag)
        self.text = cv.create_text(x, y, text=text, fill="#ffffff",
                                   font=(app.font, 13, "bold"), tags=self.tag)
        cv.tag_bind(self.tag, "<Enter>", self._enter)
        cv.tag_bind(self.tag, "<Leave>", self._leave)
        cv.tag_bind(self.tag, "<ButtonPress-1>", self._press)
        cv.tag_bind(self.tag, "<ButtonRelease-1>", self._release)

    def set_text(self, t):
        self.cv.itemconfig(self.text, text=t)

    def _enter(self, _):
        self.cv.itemconfig(self.body, fill=lighten(self.color, 0.18))
        self.cv.config(cursor="hand2")

    def _leave(self, _):
        self.cv.itemconfig(self.body, fill=self.color)
        self.cv.config(cursor="")

    def _press(self, _):
        self.cv.move(self.tag, 0, 2)

    def _release(self, _):
        self.cv.move(self.tag, 0, -2)
        self.command()


# ─────────────────────────── Applicazione ────────────────────────────
class AbacusApp:
    def __init__(self, root):
        self.root = root
        root.title("Abaco")
        root.resizable(False, False)
        root.configure(bg=BG_BOTTOM)

        self.font = pick_font(["Ubuntu", "Cantarell", "Noto Sans", "DejaVu Sans", "Helvetica"])
        self.cv = tk.Canvas(root, width=W, height=H, highlightthickness=0, bg=BG_BOTTOM)
        self.cv.pack()

        self.digits = [0] * RODS
        self.beads = []
        self.badges = []
        self.counting = False
        self.rng = random.Random(7)

        self._draw_background()
        self._draw_title()
        self._draw_frame()
        self._draw_rods_and_beam()
        self._create_beads()
        self._draw_badges()
        self._create_buttons()
        self._bind_events()

        self.refresh()
        self._animate()

    # ── disegno statico ──
    def _draw_background(self):
        cv = self.cv
        for y in range(0, H, 2):
            cv.create_line(0, y, W, y, fill=blend(BG_TOP, BG_BOTTOM, y / H), width=2)
        # stelline decorative
        for _ in range(70):
            x, y = self.rng.uniform(0, W), self.rng.uniform(0, H)
            r = self.rng.choice([0.8, 1, 1.2, 1.6])
            c = blend(BG_TOP, self.rng.choice(ROD_COLORS + ["#ffffff"] * 4), self.rng.uniform(0.25, 0.6))
            cv.create_oval(x - r, y - r, x + r, y + r, fill=c, outline="")

    def _draw_title(self):
        cv = self.cv
        title = "ABACO"
        f = (self.font, 26, "bold")
        step = 34
        x0 = W / 2 - step * (len(title) - 1) / 2
        for i, ch in enumerate(title):
            col = ROD_COLORS[(i * 2) % len(ROD_COLORS)]
            cv.create_text(x0 + i * step + 2, 40 + 3, text=ch, fill=darken(col, 0.6), font=f)
            cv.create_text(x0 + i * step, 40, text=ch, fill=col, font=f)

        # pannello del valore
        rounded_rect(cv, W / 2 - 260, 68, W / 2 + 260, 124, 22,
                     fill="#23264a", outline="#3a3f70", width=2)
        self.value_text = cv.create_text(W / 2, 96, text="0", fill="#ffffff",
                                         font=(self.font, 30, "bold"))

    def _draw_frame(self):
        cv, rng = self.cv, self.rng
        # ombra
        rounded_rect(cv, FX0 + 6, FY0 + 10, FX1 + 6, FY1 + 10, 26, fill="#07080f", outline="")
        # legno
        rounded_rect(cv, FX0, FY0, FX1, FY1, 26, fill=WOOD, outline=WOOD_DARK, width=3)
        # venature
        def grain_h(y0, y1):
            for _ in range(7):
                y = rng.uniform(y0, y1)
                amp, ph, fr = rng.uniform(0.6, 2.2), rng.uniform(0, 6.28), rng.uniform(0.008, 0.02)
                pts = []
                for x in range(int(FX0 + 22), int(FX1 - 22), 12):
                    pts += [x, y + amp * math.sin(x * fr + ph)]
                cv.create_line(pts, smooth=True, width=1,
                               fill=rng.choice([WOOD_DARK, blend(WOOD, WOOD_DARK, 0.5), WOOD_LIGHT]))

        def grain_v(x0, x1):
            for _ in range(4):
                x = rng.uniform(x0, x1)
                amp, ph = rng.uniform(0.5, 1.6), rng.uniform(0, 6.28)
                pts = []
                for y in range(int(FY0 + 24), int(FY1 - 24), 12):
                    pts += [x + amp * math.sin(y * 0.02 + ph), y]
                cv.create_line(pts, smooth=True, width=1,
                               fill=rng.choice([WOOD_DARK, blend(WOOD, WOOD_DARK, 0.5), WOOD_LIGHT]))

        grain_h(FY0 + 5, IY0 - 5)
        grain_h(IY1 + 5, FY1 - 5)
        grain_v(FX0 + 6, IX0 - 6)
        grain_v(IX1 + 6, FX1 - 6)
        # bordo lucido
        rounded_rect(cv, FX0 + 4, FY0 + 4, FX1 - 4, FY1 - 4, 22, fill="", outline=WOOD_LIGHT, width=1)

        # area interna sfumata
        sep = self.comma_x()
        for y in range(IY0, IY1):
            t = (y - IY0) / (IY1 - IY0)
            cv.create_line(IX0, y, sep, y, fill=blend(INNER_TOP, INNER_BOTTOM, t))
            if DECIMALS:
                cv.create_line(sep, y, IX1, y, fill=blend(DEC_TOP, DEC_BOTTOM, t))
        cv.create_rectangle(IX0, IY0, IX1, IY1, outline=WOOD_DARK, width=3)
        cv.create_line(IX0 + 2, IY0 + 3, IX1 - 2, IY0 + 3, fill=darken(INNER_TOP, 0.45), width=3)

        # viti negli angoli
        for (x, y) in [(FX0 + 15, FY0 + 15), (FX1 - 15, FY0 + 15), (FX0 + 15, FY1 - 15), (FX1 - 15, FY1 - 15)]:
            cv.create_oval(x - 6, y - 6, x + 6, y + 6, fill="#d4b483", outline="#6b4a22", width=1)
            cv.create_line(x - 4, y - 4, x + 4, y + 4, fill="#6b4a22", width=2)

        # etichette delle posizioni
        for i, lab in enumerate(PLACE_LABELS):
            cv.create_text(self.rod_x(i), FY0 - 14, text=lab,
                           fill="#c0a8e8" if i >= INT_RODS else "#8a90c0",
                           font=(self.font, 10, "bold"))
        if DECIMALS:
            cv.create_text(sep, FY0 - 16, text=",", fill=COMMA_COLOR, font=(self.font, 22, "bold"))

    def _draw_rods_and_beam(self):
        cv = self.cv
        for i in range(RODS):
            x = self.rod_x(i)
            cv.create_line(x, IY0, x, IY1, fill="#6f7488", width=6)
            cv.create_line(x - 1, IY0, x - 1, IY1, fill="#d9dce8", width=2)
            cv.create_line(x + 2, IY0, x + 2, IY1, fill="#4a4e60", width=1)

        # linea della virgola decimale
        if DECIMALS:
            sep = self.comma_x()
            cv.create_line(sep, IY0 + 2, sep, IY1 - 2, fill=blend(COMMA_COLOR, DEC_BOTTOM, 0.45),
                           width=2, dash=(6, 5))

        # sbarra centrale
        cv.create_rectangle(IX0, BEAM_Y0 + 3, IX1, BEAM_Y1 + 3, fill="#0b0c16", outline="")
        cv.create_rectangle(IX0, BEAM_Y0, IX1, BEAM_Y1, fill=WOOD, outline=WOOD_DARK, width=2)
        cv.create_line(IX0 + 2, BEAM_Y0 + 3, IX1 - 2, BEAM_Y0 + 3, fill=WOOD_LIGHT, width=1)
        # punti di riferimento (unità, migliaia, milioni)
        my = (BEAM_Y0 + BEAM_Y1) / 2
        for i in range(INT_RODS):
            if (INT_RODS - 1 - i) % 3 == 0:
                x = self.rod_x(i)
                cv.create_oval(x - 4, my - 4, x + 4, my + 4, fill="#fff3d6", outline=WOOD_DARK)
        if DECIMALS:  # rombo dorato sulla virgola
            x = self.comma_x()
            cv.create_polygon(x, my - 9, x + 7, my, x, my + 9, x - 7, my,
                              fill=COMMA_COLOR, outline=darken(COMMA_COLOR, 0.5))

    def _draw_bead(self, b):
        cv = self.cv
        cx, cy = self.rod_x(b.rod), b.y
        col = ROD_COLORS[b.rod]
        tags = ("bead", b.tag)
        cv.create_polygon(bead_shape(cx + 3, cy + 5, BW, BH), smooth=True,
                          fill=darken(INNER_BOTTOM, 0.5), outline="", tags=tags)
        cv.create_polygon(bead_shape(cx, cy, BW, BH), smooth=True,
                          fill=darken(col, 0.35), outline=darken(col, 0.55), tags=tags)
        cv.create_polygon(bead_shape(cx, cy - 2, BW - 6, BH - 6), smooth=True,
                          fill=col, outline="", tags=tags)
        cv.create_polygon(bead_shape(cx, cy - BH * 0.17, BW * 0.66, BH * 0.38), smooth=True,
                          fill=lighten(col, 0.35), outline="", tags=tags)
        cv.create_oval(cx - BW * 0.24, cy - BH * 0.36, cx - BW * 0.04, cy - BH * 0.2,
                       fill=lighten(col, 0.8), outline="", tags=tags)

    def _create_beads(self):
        for r in range(RODS):
            b = Bead(r, "h", 0, self.heaven_y(r, False))
            self.beads.append(b)
            for j in range(4):
                self.beads.append(Bead(r, "e", j, self.earth_y(j, False)))
        for b in self.beads:
            self._draw_bead(b)
            self.cv.tag_bind(b.tag, "<Button-1>", lambda e, bb=b: self.on_bead(bb))

    def _draw_badges(self):
        cv = self.cv
        for i in range(RODS):
            x, y = self.rod_x(i), FY1 + 30
            col = ROD_COLORS[i]
            cv.create_oval(x - 17, y - 17 + 3, x + 17, y + 17 + 3, fill="#07080f", outline="")
            cv.create_oval(x - 17, y - 17, x + 17, y + 17, fill=col, outline=lighten(col, 0.4), width=2)
            t = cv.create_text(x, y, text="0", fill=darken(col, 0.7), font=(self.font, 15, "bold"))
            self.badges.append(t)
        if DECIMALS:
            x, y = self.comma_x(), FY1 + 30
            cv.create_text(x, y + 6, text=",", fill=COMMA_COLOR, font=(self.font, 26, "bold"))

    def _create_buttons(self):
        y, w, h, gap = 640, 170, 46, 22
        specs = [
            ("⟲  Azzera", "#e63946", self.reset),
            ("✦  Casuale", "#8338ec", self.randomize),
            ("✎  Imposta…", "#3a86ff", self.ask_value),
            ("▶  Conta", "#2a9d8f", self.toggle_count),
        ]
        total = len(specs) * w + (len(specs) - 1) * gap
        x = W / 2 - total / 2 + w / 2
        self.buttons = []
        for text, col, cmd in specs:
            self.buttons.append(CanvasButton(self, x, y, w, h, text, col, cmd))
            x += w + gap
        self.count_btn = self.buttons[-1]
        self.cv.create_text(W / 2, H - 16, fill="#6c7199", font=(self.font, 10),
                            text="Clicca le palline  ·  rotella del mouse su un'asta: +1 / −1 in quella posizione  ·  "
                                 "Spazio conta (+0,1)  ·  R casuale  ·  Esc azzera")

    def _bind_events(self):
        cv, root = self.cv, self.root
        cv.tag_bind("bead", "<Enter>", lambda e: cv.config(cursor="hand2"))
        cv.tag_bind("bead", "<Leave>", lambda e: cv.config(cursor=""))
        cv.bind("<Button-4>", lambda e: self.on_wheel(e, +1))
        cv.bind("<Button-5>", lambda e: self.on_wheel(e, -1))
        cv.bind("<MouseWheel>", lambda e: self.on_wheel(e, 1 if e.delta > 0 else -1))
        root.bind("<space>", lambda e: self.toggle_count())
        root.bind("<Escape>", lambda e: self.reset())
        root.bind("<r>", lambda e: self.randomize())
        root.bind("<R>", lambda e: self.randomize())
        root.bind("<i>", lambda e: self.ask_value())

    # ── geometria ──
    @staticmethod
    def rod_x(i):
        return IX0 + SPACING * (i + 0.5)

    @staticmethod
    def comma_x():
        return IX0 + SPACING * INT_RODS

    @staticmethod
    def heaven_y(_rod, active):
        return BEAM_Y0 - BH / 2 - 1 if active else IY0 + BH / 2 + 3

    @staticmethod
    def earth_y(j, active):
        if active:
            return BEAM_Y1 + BH / 2 + 1 + j * BH
        return IY1 - BH / 2 - 3 - (3 - j) * BH

    # ── logica ──
    @property
    def value(self):
        v = 0
        for d in self.digits:
            v = v * 10 + d
        return v

    def set_value(self, v):
        v = max(0, min(MAX_VALUE, int(v)))
        self.digits = [int(c) for c in str(v).zfill(RODS)]
        self.refresh()

    def refresh(self):
        for b in self.beads:
            d = self.digits[b.rod]
            if b.kind == "h":
                b.target = self.heaven_y(b.rod, d >= 5)
            else:
                b.target = self.earth_y(b.index, b.index < d % 5)
        for i, t in enumerate(self.badges):
            self.cv.itemconfig(t, text=str(self.digits[i]))
        self.cv.itemconfig(self.value_text, text=format_value(self.value))

    def on_bead(self, b):
        d = self.digits[b.rod]
        if b.kind == "h":
            d = d - 5 if d >= 5 else d + 5
        else:
            ones = d % 5
            ones = b.index if b.index < ones else b.index + 1
            d = (d // 5) * 5 + ones
        self.digits[b.rod] = d
        self.refresh()

    def on_wheel(self, e, direction):
        if not (IX0 <= e.x <= IX1 and FY0 <= e.y <= FY1 + 50):
            return
        rod = int((e.x - IX0) // SPACING)
        rod = max(0, min(RODS - 1, rod))
        self.set_value(self.value + direction * 10 ** (RODS - 1 - rod))

    def reset(self):
        self._stop_count()
        self.set_value(0)

    def randomize(self):
        self._stop_count()
        self.set_value(random.randint(0, MAX_VALUE))

    def ask_value(self):
        self._stop_count()
        prompt = f"Inserisci un numero (0 – {format_value(MAX_VALUE)}),\nanche con la virgola, es. 3,14:"
        while True:
            s = simpledialog.askstring("Imposta numero", prompt, parent=self.root)
            if s is None:
                return
            v = parse_value(s)
            if v is not None:
                self.set_value(v)
                return
            prompt = f"Numero non valido. Usa cifre e una virgola (max {DECIMALS} decimali),\n" \
                     f"tra 0 e {format_value(MAX_VALUE)}:"

    def toggle_count(self):
        if self.counting:
            self._stop_count()
        else:
            self.counting = True
            self.count_btn.set_text("⏸  Ferma")
            self._count_step()

    def _stop_count(self):
        self.counting = False
        self.count_btn.set_text("▶  Conta")

    def _count_step(self):
        if not self.counting:
            return
        if self.value >= MAX_VALUE:
            self._stop_count()
            return
        self.set_value(self.value + COUNT_STEP)
        self.root.after(380, self._count_step)

    # ── animazione ──
    def _animate(self):
        for b in self.beads:
            diff = b.target - b.y
            if diff:
                dy = diff if abs(diff) < 0.6 else diff * 0.25
                self.cv.move(b.tag, 0, dy)
                b.y += dy
        self.root.after(16, self._animate)


def main():
    root = tk.Tk()
    root.update_idletasks()
    sx = (root.winfo_screenwidth() - W) // 2
    sy = max(0, (root.winfo_screenheight() - H) // 2 - 20)
    root.geometry(f"{W}x{H}+{sx}+{sy}")
    AbacusApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
