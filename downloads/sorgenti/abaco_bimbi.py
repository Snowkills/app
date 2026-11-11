#!/usr/bin/env python3
"""
L'abaco delle palline – per imparare il sistema decimale.

Quattro aste: migliaia (k), centinaia (h), decine (da), unità (u).
Su ogni asta ci stanno fino a 10 palline: quando arriva la decima,
le 10 palline si uniscono e diventano UNA pallina dell'asta a sinistra.
Quando si toglie una pallina da un'asta vuota, succede il contrario:
una pallina dell'asta a sinistra si "rompe" in 10 palline.

Comandi:
  • clic su un'asta (o sul suo "+")   → aggiunge una pallina
  • clic destro su un'asta (o "−")    → toglie una pallina
  • ▶ Conta: aggiunge un'unità alla volta, da solo
  • tastiera: + / ↑ aggiunge un'unità · − / ↓ toglie un'unità · Spazio conta · Esc azzera
"""

import math
import random
import time
import tkinter as tk
import tkinter.font as tkfont
from collections import deque
from tkinter import simpledialog

# ─────────────────────────── Configurazione ────────────────────────────
W, H = 1000, 760
MAX_VALUE = 9999

LETTERS = ["k", "h", "da", "u"]
PLURAL = ["migliaia", "centinaia", "decine", "unità"]
SINGULAR = ["migliaio", "centinaio", "decina", "unità"]
COLORS = ["#ff9f1c",   # migliaia: arancio
          "#2ec4b6",   # centinaia: verde acqua
          "#ff5e7e",   # decine: rosso/rosa
          "#4895ef"]   # unità: blu

BASE_X0, BASE_X1 = 90, W - 90
SPACING = (BASE_X1 - BASE_X0) / 4
ROD_TOP, BASE_TOP, BASE_BOTTOM = 190, 540, 588
GATHER_Y = 168                    # dove le palline si uniscono
BW, BH = 88, 30                   # dimensioni pallina

BG_TOP, BG_BOTTOM = "#dff0ff", "#fff4e2"
INK = "#2b2d42"
WOOD, WOOD_DARK, WOOD_LIGHT = "#c68b59", "#8a5a33", "#e2b27f"

SPEED = 1.0   # >1 più lento, <1 più veloce


# ─────────────────────────── Utilità ────────────────────────────
def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def blend(c1, c2, t):
    a, b = _rgb(c1), _rgb(c2)
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(a[i] + (b[i] - a[i]) * t))) for i in range(3))


def lighten(c, t):
    return blend(c, "#ffffff", t)


def darken(c, t):
    return blend(c, "#000000", t)


def rounded_rect(cv, x0, y0, x1, y1, r, **kw):
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return cv.create_polygon(pts, smooth=True, **kw)


def bead_shape(cx, cy, w, h):
    hw, hh, k = w / 2, h / 2 * 1.2, w * 0.2
    return [cx - hw, cy, cx - hw + k, cy - hh, cx + hw - k, cy - hh,
            cx + hw, cy, cx + hw - k, cy + hh, cx - hw + k, cy + hh]


def pick_font(cands):
    fams = set(tkfont.families())
    return next((f for f in cands if f in fams), "TkDefaultFont")


def rod_x(i):
    return BASE_X0 + SPACING * (i + 0.5)


def slot_y(k):
    """Centro della k-esima pallina dal basso."""
    return BASE_TOP - BH / 2 - 1 - k * BH


# Funzioni di easing
def ease_linear(t):
    return t


def ease_out(t):
    return 1 - (1 - t) ** 3


def ease_in(t):
    return t ** 3


def ease_in_out(t):
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_back(t):
    c1 = 1.70158
    return 1 + (c1 + 1) * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_bounce(t):
    n, d = 7.5625, 2.75
    if t < 1 / d:
        return n * t * t
    if t < 2 / d:
        t -= 1.5 / d
        return n * t * t + 0.75
    if t < 2.5 / d:
        t -= 2.25 / d
        return n * t * t + 0.9375
    t -= 2.625 / d
    return n * t * t + 0.984375


# ─────────────────────────── Pallina animata ────────────────────────────
class Bead:
    def __init__(self, x, y, s, color):
        self.x, self.y, self.s, self.color = x, y, s, color
        self.segs = deque()

    def go(self, x=None, y=None, s=None, dur=0.4, ease=ease_out, delay=0.0, ctrl=None, then=None):
        """Accoda un movimento. None = resta com'è. ctrl = punto di controllo per un arco."""
        self.segs.append(dict(to=(x, y, s), dur=dur * SPEED, ease=ease,
                              delay=delay * SPEED, ctrl=ctrl, then=then, t0=None, frm=None))
        return self

    @property
    def moving(self):
        return bool(self.segs)

    def update(self, now):
        while self.segs:
            g = self.segs[0]
            if g["t0"] is None:
                g["t0"] = now + g["delay"]
            if now < g["t0"]:
                return
            if g["frm"] is None:
                g["frm"] = (self.x, self.y, self.s)
            fx, fy, fs = g["frm"]
            tx, ty, ts = (v if v is not None else f for v, f in zip(g["to"], g["frm"]))
            t = 1.0 if g["dur"] <= 0 else min(1.0, (now - g["t0"]) / g["dur"])
            e = g["ease"](t)
            if g["ctrl"]:
                cx, cy = g["ctrl"]
                u = 1 - e
                self.x = u * u * fx + 2 * u * e * cx + e * e * tx
                self.y = u * u * fy + 2 * u * e * cy + e * e * ty
            else:
                self.x = fx + (tx - fx) * e
                self.y = fy + (ty - fy) * e
            self.s = fs + (ts - fs) * e
            if t < 1.0:
                return
            self.x, self.y, self.s = tx, ty, ts
            self.segs.popleft()
            if g["then"]:
                g["then"]()


# ─────────────────────────── Pulsanti disegnati ────────────────────────────
class CanvasButton:
    def __init__(self, app, x, y, w, h, text, color, command, round_=False, font_size=14):
        cv = self.cv = app.cv
        self.color, self.command = color, command
        self.tag = f"btn_{id(self)}"
        if round_:
            r = w / 2
            cv.create_oval(x - r + 1, y - r + 4, x + r + 1, y + r + 4, fill=darken(BG_BOTTOM, 0.18), outline="")
            self.body = cv.create_oval(x - r, y - r, x + r, y + r, fill=color,
                                       outline=lighten(color, 0.4), width=2, tags=self.tag)
        else:
            rounded_rect(cv, x - w / 2 + 1, y - h / 2 + 4, x + w / 2 + 1, y + h / 2 + 4, 18,
                         fill=darken(BG_BOTTOM, 0.18), outline="")
            self.body = rounded_rect(cv, x - w / 2, y - h / 2, x + w / 2, y + h / 2, 18,
                                     fill=color, outline=lighten(color, 0.4), width=2, tags=self.tag)
        self.text = cv.create_text(x, y - (2 if round_ else 0), text=text, fill="#ffffff",
                                   font=(app.font, font_size, "bold"), tags=self.tag)
        cv.tag_bind(self.tag, "<Enter>", lambda e: (cv.itemconfig(self.body, fill=lighten(color, 0.2)),
                                                    cv.config(cursor="hand2")))
        cv.tag_bind(self.tag, "<Leave>", lambda e: (cv.itemconfig(self.body, fill=color),
                                                    cv.config(cursor="")))
        cv.tag_bind(self.tag, "<ButtonPress-1>", lambda e: cv.move(self.tag, 0, 2))
        cv.tag_bind(self.tag, "<ButtonRelease-1>", self._release)

    def _release(self, _):
        self.cv.move(self.tag, 0, -2)
        self.command()
        return "break"

    def set_text(self, t):
        self.cv.itemconfig(self.text, text=t)


# ─────────────────────────── Applicazione ────────────────────────────
class KidsAbacus:
    def __init__(self, root):
        self.root = root
        root.title("L'abaco delle palline")
        root.resizable(False, False)
        self.font = pick_font(["Comic Neue", "Comic Sans MS", "Ubuntu", "Cantarell",
                               "Noto Sans", "DejaVu Sans", "Helvetica"])
        self.cv = tk.Canvas(root, width=W, height=H, highlightthickness=0, bg=BG_BOTTOM)
        self.cv.pack()

        self.value = 0                    # numero "vero"
        self.counts = [0, 0, 0, 0]        # palline posate su ogni asta (anche 10, durante il cambio)
        self.stacks = [[], [], [], []]    # palline disegnate su ogni asta
        self.flyers = []                  # palline in volo fra le aste
        self.particles = []
        self.queue = deque()
        self.busy = False
        self.counting = False
        self.count_job = None
        self.msg_job = None
        self.dirty = True
        self.last = time.monotonic()

        self._draw_static()
        self._bind_events()
        self._update_header()
        self._update_badges()
        self._tick()

    # ═════════════ disegno statico ═════════════
    def _draw_static(self):
        cv = self.cv
        rng = random.Random(3)
        for y in range(0, H, 2):
            cv.create_line(0, y, W, y, fill=blend(BG_TOP, BG_BOTTOM, y / H), width=2)
        # nuvolette
        for cx, cy, sc in [(110, 70, 1.0), (880, 60, 1.2), (930, 260, 0.7), (60, 300, 0.8)]:
            for dx, dy, r in [(-26, 6, 18), (0, -4, 24), (26, 6, 18), (0, 10, 18)]:
                r *= sc
                cv.create_oval(cx + dx * sc - r, cy + dy * sc - r, cx + dx * sc + r, cy + dy * sc + r,
                               fill="#ffffff", outline="")

        # titolo
        title = "L'abaco delle palline"
        f = (self.font, 24, "bold")
        fnt = tkfont.Font(family=self.font, size=24, weight="bold")
        x = W / 2 - fnt.measure(title) / 2
        palette = COLORS[::-1] + ["#9b5de5"]
        ci = 0
        for ch in title:
            w = fnt.measure(ch)
            if ch.strip():
                col = palette[ci % len(palette)]
                ci += 1
                cv.create_text(x + w / 2 + 2, 30 + 2, text=ch, fill=darken(col, 0.35), font=f)
                cv.create_text(x + w / 2, 30, text=ch, fill=col, font=f)
            x += w

        # colonne colorate
        for i in range(4):
            x, col = rod_x(i), COLORS[i]
            rounded_rect(cv, x - SPACING / 2 + 10, ROD_TOP - 30, x + SPACING / 2 - 10, BASE_TOP + 10, 24,
                         fill=blend(col, "#ffffff", 0.86), outline=blend(col, "#ffffff", 0.6), width=2,
                         tags=("column", f"col{i}"))

        # aste
        for i in range(4):
            x = rod_x(i)
            cv.create_line(x + 2, ROD_TOP, x + 2, BASE_TOP, fill=darken(WOOD, 0.3), width=8, capstyle="round")
            cv.create_line(x, ROD_TOP, x, BASE_TOP, fill=WOOD, width=8, capstyle="round")
            cv.create_line(x - 2, ROD_TOP + 3, x - 2, BASE_TOP, fill=WOOD_LIGHT, width=2)
            cv.create_oval(x - 8, ROD_TOP - 8, x + 8, ROD_TOP + 8, fill=COLORS[i], outline=darken(COLORS[i], 0.3))

        # base di legno
        rounded_rect(cv, BASE_X0 + 5, BASE_TOP + 8, BASE_X1 + 5, BASE_BOTTOM + 8, 18,
                     fill=darken(BG_BOTTOM, 0.2), outline="")
        rounded_rect(cv, BASE_X0, BASE_TOP, BASE_X1, BASE_BOTTOM, 18, fill=WOOD, outline=WOOD_DARK, width=3)
        for _ in range(6):
            y = rng.uniform(BASE_TOP + 8, BASE_BOTTOM - 8)
            ph, amp = rng.uniform(0, 6.3), rng.uniform(0.6, 1.8)
            pts = []
            for xx in range(BASE_X0 + 20, BASE_X1 - 20, 12):
                pts += [xx, y + amp * math.sin(xx * 0.015 + ph)]
            cv.create_line(pts, smooth=True, fill=rng.choice([WOOD_DARK, WOOD_LIGHT]))

        # contatori sulla base
        self.badge_text = []
        self.badge_circle = []
        for i in range(4):
            x, y = rod_x(i), (BASE_TOP + BASE_BOTTOM) / 2
            c = cv.create_oval(x - 19, y - 19, x + 19, y + 19, fill="#fffaf0", outline=COLORS[i], width=3)
            t = cv.create_text(x, y, text="0", fill=darken(COLORS[i], 0.25), font=(self.font, 16, "bold"))
            self.badge_circle.append(c)
            self.badge_text.append(t)

        # etichette + pulsanti − / +
        for i in range(4):
            x, col = rod_x(i), COLORS[i]
            cv.create_text(x, 620, text=LETTERS[i], fill=col, font=(self.font, 28, "bold"))
            cv.create_text(x, 654, text=PLURAL[i], fill=darken(col, 0.25), font=(self.font, 13, "bold"))
            CanvasButton(self, x - 64, 624, 44, 44, "−", col, lambda i=i: self.enqueue(self.act_remove, i),
                         round_=True, font_size=20)
            CanvasButton(self, x + 64, 624, 44, 44, "+", col, lambda i=i: self.enqueue(self.act_add, i),
                         round_=True, font_size=20)

        # pulsanti generali
        y, w, h, gap = 705, 190, 46, 24
        specs = [("⟲  Azzera", "#e63946", self.reset),
                 ("▶  Conta", "#2a9d8f", self.toggle_count),
                 ("✎  Scegli numero", "#8338ec", self.ask_number)]
        total = len(specs) * w + (len(specs) - 1) * gap
        x = W / 2 - total / 2 + w / 2
        btns = []
        for text, col, cmd in specs:
            btns.append(CanvasButton(self, x, y, w, h, text, col, cmd))
            x += w + gap
        self.count_btn = btns[1]

        cv.create_text(W / 2, H - 14, fill="#8d8fa8", font=(self.font, 10),
                       text="Clic su un'asta = aggiungi una pallina   ·   clic destro = togli   ·   "
                            "↑ / ↓ = unità   ·   Spazio = conta")

    # ═════════════ parti che cambiano ═════════════
    def _update_header(self):
        cv = self.cv
        cv.delete("hdr")
        digits = f"{self.value:04d}"
        bw, gap = 58, 8
        total = 4 * bw + 3 * gap
        x0 = W / 2 - total / 2
        rounded_rect(cv, x0 - 16, 52, x0 + total + 16, 116, 20, fill="#ffffff",
                     outline="#d6dcef", width=2, tags="hdr")
        leading = True
        for i, d in enumerate(digits):
            if d != "0" or i == 3:
                leading = False
            col = COLORS[i]
            x = x0 + i * (bw + gap) + bw / 2
            fill = blend(col, "#ffffff", 0.7) if leading else col
            cv.create_text(x, 78, text=d, fill=fill, font=(self.font, 30, "bold"), tags="hdr")
            cv.create_text(x, 104, text=LETTERS[i], fill=blend(col, "#ffffff", 0.3),
                           font=(self.font, 11, "bold"), tags="hdr")

    def _update_badges(self):
        for i in range(4):
            n = self.counts[i]
            full = n >= 10
            self.cv.itemconfig(self.badge_text[i], text=str(n),
                               fill="#ffffff" if full else darken(COLORS[i], 0.25))
            self.cv.itemconfig(self.badge_circle[i], fill=COLORS[i] if full else "#fffaf0")

    def show_message(self, text, color, ms=2800):
        cv = self.cv
        cv.delete("msg")
        if self.msg_job:
            self.root.after_cancel(self.msg_job)
        fnt = tkfont.Font(family=self.font, size=16, weight="bold")
        w = fnt.measure(text) + 44
        rounded_rect(cv, W / 2 - w / 2, 124, W / 2 + w / 2, 156, 16, fill=color,
                     outline=darken(color, 0.2), width=2, tags="msg")
        cv.create_text(W / 2, 140, text=text, fill="#ffffff", font=(self.font, 16, "bold"), tags="msg")
        self.msg_job = self.root.after(int(ms * SPEED), lambda: cv.delete("msg"))

    def burst(self, x, y, colors, n=18):
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            sp = random.uniform(120, 300)
            self.particles.append([x, y, math.cos(a) * sp, math.sin(a) * sp - 80,
                                   random.choice(colors), 0.7])

    # ═════════════ coda delle azioni ═════════════
    def enqueue(self, fn, *args):
        if len(self.queue) < 6:
            self.queue.append((fn, args))
            self._run_next()

    def _run_next(self):
        if self.busy or not self.queue:
            return
        fn, args = self.queue.popleft()
        self.busy = True
        fn(*args, self._done)

    def _done(self):
        self.busy = False
        if self.queue:
            self.root.after(60, self._run_next)
        elif self.counting:
            self.count_job = self.root.after(int(450 * SPEED), self._count_tick)

    def later(self, ms, fn):
        self.root.after(int(ms * SPEED), fn)

    # ═════════════ azioni ═════════════
    def act_add(self, i, done):
        step = 10 ** (3 - i)
        if self.value + step > MAX_VALUE:
            self._stop_count()
            self.show_message(f"{MAX_VALUE} è il numero più grande di questo abaco!", "#e63946")
            done()
            return
        self.value += step
        self._update_header()
        stack = self.stacks[i]
        b = Bead(rod_x(i), ROD_TOP - 50, 0.4, COLORS[i])
        stack.append(b)

        def landed():
            self.counts[i] += 1
            self._update_badges()
            if self.counts[i] == 10:
                self.later(250, lambda: self._carry(i, done))
            else:
                done()

        b.go(y=slot_y(len(stack) - 1), s=1, dur=0.5, ease=ease_bounce, then=landed)

    def _carry(self, i, done):
        """10 palline sull'asta i diventano 1 pallina sull'asta i-1."""
        self.show_message(f"10 {PLURAL[i]} diventano 1 {SINGULAR[i - 1]}!", COLORS[i - 1], 3400)
        stack = self.stacks[i]
        gx, gy = rod_x(i), GATHER_Y
        # 1) le palline "saltellano"
        for k, b in enumerate(stack):
            b.go(s=1.18, dur=0.2, delay=k * 0.04).go(s=1.0, dur=0.2)

        # 2) si raccolgono in un punto
        def gather():
            arrived = [0]

            def one_arrived():
                arrived[0] += 1
                if arrived[0] == len(stack):
                    merge()

            for k, b in enumerate(reversed(stack)):
                b.go(gx, gy, s=0.55, dur=0.6, ease=ease_in_out, delay=k * 0.08, then=one_arrived)

        # 3) diventano una pallina sola, che vola sull'asta a sinistra
        def merge():
            stack.clear()
            self.counts[i] = 0
            self._update_badges()
            self.burst(gx, gy, [COLORS[i], COLORS[i - 1], "#ffd23f"])
            nb = Bead(gx, gy, 0.2, COLORS[i - 1])
            self.flyers.append(nb)
            tx = rod_x(i - 1)
            nb.go(s=1.45, dur=0.4, ease=ease_back)
            nb.go(dur=0.35)                                   # pausa per farla notare
            nb.go(tx, gy, s=1.0, dur=0.9, ease=ease_in_out, ctrl=((gx + tx) / 2, gy - 40), then=drop)
            self._new_bead = nb

        def drop():
            nb = self._new_bead
            self.flyers.remove(nb)
            target = self.stacks[i - 1]
            target.append(nb)

            def landed():
                self.counts[i - 1] += 1
                self._update_badges()
                if self.counts[i - 1] == 10:
                    self.later(300, lambda: self._carry(i - 1, done))
                else:
                    done()

            nb.go(y=slot_y(len(target) - 1), dur=0.55, ease=ease_bounce, then=landed)

        self.later(1000, gather)

    def act_remove(self, i, done):
        step = 10 ** (3 - i)
        if self.value - step < 0:
            msg = ("Non ci sono palline da togliere!" if self.value == 0
                   else f"Non ci sono abbastanza palline per togliere 1 {SINGULAR[i]}!")
            self.show_message(msg, "#e63946")
            done()
            return
        self.value -= step
        self._update_header()
        if self.counts[i] > 0:
            self._take(i, done)
        else:
            self._borrow(i, lambda: self._take(i, done))

    def _take(self, i, done):
        b = self.stacks[i].pop()
        self.counts[i] -= 1
        self._update_badges()
        self.flyers.append(b)

        def gone():
            self.flyers.remove(b)
            self.burst(b.x, b.y, [COLORS[i]], n=8)
            done()

        b.go(y=ROD_TOP - 40, s=0.0, dur=0.5, ease=ease_in, then=gone)

    def _borrow(self, i, cont):
        """1 pallina dell'asta i-1 si rompe in 10 palline sull'asta i."""
        if self.counts[i - 1] == 0:
            self._borrow(i - 1, lambda: self._borrow(i, cont))
            return
        self.show_message(f"1 {SINGULAR[i - 1]} diventa 10 {PLURAL[i]}!", COLORS[i], 3400)
        b = self.stacks[i - 1].pop()
        self.counts[i - 1] -= 1
        self._update_badges()
        self.flyers.append(b)
        fx, tx, gy = rod_x(i - 1), rod_x(i), GATHER_Y

        def split():
            self.flyers.remove(b)
            self.burst(tx, gy, [COLORS[i - 1], COLORS[i], "#ffd23f"])
            stack = self.stacks[i]

            def landed():
                self.counts[i] += 1
                self._update_badges()
                if self.counts[i] == 10:
                    self.later(400, cont)

            for k in range(10):
                nb = Bead(tx, gy, 0.5, COLORS[i])
                stack.append(nb)
                nb.go(y=slot_y(k), s=1.0, dur=0.55, ease=ease_bounce, delay=0.15 + k * 0.12, then=landed)

        b.go(s=1.2, dur=0.2).go(s=1.0, dur=0.2)
        b.go(y=gy, dur=0.5, ease=ease_in_out)
        b.go(tx, gy, dur=0.9, ease=ease_in_out, ctrl=((fx + tx) / 2, gy - 40))
        b.go(s=1.5, dur=0.35, ease=ease_back)
        b.go(dur=0.25, then=split)

    def act_reset(self, done):
        everything = [b for st in self.stacks for b in st]
        for st in self.stacks:
            st.clear()
        self.counts = [0, 0, 0, 0]
        self.value = 0
        self._update_header()
        self._update_badges()
        for b in everything:
            self.flyers.append(b)
            b.go(y=ROD_TOP - 40, s=0.0, dur=0.45, ease=ease_in, delay=random.uniform(0, 0.3),
                 then=lambda b=b: self.flyers.remove(b))
        self.later(800 if everything else 0, done)

    def act_set(self, n, done):
        self.value = n
        self._update_header()
        digits = [int(c) for c in f"{n:04d}"]
        pending = [sum(digits)]
        if not pending[0]:
            done()
            return

        def landed(i):
            self.counts[i] += 1
            self._update_badges()
            pending[0] -= 1
            if pending[0] == 0:
                done()

        for i, d in enumerate(digits):
            for k in range(d):
                b = Bead(rod_x(i), ROD_TOP - 50, 0.4, COLORS[i])
                self.stacks[i].append(b)
                b.go(y=slot_y(k), s=1.0, dur=0.5, ease=ease_bounce, delay=i * 0.25 + k * 0.1,
                     then=lambda i=i: landed(i))

    # ═════════════ comandi ═════════════
    def reset(self):
        self._stop_count()
        self.queue.clear()
        self.enqueue(self.act_reset)

    def ask_number(self):
        self._stop_count()
        n = simpledialog.askinteger("Scegli un numero", f"Scrivi un numero da 0 a {MAX_VALUE}:",
                                    parent=self.root, minvalue=0, maxvalue=MAX_VALUE)
        if n is not None:
            self.queue.clear()
            self.enqueue(self.act_reset)
            self.enqueue(self.act_set, n)

    def toggle_count(self):
        if self.counting:
            self._stop_count()
        else:
            self.counting = True
            self.count_btn.set_text("⏸  Ferma")
            if not self.busy and not self.queue:
                self._count_tick()

    def _stop_count(self):
        self.counting = False
        self.count_btn.set_text("▶  Conta")
        if self.count_job:
            self.root.after_cancel(self.count_job)
            self.count_job = None

    def _count_tick(self):
        self.count_job = None
        if not self.counting:
            return
        if self.value >= MAX_VALUE:
            self._stop_count()
            return
        self.enqueue(self.act_add, 3)

    def _rod_at(self, x, y):
        if not (ROD_TOP - 30 <= y <= BASE_BOTTOM and BASE_X0 <= x <= BASE_X1):
            return None
        return min(3, int((x - BASE_X0) // SPACING))

    def _bind_events(self):
        cv, root = self.cv, self.root

        def left(e):
            i = self._rod_at(e.x, e.y)
            if i is not None:
                self.enqueue(self.act_add, i)

        def right(e):
            i = self._rod_at(e.x, e.y)
            if i is not None:
                self.enqueue(self.act_remove, i)

        cv.bind("<Button-1>", left)
        cv.bind("<Button-3>", right)
        for key in ("<plus>", "<KP_Add>", "<Up>"):
            root.bind(key, lambda e: self.enqueue(self.act_add, 3))
        for key in ("<minus>", "<KP_Subtract>", "<Down>"):
            root.bind(key, lambda e: self.enqueue(self.act_remove, 3))
        root.bind("<space>", lambda e: self.toggle_count())
        root.bind("<Escape>", lambda e: self.reset())

    # ═════════════ animazione ═════════════
    def _draw_bead(self, b):
        if b.s <= 0.03:
            return
        cv, col = self.cv, b.color
        w, h, x, y = BW * b.s, BH * b.s, b.x, b.y
        cv.create_polygon(bead_shape(x + 3, y + 4, w, h), smooth=True,
                          fill=blend(col, BG_BOTTOM, 0.55), outline="", tags="dyn")
        cv.create_polygon(bead_shape(x, y, w, h), smooth=True,
                          fill=darken(col, 0.25), outline=darken(col, 0.45), tags="dyn")
        cv.create_polygon(bead_shape(x, y - 2 * b.s, w - 6 * b.s, h - 6 * b.s), smooth=True,
                          fill=col, outline="", tags="dyn")
        cv.create_polygon(bead_shape(x, y - h * 0.17, w * 0.64, h * 0.36), smooth=True,
                          fill=lighten(col, 0.35), outline="", tags="dyn")
        cv.create_oval(x - w * 0.24, y - h * 0.36, x - w * 0.05, y - h * 0.2,
                       fill=lighten(col, 0.8), outline="", tags="dyn")

    def _tick(self):
        now = time.monotonic()
        dt = min(0.05, now - self.last)
        self.last = now
        active = self.dirty or bool(self.particles)
        for b in [b for st in self.stacks for b in st] + list(self.flyers):
            if b.moving:
                active = True
                b.update(now)
        if active:
            self.dirty = False
            cv = self.cv
            cv.delete("dyn")
            for st in self.stacks:
                for b in st:
                    self._draw_bead(b)
            for b in self.flyers:
                self._draw_bead(b)
            alive = []
            for p in self.particles:
                p[0] += p[2] * dt
                p[1] += p[3] * dt
                p[3] += 500 * dt
                p[5] -= dt
                if p[5] > 0:
                    r = 6 * p[5] / 0.7
                    cv.create_oval(p[0] - r, p[1] - r, p[0] + r, p[1] + r, fill=p[4], outline="", tags="dyn")
                    alive.append(p)
            self.particles = alive
            self.dirty = True if self.flyers or alive else False
        self.root.after(16, self._tick)


def main():
    root = tk.Tk()
    root.update_idletasks()
    sx = (root.winfo_screenwidth() - W) // 2
    sy = max(0, (root.winfo_screenheight() - H) // 2 - 30)
    root.geometry(f"{W}x{H}+{sx}+{sy}")
    KidsAbacus(root)
    root.mainloop()


if __name__ == "__main__":
    main()
