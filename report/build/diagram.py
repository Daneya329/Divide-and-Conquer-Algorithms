from PIL import Image, ImageDraw, ImageFont
W, H = 2400, 850
img = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(img)
F = "/usr/share/fonts/opentype/inter/Inter-%s.otf"
def font(w, s): return ImageFont.truetype(F % w, s)
T, B, S = font("Regular", 26), font("Bold", 30), font("Regular", 23)
COL = {"in": ("#e0ecff", "#2563eb"), "ui": ("#e7e6fd", "#4f46e5"), "core": ("#fdf0d5", "#b45309"),
       "alg": ("#dcfce7", "#15803d"), "out": ("#fce7f3", "#be185d"), "bm": ("#f1f5f9", "#475569")}
def box(x, y, w, h, kind, title, lines):
    fill, line = COL[kind]
    d.rounded_rectangle((x, y, x + w, y + h), 18, fill=fill, outline=line, width=4)
    d.text((x + w / 2, y + 22), title, font=B, fill=line, anchor="mt")
    yy = y + 66
    for ln in lines:
        d.text((x + w / 2, yy), ln, font=S, fill="#1f2937", anchor="mt"); yy += 32
def arrow(x1, y1, x2, y2, label=None, color="#334155"):
    d.line((x1, y1, x2, y2), fill=color, width=5)
    import math
    a = math.atan2(y2 - y1, x2 - x1); L = 22
    d.polygon([(x2, y2), (x2 - L*math.cos(a - .4), y2 - L*math.sin(a - .4)), (x2 - L*math.cos(a + .4), y2 - L*math.sin(a + .4))], fill=color)
    if label: d.text(((x1+x2)/2, (y1+y2)/2 - 12), label, font=S, fill="#475569", anchor="mb")
# lane labels
d.text((W/2, 18), "Proposed system: Divide & Conquer Visualizer (Python + Tkinter)", font=font("Bold", 36), fill="#111827", anchor="mt")
# column 1: inputs
box(30, 270, 330, 300, "in", "Input files (.txt)", ["datasets/closest_pair", "testcase1–10", "datasets/karatsuba", "karatsuba_input_1–10", "or any file (Browse)"])
# column 2: GUI controller
box(440, 250, 360, 340, "ui", "GUI controller", ["algorithm selector", "dataset list / Browse", "detect_kind(): points", "or two integers?", "Run (worker thread)", "speed slider"])
arrow(360, 420, 440, 420)
# lanes
yl1, yl2, h = 90, 580, 250
box(890, yl1, 380, h, "core", "Recorder (core.py)", ["wraps closest_pair()", "logs every call:", "sub-array, median,", "δ returned", "(no algorithm change)"])
box(890, yl2, 380, h, "core", "Recorder (core.py)", ["wraps karatsuba()", "logs n, m, depth,", "role w / y / z, result", "captures print() trace", "(no algorithm change)"])
arrow(800, 380, 890, 215); d.text((838, 300), "points", font=S, fill="#475569", anchor="rm")
arrow(800, 520, 890, 705); d.text((780, 630), "N, M", font=S, fill="#475569")
box(1360, yl1, 440, h, "alg", "Original closest_pair()", ["DIVIDE: split at median x", "CONQUER: solve halves", "COMBINE: strip |x−mid|<δ,", "≤7 neighbours by y", "base case n≤3: brute_force"])
box(1360, yl2, 440, h, "alg", "Original karatsuba()", ["DIVIDE: n=a·10^h+b, m=c·10^h+d", "CONQUER: w=ac, y=bd,", "z=(a+b)(c+d)−w−y", "COMBINE: w·10^2h+z·10^h+y", "base case: n<10 or m<10"])
arrow(1270, 190, 1360, 190, "call"); arrow(1360, 260, 1270, 260, "δ")
arrow(1270, 680, 1360, 680, "call"); arrow(1360, 750, 1270, 750, "n·m")
box(1890, yl1, 480, h, "out", "Closest-pair view", ["scatter plot + dividing lines", "strip & best-pair animation", "Play / Step / Finish + log", "δ, pair, time, calls", "check vs brute_force()"])
box(1890, yl2, 480, h, "out", "Karatsuba view", ["lazy recursion tree", "split / 3 products / combine", "walk-through animation", "calls per level, trace", "check vs Python n*m"])
arrow(1800, 215, 1890, 215); arrow(1800, 705, 1890, 705)
# benchmark
box(1000, 400, 760, 130, "bm", "run_benchmarks.py (terminal)", ["applies both algorithms to all 20 files · timing · correctness · CSV"])
arrow(800, 465, 1000, 465)
img.save("/home/user/DAA_Project/report/build/system_diagram.png")
