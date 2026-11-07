
import math
import os
import queue
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk

import core
from algos import projectSignup as cp

TEAM = [("24K-3037", "Daneya Shafiq"),
        ("24K-3010", "Erfa Kashif"),
        ("24K-3092", "Anshrah Shafique")]

# ---------------------------------------------------------------- palette
C = {
    "bg": "#eef1f6", "card": "#ffffff", "border": "#d9dee8",
    "side": "#1b2333", "side2": "#252f44", "side_text": "#c9d2e3", "side_muted": "#7f8aa3",
    "text": "#1d2433", "muted": "#667085",
    "accent": "#4f46e5", "accent_dark": "#3730a3", "accent_soft": "#e7e6fd",
    "green": "#16a34a", "green_soft": "#dcfce7",
    "red": "#dc2626", "red_soft": "#fee2e2",
    "amber": "#d97706", "amber_soft": "#fdf0d5",
    "blue": "#2563eb", "blue_soft": "#dbeafe",
    "teal": "#0d9488", "teal_soft": "#ccfbf1",
    "point": "#64748b", "grid": "#e8ebf1",
}

CP_INFO = ("Closest Pair of Points", "O(n log n)",
           "Sort by x, split at the median, solve both halves, then check a strip of "
           "width 2δ around the dividing line.")
KS_INFO = ("Karatsuba Integer Multiplication", "O(n^1.585)",
           "Split each number into high/low halves and use 3 recursive products "
           "(instead of 4): w = a·c, y = b·d, z = (a+b)(c+d) − w − y.")


def pick_font(root, candidates, fallback):
    families = set(tkfont.families(root))
    for name in candidates:
        if name in families:
            return name
    return fallback


def short_num(value, keep=22):
    s = str(value)
    if len(s) <= keep:
        return s
    return f"{s[:keep // 2]}…{s[-(keep // 2 - 2):]}"


def fmt_ms(seconds):
    ms = seconds * 1000
    if ms < 1:
        return f"{ms * 1000:.0f} µs"
    return f"{ms:.2f} ms"


# =========================================================================
#  Small widgets
# =========================================================================
class Card(tk.Frame):
    def __init__(self, master, title=None, fonts=None, **kw):
        super().__init__(master, bg=C["card"], highlightthickness=1,
                         highlightbackground=C["border"], **kw)
        if title:
            tk.Label(self, text=title.upper(), bg=C["card"], fg=C["muted"],
                     font=fonts["small_bold"]).pack(anchor="w", padx=14, pady=(10, 2))
        self.body = tk.Frame(self, bg=C["card"])
        self.body.pack(fill="both", expand=True, padx=14, pady=(2, 12))


class Stat(tk.Frame):
    """Label + value tile."""

    def __init__(self, master, label, fonts, color=None):
        super().__init__(master, bg=C["card"])
        tk.Label(self, text=label, bg=C["card"], fg=C["muted"],
                 font=fonts["small"]).pack(anchor="w")
        self.var = tk.StringVar(value="—")
        self.lbl = tk.Label(self, textvariable=self.var, bg=C["card"],
                            fg=color or C["text"], font=fonts["stat"], anchor="w",
                            justify="left")
        self.lbl.pack(anchor="w", fill="x")

    def set(self, text, color=None):
        self.var.set(text)
        if color:
            self.lbl.configure(fg=color)


def flat_button(master, text, command, kind="accent", fonts=None, **kw):
    colors = {
        "accent": (C["accent"], "#ffffff", C["accent_dark"]),
        "soft": (C["accent_soft"], C["accent_dark"], "#d6d4fb"),
        "ghost": (C["side2"], C["side_text"], "#33405c"),
        "plain": ("#f1f3f8", C["text"], "#e2e6ef"),
    }[kind]
    b = tk.Button(master, text=text, command=command, bg=colors[0], fg=colors[1],
                  activebackground=colors[2], activeforeground=colors[1],
                  relief="flat", bd=0, cursor="hand2", font=fonts["button"],
                  padx=12, pady=7, highlightthickness=0, **kw)
    b.bind("<Enter>", lambda e: b.configure(bg=colors[2]) if str(b["state"]) != "disabled" else None)
    b.bind("<Leave>", lambda e: b.configure(bg=colors[0]))
    return b


# =========================================================================
#  Closest pair view
# =========================================================================
class ClosestPairView(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=C["bg"])
        self.app = app
        f = app.fonts
        self.data = None
        self.step = 0
        self.playing = False
        self.pair_cache = {}
        self.best_so_far = None

        # ---- left: plot -------------------------------------------------
        plot_card = Card(self, fonts=f)
        plot_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        head = tk.Frame(plot_card.body, bg=C["card"])
        head.pack(fill="x")
        tk.Label(head, text="Point set & recursion", bg=C["card"], fg=C["text"],
                 font=f["h2"]).pack(side="left")
        self.coord_var = tk.StringVar(value="")
        tk.Label(head, textvariable=self.coord_var, bg=C["card"], fg=C["muted"],
                 font=f["small"]).pack(side="right")
        self.canvas = tk.Canvas(plot_card.body, bg="#fbfcfe", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, pady=(8, 6))
        self.canvas.bind("<Configure>", lambda e: self._schedule_redraw())
        self.canvas.bind("<Motion>", self._on_motion)
        legend = tk.Frame(plot_card.body, bg=C["card"])
        legend.pack(fill="x")
        for color, text in ((C["accent"], "current sub-problem"), (C["red"], "dividing line"),
                            (C["amber"], "strip (|x − mid| < δ)"), (C["green"], "best pair of call"),
                            ("#be123c", "closest pair")):
            tk.Label(legend, text="■", fg=color, bg=C["card"], font=f["body"]).pack(side="left")
            tk.Label(legend, text=text, fg=C["muted"], bg=C["card"], font=f["small"]).pack(side="left", padx=(0, 10))

        # ---- right: results / controls ---------------------------------
        right = tk.Frame(self, bg=C["bg"], width=360)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        res = Card(right, "Result", fonts=f)
        res.pack(fill="x")
        grid = res.body
        self.s_file = Stat(grid, "Input file", f)
        self.s_points = Stat(grid, "Points", f)
        self.s_dist = Stat(grid, "Closest distance", f, C["accent_dark"])
        self.s_pair = Stat(grid, "Closest pair", f)
        self.s_time = Stat(grid, "Time", f)
        self.s_ok = Stat(grid, "Correct?", f)
        self.s_file.grid(row=0, column=0, sticky="we", pady=2)
        self.s_points.grid(row=0, column=1, sticky="we", pady=2)
        self.s_pair.grid(row=1, column=0, columnspan=2, sticky="we", pady=2)
        self.s_dist.grid(row=2, column=0, sticky="we", pady=2)
        self.s_time.grid(row=2, column=1, sticky="we", pady=2)
        self.s_ok.grid(row=3, column=0, columnspan=2, sticky="we", pady=2)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        anim = Card(right, "Watch it work", fonts=f)
        anim.pack(fill="both", expand=True, pady=(10, 0))
        bar = tk.Frame(anim.body, bg=C["card"])
        bar.pack(fill="x")
        self.b_play = flat_button(bar, "▶ Play", self.toggle_play, "accent", f)
        self.b_play.pack(side="left")
        flat_button(bar, "Step ›", self.step_once, "soft", f).pack(side="left", padx=4)
        flat_button(bar, "Finish ⏭", self.finish, "soft", f).pack(side="left")
        flat_button(bar, "⟲", self.reset_anim, "plain", f).pack(side="left", padx=4)
        self.progress = ttk.Progressbar(anim.body, mode="determinate", style="Accent.Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(10, 2))
        self.step_var = tk.StringVar(value="Select a dataset and press Run.")
        tk.Label(anim.body, textvariable=self.step_var, bg=C["card"], fg=C["muted"],
                 font=f["small"]).pack(anchor="w")
        self.desc = tk.Label(anim.body, text=CP_INFO[2], bg=C["accent_soft"], fg=C["accent_dark"],
                             font=f["body"], wraplength=310, justify="left", anchor="w",
                             padx=10, pady=8)
        self.desc.pack(fill="x", pady=6)
        lf = tk.Frame(anim.body, bg=C["card"])
        lf.pack(fill="both", expand=True)
        self.log = tk.Listbox(lf, font=f["mono_small"], bd=0, highlightthickness=1,
                              highlightbackground=C["border"], activestyle="none",
                              selectbackground=C["accent"], fg=C["text"], bg="#fbfcfe")
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        self.log.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.log.bind("<<ListboxSelect>>", self._jump_to_log)
        self._redraw_job = None

    # ------------------------------------------------------------- data
    @staticmethod
    def compute(path):
        points = cp.load_points(path)                 # original loader
        d, nodes, events, _ = core.trace_closest_pair(points)
        d_plain, t_plain = core.time_closest_pair(points)
        brute, t_brute = None, None
        if len(points) <= 6000:
            b0 = time.perf_counter()
            brute = cp.brute_force(points)            # original brute force
            t_brute = time.perf_counter() - b0
        pair = core.find_pair_with_distance(points, d)
        return dict(path=path, points=points, d=d_plain, nodes=nodes, events=events,
                    time=t_plain, brute=brute, brute_time=t_brute, pair=pair)

    def show(self, data):
        self.data = data
        self.pair_cache = {}
        pts = data["points"]
        xs = [p.x for p in pts]
        ys = [p.y for p in pts]
        self.bounds = (min(xs), max(xs), min(ys), max(ys))
        self.descriptions = [self._describe(kind, node) for kind, node in data["events"]]
        nodes = data["nodes"]
        self.s_file.set(os.path.basename(data["path"]))
        self.s_points.set(str(len(pts)))
        self.s_dist.set(cp.format_number(data["d"]))
        p = data["pair"]
        self.s_pair.set(f"{p[0].show()}  ↔  {p[1].show()}" if p else "—")
        self.s_time.set(fmt_ms(data["time"]))
        if data["brute"] is None:
            self.s_ok.set("not checked", C["muted"])
        elif math.isclose(data["brute"], data["d"], rel_tol=1e-12, abs_tol=1e-12):
            self.s_ok.set("✔ yes (matches brute force)", C["green"])
        else:
            self.s_ok.set("✘ no", C["red"])
        self.log.delete(0, "end")
        self.progress.configure(maximum=len(data["events"]))
        self.reset_anim()
        self.app.set_status(f"Closest pair: δ = {cp.format_number(data['d'])} for {len(pts)} points "
                            f"({fmt_ms(data['time'])}). Press Play to watch the recursion.")

    def _describe(self, kind, node):
        pad = " " * min(node.depth, 6)
        if kind == "enter":
            if node.mid is None:
                return f"{pad}d{node.depth}  base case: {node.n} pts → brute force"
            return (f"{pad}d{node.depth}  divide {node.n} pts at x={cp.format_number(node.mid.x)} "
                    f"→ {node.n // 2} | {node.n - node.n // 2}")
        if node.mid is None:
            return f"{pad}d{node.depth}  brute force δ={cp.format_number(node.d)}"
        strip, delta = core.strip_points(node)
        return (f"{pad}d{node.depth}  combine: min(δL,δR)={cp.format_number(delta)}, "
                f"strip {len(strip)} pts → δ={cp.format_number(node.d)}")

    def _long_text(self, kind, node):
        if kind == "enter":
            if node.mid is None:
                return (f"Depth {node.depth}: only {node.n} point(s) left (n ≤ 3), so the original "
                        f"brute_force() compares every pair directly.")
            return (f"Depth {node.depth} – DIVIDE: {node.n} points are split at the median "
                    f"x = {cp.format_number(node.mid.x)} into a left half ({node.n // 2}) and a "
                    f"right half ({node.n - node.n // 2}). Each half is solved recursively.")
        if node.mid is None:
            return f"Depth {node.depth}: brute force on {node.n} points gives δ = {cp.format_number(node.d)}."
        strip, delta = core.strip_points(node)
        dl, dr = node.children[0].d, node.children[1].d
        better = "a closer pair crosses the line!" if node.d < delta else "no closer pair crosses the line."
        return (f"Depth {node.depth} – COMBINE: δL = {cp.format_number(dl)}, δR = {cp.format_number(dr)}, "
                f"δ = {cp.format_number(delta)}. {len(strip)} points lie in the strip; each is compared with "
                f"at most 7 neighbours (sorted by y) – {better} Result: {cp.format_number(node.d)}.")

    # -------------------------------------------------------- animation
    def toggle_play(self):
        if not self.data:
            return
        if self.step >= len(self.data["events"]):
            self.reset_anim()
        self.playing = not self.playing
        self.b_play.configure(text="⏸ Pause" if self.playing else "▶ Play")
        if self.playing:
            self._tick()

    def _tick(self):
        if not self.playing or not self.data:
            return
        speed = self.app.speed.get()                      # 1 .. 100
        batch = 1 if speed < 80 else int((speed - 70) / 3)
        for _ in range(batch):
            if not self._advance():
                break
        self._render()
        if self.step >= len(self.data["events"]):
            self.playing = False
            self.b_play.configure(text="▶ Play")
            return
        delay = int(900 * (1 - speed / 100) ** 2) + 5
        self.after(delay, self._tick)

    def _advance(self):
        ev = self.data["events"]
        if self.step >= len(ev):
            return False
        kind, node = ev[self.step]
        if kind == "exit":
            if self.best_so_far is None or node.d < self.best_so_far.d:
                self.best_so_far = node
        self.log.insert("end", self.descriptions[self.step])
        self.step += 1
        return True

    def step_once(self):
        if self.data and self._advance():
            self._render()

    def finish(self):
        if not self.data:
            return
        self.playing = False
        self.b_play.configure(text="▶ Play")
        ev = self.data["events"]
        self.log.delete(0, "end")
        self.log.insert("end", *self.descriptions)
        for kind, node in ev[self.step:]:
            if kind == "exit" and (self.best_so_far is None or node.d < self.best_so_far.d):
                self.best_so_far = node
        self.step = len(ev)
        self._render()

    def reset_anim(self):
        self.playing = False
        self.b_play.configure(text="▶ Play")
        self.step = 0
        self.best_so_far = None
        self.log.delete(0, "end")
        self._render()

    def _jump_to_log(self, _e):
        sel = self.log.curselection()
        if not sel or self.playing:
            return
        target = sel[0] + 1
        self.best_so_far = None
        for kind, node in self.data["events"][:target]:
            if kind == "exit" and (self.best_so_far is None or node.d < self.best_so_far.d):
                self.best_so_far = node
        self.step = target
        self._render(keep_log=True)

    # ------------------------------------------------------------ drawing
    def _schedule_redraw(self):
        if self._redraw_job:
            self.after_cancel(self._redraw_job)
        self._redraw_job = self.after(60, self._render)

    def _setup_transform(self):
        w = max(self.canvas.winfo_width(), 100)
        h = max(self.canvas.winfo_height(), 100)
        x0, x1, y0, y1 = self.bounds
        pad = 36
        xr = (x1 - x0) or 1.0
        yr = (y1 - y0) or 1.0
        self.scale = min((w - 2 * pad) / xr, (h - 2 * pad) / yr)
        self.ox = (w - self.scale * xr) / 2 - x0 * self.scale
        self.oy = (h + self.scale * yr) / 2 + y0 * self.scale
        self.cw, self.ch = w, h

    def X(self, x):
        return self.ox + x * self.scale

    def Y(self, y):
        return self.oy - y * self.scale

    def _pair_of(self, node):
        if node.id not in self.pair_cache:
            self.pair_cache[node.id] = core.find_pair_with_distance(node.px, node.d)
        return self.pair_cache[node.id]

    def _render(self, keep_log=False):
        cv = self.canvas
        cv.delete("all")
        f = self.app.fonts
        if not self.data:
            w, h = max(cv.winfo_width(), 100), max(cv.winfo_height(), 100)
            cv.create_text(w / 2, h / 2 - 12, text="No input loaded", font=f["h2"], fill=C["muted"])
            cv.create_text(w / 2, h / 2 + 14, text="Choose a closest-pair file on the left and press Run",
                           font=f["body"], fill=C["muted"])
            return
        self._setup_transform()
        pts = self.data["points"]
        ev = self.data["events"]
        n_total = len(ev)
        self.progress.configure(value=self.step)
        self.step_var.set(f"Step {self.step} / {n_total}")
        x0, x1, y0, y1 = self.bounds

        # axes
        top, bottom = self.Y(y1), self.Y(y0)
        left, right = self.X(x0), self.X(x1)
        cv.create_rectangle(left, top, right, bottom, outline=C["grid"])
        for i in range(5):
            xv = x0 + (x1 - x0) * i / 4
            yv = y0 + (y1 - y0) * i / 4
            cv.create_text(self.X(xv), bottom + 12, text=cp.format_number(round(xv, 2)),
                           font=f["tiny"], fill=C["muted"])
            cv.create_text(left - 4, self.Y(yv), text=cp.format_number(round(yv, 2)),
                           font=f["tiny"], fill=C["muted"], anchor="e")

        current = ev[self.step - 1] if self.step > 0 else None
        if current:
            kind, node = current
            nx0, nx1 = node.px[0].x, node.px[-1].x
            rx0, rx1 = self.X(nx0) - 4, self.X(nx1) + 4
            cv.create_rectangle(rx0, top - 4, rx1, bottom + 4, fill=C["accent_soft"], outline=C["accent"],
                                dash=(4, 3))
            if kind == "exit" and node.mid is not None:
                strip, delta = core.strip_points(node)
                if delta is not None and delta > 0:
                    sx0 = max(self.X(node.mid.x - delta), rx0)
                    sx1 = min(self.X(node.mid.x + delta), rx1)
                    cv.create_rectangle(sx0, top - 4, sx1, bottom + 4, fill=C["amber_soft"], outline=C["amber"])
            if node.mid is not None:
                mx = self.X(node.mid.x)
                cv.create_line(mx, top - 10, mx, bottom + 6, fill=C["red"], width=2, dash=(6, 3))
                cv.create_text(mx, top - 18, text=f"x = {cp.format_number(node.mid.x)}",
                               font=f["tiny"], fill=C["red"])

        # all points
        r = 2.2 if len(pts) > 600 else 3.2
        for p in pts:
            x, y = self.X(p.x), self.Y(p.y)
            cv.create_oval(x - r, y - r, x + r, y + r, fill=C["point"], outline="")

        if current:
            kind, node = current
            if kind == "exit" and node.mid is not None:
                strip, _ = core.strip_points(node)
                for p in strip:
                    x, y = self.X(p.x), self.Y(p.y)
                    cv.create_oval(x - r - 1.5, y - r - 1.5, x + r + 1.5, y + r + 1.5,
                                   fill=C["amber"], outline="")
            if node.mid is None:
                sub = node.px
                for i in range(len(sub)):
                    for j in range(i + 1, len(sub)):
                        cv.create_line(self.X(sub[i].x), self.Y(sub[i].y), self.X(sub[j].x), self.Y(sub[j].y),
                                       fill=C["accent"], dash=(3, 2))
                for p in sub:
                    x, y = self.X(p.x), self.Y(p.y)
                    cv.create_oval(x - 5, y - 5, x + 5, y + 5, outline=C["accent"], width=2)
            if kind == "exit":
                pair = self._pair_of(node)
                if pair:
                    self._draw_pair(pair, C["green"], node.d, 3)

        # best pair found so far / final answer
        done = self.step >= n_total
        if done:
            pair = self.data["pair"]
            if pair:
                self._draw_pair(pair, "#be123c", self.data["d"], 3, final=True)
        elif self.best_so_far is not None:
            pair = self._pair_of(self.best_so_far)
            if pair:
                self._draw_pair(pair, "#be123c", self.best_so_far.d, 2)

        if current and not keep_log:
            self.log.see("end")
        if done:
            p = self.data["pair"]
            self.desc.configure(
                text=f"Done. The closest pair is {p[0].show()} and {p[1].show()} with distance "
                     f"δ = {cp.format_number(self.data['d'])}." if p else "Done.",
                bg=C["green_soft"], fg="#166534")
        elif current:
            self.desc.configure(text=self._long_text(*current), bg=C["accent_soft"], fg=C["accent_dark"])
        else:
            self.desc.configure(text=CP_INFO[2], bg=C["accent_soft"], fg=C["accent_dark"])

    def _draw_pair(self, pair, color, d, width, final=False):
        cv = self.canvas
        a, b = pair
        ax, ay, bx, by = self.X(a.x), self.Y(a.y), self.X(b.x), self.Y(b.y)
        cv.create_line(ax, ay, bx, by, fill=color, width=width)
        rr = 8 if final else 6
        for x, y in ((ax, ay), (bx, by)):
            cv.create_oval(x - rr, y - rr, x + rr, y + rr, outline=color, width=2)
        if final:
            label = f" δ = {cp.format_number(d)} "
            tx, ty = (ax + bx) / 2, min(ay, by) - 18
            tid = cv.create_text(tx, ty, text=label, font=self.app.fonts["body_bold"], fill="white")
            bb = cv.bbox(tid)
            rid = cv.create_rectangle(bb[0] - 4, bb[1] - 2, bb[2] + 4, bb[3] + 2, fill=color, outline="")
            cv.tag_raise(tid, rid)

    def _on_motion(self, e):
        if not self.data:
            return
        x = (e.x - self.ox) / self.scale
        y = (self.oy - e.y) / self.scale
        self.coord_var.set(f"x = {x:.1f}, y = {y:.1f}")


# =========================================================================
#  Karatsuba view
# =========================================================================
class KaratsubaView(tk.Frame):
    TRACE_LIMIT = 400_000

    def __init__(self, master, app):
        super().__init__(master, bg=C["bg"])
        self.app = app
        f = app.fonts
        self.data = None
        self.loaded = set()
        self.playing = False
        self.play_list = []
        self.play_idx = 0
        self.current = None

        # ---- top: one-row result strip -------------------------------
        st = Card(self, fonts=f)
        st.pack(fill="x")
        g = st.body
        self.s_file = Stat(g, "Input file", f)
        self.s_inputs = Stat(g, "Numbers", f)
        self.s_digits = Stat(g, "Product digits", f, C["accent_dark"])
        self.s_time = Stat(g, "Time", f)
        self.s_calls = Stat(g, "Recursive calls", f)
        self.s_ok = Stat(g, "Correct?", f)
        for i, s in enumerate([self.s_file, self.s_inputs, self.s_digits, self.s_time, self.s_calls, self.s_ok]):
            s.grid(row=0, column=i, sticky="w", padx=(0, 10))
            g.columnconfigure(i, weight=1)

        self.bottom = ttk.Notebook(self, style="Inner.TNotebook",
                                    height=118 if self.winfo_screenheight() >= 850 else 72)
        self.bottom.pack(side="bottom", fill="x")

        # ---- middle: tree + detail -----------------------------------
        mid = tk.PanedWindow(self, orient="horizontal", sashwidth=8, bg=C["bg"], bd=0)
        mid.pack(fill="both", expand=True, pady=10)
        tree_card = Card(mid, fonts=f)
        th = tk.Frame(tree_card.body, bg=C["card"])
        th.pack(fill="x")
        tk.Label(th, text="Recursion tree", bg=C["card"], fg=C["text"], font=f["h2"]).pack(side="left")
        tk.Label(th, text="click a call to inspect", bg=C["card"], fg=C["muted"],
                 font=f["small"]).pack(side="right")
        tf = tk.Frame(tree_card.body, bg=C["card"])
        tf.pack(fill="both", expand=True, pady=(8, 0))
        self.tree = ttk.Treeview(tf, columns=("digits", "result"), show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="Call")
        self.tree.heading("digits", text="Operands")
        self.tree.heading("result", text="Product")
        self.tree.column("#0", width=230, stretch=True)
        self.tree.column("digits", width=90, anchor="center", stretch=False)
        self.tree.column("result", width=150, stretch=False)
        ysb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        ysb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewOpen>>", self._on_open)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.tag_configure("base", foreground=C["teal"])
        mid.add(tree_card, minsize=320, width=470)

        det = Card(mid, fonts=f)
        dh = tk.Frame(det.body, bg=C["card"])
        dh.pack(fill="x")
        tk.Label(dh, text="How this call works", bg=C["card"], fg=C["text"], font=f["h2"]).pack(side="left")
        ctr = tk.Frame(dh, bg=C["card"])
        ctr.pack(side="right")
        self.depth_var = tk.IntVar(value=2)          # walk-through shows the top 3 levels
        self.b_play = flat_button(ctr, "▶ Walk through", self.toggle_play, "accent", f)
        self.b_play.pack(side="left", padx=(4, 0))
        self.detail = tk.Canvas(det.body, bg="#fbfcfe", highlightthickness=0)
        self.detail.pack(fill="both", expand=True, pady=(8, 0))
        self.detail.bind("<Configure>", lambda e: self._draw_detail())
        mid.add(det, minsize=420)

        # ---- bottom: inputs / product / trace / chart ------------------
        inf = tk.Frame(self.bottom, bg=C["card"])
        self.in_text = self._make_text(inf)
        self.in_text.tag_configure("lbl", foreground=C["accent"], font=f["mono_bold"])
        self._set_text(self.in_text, "Choose a Karatsuba input file and press Run.")
        self.bottom.add(inf, text="  Numbers & product  ")

        trf = tk.Frame(self.bottom, bg=C["card"])
        self.trace_text = self._make_text(trf, mono=True)
        tb = tk.Frame(trf, bg=C["card"])
        tb.pack(fill="x", padx=6, pady=(0, 6))
        self.trace_info = tk.Label(tb, text="", bg=C["card"], fg=C["muted"], font=f["small"])
        self.trace_info.pack(side="left")
        flat_button(tb, "Save full trace…", self.save_trace, "soft", f).pack(side="right")
        self.bottom.add(trf, text="  Console output  ")

        cf = tk.Frame(self.bottom, bg=C["card"])
        self.level_canvas = tk.Canvas(cf, bg=C["card"], highlightthickness=0)
        self.level_canvas.pack(fill="both", expand=True, padx=6, pady=6)
        self.level_canvas.bind("<Configure>", lambda e: self._draw_levels())
        self.bottom.add(cf, text="  Calls per level  ")

    def _make_text(self, parent, mono=False):
        f = self.app.fonts
        fr = tk.Frame(parent, bg=C["card"])
        fr.pack(fill="both", expand=True, padx=6, pady=6)
        t = tk.Text(fr, height=4, wrap="char" if not mono else "none", font=f["mono_small"], bd=0, bg="#fbfcfe",
                    fg=C["text"], highlightthickness=0, padx=6, pady=4)
        sb = ttk.Scrollbar(fr, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=sb.set)
        if mono:
            xb = ttk.Scrollbar(fr, orient="horizontal", command=t.xview)
            t.configure(xscrollcommand=xb.set)
            xb.pack(side="bottom", fill="x")
        sb.pack(side="right", fill="y")
        t.pack(side="left", fill="both", expand=True)
        t.configure(state="disabled")
        return t

    @staticmethod
    def _set_text(widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    # ------------------------------------------------------------- data
    @staticmethod
    def compute(path):
        n, m = core.load_numbers(path)
        product, nodes, trace, _ = core.trace_karatsuba(n, m, capture_output=True)
        p_plain, t_plain = core.time_karatsuba(n, m)
        return dict(path=path, n=n, m=m, product=p_plain, nodes=nodes, trace=trace,
                    time=t_plain, verified=(p_plain == n * m))

    def show(self, data):
        self.stop_play()
        self.data = data
        n, m, nodes = data["n"], data["m"], data["nodes"]
        t = self.in_text
        t.configure(state="normal")
        t.delete("1.0", "end")
        t.insert("end", f"N ({len(str(n))} digits)\n", "lbl")
        t.insert("end", f"{n}\n\n")
        t.insert("end", f"M ({len(str(m))} digits)\n", "lbl")
        t.insert("end", f"{m}\n\n")
        t.insert("end", f"N × M  ({len(str(data['product']))} digits)\n", "lbl")
        t.insert("end", str(data["product"]))
        t.configure(state="disabled")
        self.s_inputs.set(f"{len(str(n))} × {len(str(m))} digits")
        self.s_file.set(os.path.basename(data["path"]))
        self.s_digits.set(str(len(str(data["product"]))))
        self.s_time.set(fmt_ms(data["time"]))
        self.s_calls.set(f"{len(nodes):,}")
        self.s_ok.set("✔ yes" if data["verified"] else "✘ no",
                      C["green"] if data["verified"] else C["red"])
        trace = data["trace"]
        shown = trace[:self.TRACE_LIMIT]
        if len(trace) > self.TRACE_LIMIT:
            shown += f"\n\n… trace truncated for display ({len(trace):,} characters in total). " \
                     f"Use 'Save full trace…' to get the complete output."
        self._set_text(self.trace_text, shown)
        self.trace_info.configure(text=f"{trace.count(chr(10)):,} lines · {len(trace) / 1024:,.0f} KB "
                                       f"printed by the original karatsuba()")
        # tree
        self.tree.delete(*self.tree.get_children())
        self.loaded = set()
        self._insert(nodes[0], "")
        self.tree.item("0", open=True)
        self._load_children(nodes[0])
        self.tree.selection_set("0")
        self.tree.focus("0")
        self.current = nodes[0]
        self._draw_detail()
        self._draw_levels()
        self.app.set_status(f"Karatsuba: {len(str(n))}×{len(str(m))} digits → {len(str(data['product']))}-digit "
                            f"product in {fmt_ms(data['time'])} using {len(nodes):,} recursive calls.")

    def _insert(self, node, parent_iid):
        label = f"#{node.id}  {node.role}" if node.role != "root" else "#0  karatsuba(N, M)"
        digits = f"{len(str(node.n))}×{len(str(node.m))}"
        self.tree.insert(parent_iid, "end", iid=str(node.id), text=label,
                         values=(digits, short_num(node.result, 18)),
                         tags=("base",) if node.is_base else ())
        if node.children:
            self.tree.insert(str(node.id), "end", iid=f"dummy{node.id}", text="…")

    def _load_children(self, node):
        if node.id in self.loaded:
            return
        self.loaded.add(node.id)
        if self.tree.exists(f"dummy{node.id}"):
            self.tree.delete(f"dummy{node.id}")
        for ch in node.children:
            self._insert(ch, str(node.id))

    def _on_open(self, _e):
        iid = self.tree.focus()
        if iid and iid.isdigit():
            self._load_children(self.data["nodes"][int(iid)])

    def _on_select(self, _e):
        sel = self.tree.selection()
        if sel and sel[0].isdigit() and self.data:
            self.current = self.data["nodes"][int(sel[0])]
            self._draw_detail()

    def select_node(self, node):
        chain = []
        p = node.parent
        while p is not None:
            chain.append(p)
            p = p.parent
        for anc in reversed(chain):
            self._load_children(anc)
            self.tree.item(str(anc.id), open=True)
        iid = str(node.id)
        self.tree.selection_set(iid)
        self.tree.focus(iid)
        self.tree.see(iid)

    def toggle_play(self):
        if not self.data:
            return
        if self.playing:
            self.stop_play()
            return
        limit = self.depth_var.get()
        self.play_list = []
        stack = [self.data["nodes"][0]]
        while stack:                                    # pre-order = execution order
            nd = stack.pop()
            if nd.depth <= limit:
                self.play_list.append(nd)
                stack.extend(reversed(nd.children))
        self.play_idx = 0
        self.playing = True
        self.b_play.configure(text="⏸ Stop")
        self._tick()

    def stop_play(self):
        self.playing = False
        self.b_play.configure(text="▶ Walk through")

    def _tick(self):
        if not self.playing:
            return
        if self.play_idx >= len(self.play_list):
            self.stop_play()
            return
        self.select_node(self.play_list[self.play_idx])
        self.play_idx += 1
        speed = self.app.speed.get()
        self.after(int(2500 * (1 - speed / 100) ** 2) + 40, self._tick)

    # ------------------------------------------------------------ drawing
    def _draw_detail(self):
        cv = self.detail
        cv.delete("all")
        f = self.app.fonts
        cw = self.app.mono_w                                   # width of one mono digit
        w, h = max(cv.winfo_width(), 300), max(cv.winfo_height(), 200)
        node = self.current
        if node is None:
            cv.create_text(w / 2, h / 2 - 30, text=KS_INFO[0], font=f["h2"], fill=C["text"])
            cv.create_text(w / 2, h / 2, text=KS_INFO[2], font=f["body"], fill=C["muted"], width=w - 60,
                           justify="center")
            cv.create_text(w / 2, h / 2 + 40, text="Time complexity: " + KS_INFO[1], font=f["body_bold"],
                           fill=C["accent"])
            return

        def fit(px):                                         # how many digits fit in px pixels
            return max(8, int(px / cw))

        x, y = 14, 14
        cv.create_text(x, y, anchor="w", font=f["body_bold"], fill=C["text"],
                       text=f"Call #{node.id}   ·   depth {node.depth}   ·   {node.role}")
        y += 22
        if node.is_base:
            self._box(cv, x, y, w - 28, 60, C["teal_soft"], C["teal"])
            cv.create_text(x + 12, y + 18, anchor="w", font=f["body_bold"], fill=C["teal"],
                           text="BASE CASE  (n < 10 or m < 10)")
            k = fit((w - 120) / 3)
            cv.create_text(x + 12, y + 40, anchor="w", font=f["mono"], fill=C["text"],
                           text=f"{short_num(node.n, k)} × {short_num(node.m, k)} = {short_num(node.result, k)}")
            y += 78
            cv.create_text(x, y, anchor="w", font=f["small"], fill=C["muted"], width=w - 30,
                           text="One operand is a single digit, so the original function multiplies directly "
                                "and returns the result to its parent call.")
            return

        half, a, b, c, d = node.split()
        col_w = (w - 28 - 40) / 2

        def operand_row(yy, name, hi, lo, hi_name, lo_name):
            cv.create_text(x, yy + 19, anchor="w", font=f["mono_bold"], fill=C["text"], text=f"{name} =")
            for i, (val, nm, desc, (fill, line)) in enumerate((
                    (hi, hi_name, f"high part, {len(str(hi))} digits", (C["blue_soft"], C["blue"])),
                    (lo, lo_name, f"low part, {half} digits", (C["amber_soft"], C["amber"])))):
                bx = x + 40 + i * (col_w + 4)
                self._box(cv, bx, yy, col_w - 4, 38, fill, line)
                cv.create_text(bx + 8, yy + 11, anchor="w", font=f["tiny"], fill=line, text=f"{nm}  ({desc})")
                cv.create_text(bx + 8, yy + 27, anchor="w", font=f["mono"], fill=C["text"],
                               text=short_num(val, fit(col_w - 24)))

        cv.create_text(x, y, anchor="w", font=f["small"], fill=C["muted"],
                       text=f"① DIVIDE — split both operands at 10^{half}  "
                            f"(operands have {len(str(node.n))} and {len(str(node.m))} digits)")
        y += 11
        operand_row(y, "n", a, b, "a", "b")
        y += 42
        operand_row(y, "m", c, d, "c", "d")
        y += 52

        cv.create_text(x, y, anchor="w", font=f["small"], fill=C["muted"],
                       text="② CONQUER — only three recursive multiplications (click one to open it)")
        y += 11
        ch = node.children
        w_val, y_val = ch[0].result, ch[1].result
        z_val = ch[2].result - w_val - y_val
        cards = [("w = karatsuba(a, c)", w_val, ch[0]), ("y = karatsuba(b, d)", y_val, ch[1]),
                 ("z = (a+b)(c+d) − w − y", z_val, ch[2])]
        cwid = (w - 28 - 12) / 3
        for i, (title, val, child) in enumerate(cards):
            cx = x + i * (cwid + 6)
            tag = f"child{child.id}"
            self._box(cv, cx, y, cwid, 44, C["accent_soft"], C["accent"], tag)
            cv.create_text(cx + 8, y + 12, anchor="w", font=f["tiny"], fill=C["accent_dark"], text=title,
                           tags=tag, width=cwid - 12)
            cv.create_text(cx + 8, y + 30, anchor="w", font=f["mono"], fill=C["text"],
                           text=short_num(val, fit(cwid - 20)), tags=tag)
            cv.tag_bind(tag, "<Button-1>", lambda e, nd=child: self.select_node(nd))
            cv.tag_bind(tag, "<Enter>", lambda e: cv.configure(cursor="hand2"))
            cv.tag_bind(tag, "<Leave>", lambda e: cv.configure(cursor=""))
        y += 54

        cv.create_text(x, y, anchor="w", font=f["small"], fill=C["muted"], text="③ COMBINE — shift and add")
        y += 11
        self._box(cv, x, y, w - 28, 62, C["green_soft"], C["green"])
        cv.create_text(x + 10, y + 13, anchor="w", font=f["mono_bold"], fill="#166534",
                       text=f"result = w·10^{2 * half} + z·10^{half} + y")
        fixed = len(f"       = ·10^{2 * half} + ·10^{half} + ")
        k2 = fit(((w - 50) - fixed * cw) / 3)
        cv.create_text(x + 10, y + 31, anchor="w", font=f["mono"], fill=C["text"],
                       text=f"       = {short_num(w_val, k2)}·10^{2 * half} + {short_num(z_val, k2)}·10^{half} "
                            f"+ {short_num(y_val, k2)}")
        ok = node.result == node.n * node.m
        cv.create_text(x + 10, y + 49, anchor="w", font=f["mono_bold"], fill=C["text"],
                       text=f"       = {short_num(node.result, fit(w - 50 - 24 * cw))}   "
                            f"{'✔ equals n·m' if ok else '✘'}")

    def _box(self, cv, x, y, w, h, fill, outline, tag=None):
        cv.create_rectangle(x, y, x + w, y + h, fill=fill, outline=outline, width=1, tags=tag)

    def _draw_levels(self):
        cv = self.level_canvas
        cv.delete("all")
        f = self.app.fonts
        if not self.data:
            return
        counts = {}
        for nd in self.data["nodes"]:
            counts[nd.depth] = counts.get(nd.depth, 0) + 1
        w, h = max(cv.winfo_width(), 200), max(cv.winfo_height(), 80)
        levels = sorted(counts)
        mx = max(counts.values())
        left, bottom, top = 40, h - 18, 22
        cv.create_text(left, 8, anchor="w", font=f["small"], fill=C["muted"],
                       text="Number of recursive calls at each depth (each call spawns 3 → about 3^k calls at level k)")
        bw = (w - left - 10) / len(levels)
        for i, lv in enumerate(levels):
            bh = (bottom - top) * counts[lv] / mx
            x0 = left + i * bw + 3
            cv.create_rectangle(x0, bottom - bh, x0 + bw - 6, bottom, fill=C["accent"], outline="")
            cv.create_text(x0 + (bw - 6) / 2, bottom + 9, text=str(lv), font=f["tiny"], fill=C["muted"])
            cv.create_text(x0 + (bw - 6) / 2, bottom - bh - 7, text=f"{counts[lv]:,}", font=f["tiny"],
                           fill=C["text"])

    # ------------------------------------------------------------ actions
    def save_trace(self):
        if not self.data:
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")],
                                            initialfile="karatsuba_trace.txt")
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self.data["trace"])
            self.app.set_status(f"Trace saved to {path}")


# =========================================================================
#  Main window
# =========================================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Divide & Conquer Visualizer – Closest Pair & Karatsuba")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{min(1360, sw - 20)}x{min(860, sh - 70)}+0+0")
        self.minsize(min(1150, sw - 20), min(700, sh - 70))
        if sw < 1360 or sh < 900:
            try:
                self.state("zoomed")            # Windows / macOS: start maximised on small screens
            except tk.TclError:
                pass
        self.configure(bg=C["bg"])
        ui = pick_font(self, ["Segoe UI", "Inter", "Helvetica Neue", "SF Pro Text", "Helvetica", "Arial"],
                       "TkDefaultFont")
        mono = pick_font(self, ["Consolas", "JetBrains Mono", "Menlo", "DejaVu Sans Mono", "Courier New"],
                         "TkFixedFont")
        self.mono_w = tkfont.Font(self, family=mono, size=10).measure("0")
        self.fonts = {
            "title": (ui, 17, "bold"), "h2": (ui, 12, "bold"), "body": (ui, 10), "body_bold": (ui, 10, "bold"),
            "small": (ui, 9), "small_bold": (ui, 8, "bold"), "tiny": (ui, 8), "stat": (ui, 11, "bold"),
            "button": (ui, 10, "bold"), "mono": (mono, 10), "mono_bold": (mono, 10, "bold"),
            "mono_small": (mono, 9),
        }
        self._style()
        self.kind = tk.StringVar(value="closest")
        self.speed = tk.IntVar(value=60)
        self.selected_path = None
        self.busy = False

        self._header()
        self.status = tk.StringVar(value="Ready. Pick an algorithm and a dataset, then press Run.")
        sbar = tk.Frame(self, bg="#e3e7ef")
        sbar.pack(fill="x", side="bottom")
        tk.Label(sbar, textvariable=self.status, bg="#e3e7ef", fg=C["muted"], font=self.fonts["small"],
                 anchor="w", padx=12, pady=4).pack(fill="x")
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True)
        self._sidebar(body)
        main = tk.Frame(body, bg=C["bg"])
        main.pack(side="left", fill="both", expand=True, padx=14, pady=12)
        self.nb = ttk.Notebook(main, style="Main.TNotebook")
        self.nb.pack(fill="both", expand=True)
        self.cp_view = ClosestPairView(self.nb, self)
        self.ks_view = KaratsubaView(self.nb, self)
        self.nb.add(self.cp_view, text="   Closest Pair of Points   ")
        self.nb.add(self.ks_view, text="   Karatsuba Multiplication   ")
        self.nb.bind("<<NotebookTabChanged>>", self._tab_changed)

        self.refresh_datasets()

    # --------------------------------------------------------------- style
    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        f = self.fonts
        s.configure(".", font=f["body"], background=C["bg"])
        s.configure("Main.TNotebook", background=C["bg"], borderwidth=0, tabmargins=(0, 0, 0, 0))
        s.configure("Main.TNotebook.Tab", padding=(14, 8), font=f["body_bold"], background="#dfe3ec",
                    foreground=C["muted"], borderwidth=0)
        s.map("Main.TNotebook.Tab", background=[("selected", C["accent"])],
              foreground=[("selected", "#ffffff")], expand=[("selected", (0, 0, 0, 0))])
        s.configure("Inner.TNotebook", background=C["bg"], borderwidth=0)
        s.configure("Inner.TNotebook.Tab", padding=(10, 5), font=f["small_bold"], background="#dfe3ec",
                    foreground=C["muted"])
        s.map("Inner.TNotebook.Tab", background=[("selected", C["card"])], foreground=[("selected", C["accent"])])
        s.configure("TNotebook", background=C["bg"])
        s.configure("Treeview", rowheight=24, font=f["small"], background=C["card"], fieldbackground=C["card"],
                    bordercolor=C["border"], borderwidth=0)
        s.configure("Treeview.Heading", font=f["small_bold"], background="#f1f3f8", foreground=C["muted"],
                    relief="flat", padding=(6, 5))
        s.map("Treeview", background=[("selected", C["accent"])], foreground=[("selected", "#ffffff")])
        s.configure("Accent.Horizontal.TProgressbar", troughcolor="#eceef4", background=C["accent"],
                    bordercolor="#eceef4", lightcolor=C["accent"], darkcolor=C["accent"], thickness=6)
        s.configure("Vertical.TScrollbar", background="#e3e7ef", troughcolor=C["card"], bordercolor=C["card"],
                    arrowcolor=C["muted"])
        s.configure("Side.Horizontal.TScale", background=C["side"], troughcolor=C["side2"])

    def _header(self):
        f = self.fonts
        hd = tk.Frame(self, bg=C["accent"], height=58)
        hd.pack(fill="x")
        hd.pack_propagate(False)
        left = tk.Frame(hd, bg=C["accent"])
        left.pack(side="left", padx=20)
        tk.Label(left, text="◆ Divide & Conquer Visualizer", bg=C["accent"], fg="white",
                 font=f["title"]).pack(anchor="w", pady=(7, 0))
        tk.Label(left, text="Design & Analysis of Algorithms – Project  ·  Closest Pair of Points  ·  "
                            "Karatsuba Integer Multiplication", bg=C["accent"], fg="#d9d7ff",
                 font=f["small"]).pack(anchor="w")
        right = tk.Frame(hd, bg=C["accent"])
        right.pack(side="right", padx=20)
        for roll, name in TEAM:
            chip = tk.Frame(right, bg=C["accent_dark"])
            chip.pack(side="left", padx=4)
            tk.Label(chip, text=f"{name}  ·  {roll}", bg=C["accent_dark"], fg="white",
                     font=f["small"], padx=10, pady=5).pack()

    def _sidebar(self, parent):
        f = self.fonts
        sb = tk.Frame(parent, bg=C["side"], width=290)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        def section(text):
            tk.Label(sb, text=text, bg=C["side"], fg=C["side_muted"], font=f["small_bold"]).pack(
                anchor="w", padx=18, pady=(16, 6))

        section("1 · CHOOSE ALGORITHM")
        self.alg_buttons = {}
        for key, (title, cx, _) in (("closest", CP_INFO), ("karatsuba", KS_INFO)):
            b = tk.Frame(sb, bg=C["side2"], cursor="hand2")
            b.pack(fill="x", padx=14, pady=3)
            t1 = tk.Label(b, text=title, bg=C["side2"], fg="white", font=f["body_bold"], anchor="w")
            t1.pack(fill="x", padx=12, pady=(8, 0))
            t2 = tk.Label(b, text=f"Divide & conquer · {cx}", bg=C["side2"], fg=C["side_muted"],
                          font=f["small"], anchor="w")
            t2.pack(fill="x", padx=12, pady=(0, 8))
            for wdg in (b, t1, t2):
                wdg.bind("<Button-1>", lambda e, k=key: self.choose_algorithm(k))
            self.alg_buttons[key] = (b, t1, t2)

        section("2 · SELECT INPUT FILE")
        lf = tk.Frame(sb, bg=C["side"])
        lf.pack(fill="both", expand=True, padx=14)
        self.ds_list = tk.Listbox(lf, bg=C["side2"], fg=C["side_text"], font=f["mono_small"], bd=0,
                                  highlightthickness=0, selectbackground=C["accent"], selectforeground="white",
                                  activestyle="none", height=10)
        dsb = ttk.Scrollbar(lf, orient="vertical", command=self.ds_list.yview)
        self.ds_list.configure(yscrollcommand=dsb.set)
        self.ds_list.pack(side="left", fill="both", expand=True)
        dsb.pack(side="right", fill="y")
        self.ds_list.bind("<<ListboxSelect>>", self._dataset_selected)
        self.ds_list.bind("<Double-Button-1>", lambda e: self.run())
        flat_button(sb, "📂  Browse any .txt file…", self.browse, "ghost", f).pack(fill="x", padx=14, pady=(8, 0))
        self.sel_var = tk.StringVar(value="No file selected")
        tk.Label(sb, textvariable=self.sel_var, bg=C["side"], fg=C["side_text"], font=f["small"],
                 wraplength=250, justify="left", anchor="w").pack(fill="x", padx=18, pady=(8, 0))

        section("3 · RUN")
        self.run_btn = flat_button(sb, "▶  Run algorithm", self.run, "accent", f)
        self.run_btn.configure(pady=10)
        self.run_btn.pack(fill="x", padx=14)
        tk.Label(sb, text="Animation speed", bg=C["side"], fg=C["side_muted"], font=f["small"]).pack(
            anchor="w", padx=18, pady=(12, 0))
        tk.Scale(sb, from_=1, to=100, orient="horizontal", variable=self.speed, showvalue=False,
                 bg=C["accent"], fg=C["side_text"], troughcolor=C["side2"], highlightthickness=0, bd=0,
                 sliderrelief="flat", sliderlength=22, width=12, activebackground="#6d66f0").pack(
            fill="x", padx=14, pady=(4, 0))
        tk.Label(sb, text="slow                                     fast", bg=C["side"], fg=C["side_muted"],
                 font=f["tiny"]).pack(anchor="w", padx=18, pady=(0, 12))

    # ------------------------------------------------------------- actions
    def set_status(self, text):
        self.status.set(text)

    def choose_algorithm(self, key, switch_tab=True):
        self.kind.set(key)
        for k, (b, t1, t2) in self.alg_buttons.items():
            bg = C["accent"] if k == key else C["side2"]
            for wdg in (b, t1, t2):
                wdg.configure(bg=bg)
            t2.configure(fg="#d9d7ff" if k == key else C["side_muted"])
        self.refresh_datasets()
        if switch_tab:
            self.nb.select(0 if key == "closest" else 1)

    def _tab_changed(self, _e):
        idx = self.nb.index(self.nb.select())
        if idx in (0, 1):
            key = "closest" if idx == 0 else "karatsuba"
            if key != self.kind.get():
                self.choose_algorithm(key, switch_tab=False)

    def refresh_datasets(self):
        if not hasattr(self, "ds_list"):
            return
        self.ds_paths = core.list_datasets(self.kind.get())
        self.ds_list.delete(0, "end")
        for p in self.ds_paths:
            name = os.path.basename(p)
            self.ds_list.insert("end", f" {name:<22}{core.dataset_summary(p):>8}")
        if self.selected_path in self.ds_paths:
            i = self.ds_paths.index(self.selected_path)
            self.ds_list.selection_set(i)
            self.ds_list.see(i)

    def _dataset_selected(self, _e):
        sel = self.ds_list.curselection()
        if sel:
            self.selected_path = self.ds_paths[sel[0]]
            self.sel_var.set(f"Selected: {os.path.basename(self.selected_path)}")

    def browse(self):
        path = filedialog.askopenfilename(title="Select an input file", initialdir=core.BASE_DIR,
                                          filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            kind = core.detect_kind(path)
        except Exception as exc:
            messagebox.showerror("Invalid file", str(exc))
            return
        self.selected_path = path
        self.sel_var.set(f"Selected: {os.path.basename(path)}\n(detected: "
                         f"{'closest pair points' if kind == 'closest' else 'two big integers'})")
        self.choose_algorithm(kind)
        self.run()

    def run(self):
        if self.busy:
            return
        path = self.selected_path
        if not path or not os.path.isfile(path):
            messagebox.showwarning("No file", "Please select an input file first.")
            return
        try:
            kind = core.detect_kind(path)
        except Exception as exc:
            messagebox.showerror("Invalid file", str(exc))
            return
        if kind != self.kind.get():
            self.choose_algorithm(kind)
        else:
            self.nb.select(0 if kind == "closest" else 1)
        view = self.cp_view if kind == "closest" else self.ks_view
        self.busy = True
        self.run_btn.configure(text="⏳  Running…", state="disabled")
        self.set_status(f"Running {'closest pair' if kind == 'closest' else 'Karatsuba'} on "
                        f"{os.path.basename(path)}…")
        self.configure(cursor="watch")
        q = queue.Queue()

        def work():
            try:
                q.put(("ok", view.compute(path)))
            except Exception as exc:
                q.put(("err", exc))

        threading.Thread(target=work, daemon=True).start()
        self._wait(q, view)

    def _wait(self, q, view):
        try:
            status, payload = q.get_nowait()
        except queue.Empty:
            self.after(40, self._wait, q, view)
            return
        self.busy = False
        self.configure(cursor="")
        self.run_btn.configure(text="▶  Run algorithm", state="normal")
        if status == "err":
            messagebox.showerror("Error", f"Could not run the algorithm:\n{payload}")
            self.set_status("Error – see message.")
            return
        view.show(payload)


def main():
    app = App()
    app.choose_algorithm("closest")
    app.mainloop()


if __name__ == "__main__":
    main()
