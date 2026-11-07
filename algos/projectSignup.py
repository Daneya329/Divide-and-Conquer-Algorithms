import math
import os
import tkinter as tk
from tkinter import filedialog, messagebox

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def show(self):
        return f"({self.x},{self.y})"

def distance(p1, p2):
    return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)

def brute_force(points):
    minimum = float('inf')
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            d = distance(points[i], points[j])
            if d < minimum:
                minimum = d
    return minimum

def closest_pair(px, py):
    n = len(px)
    if n <= 3:
        return brute_force(px)
    mid = n // 2
    mid_point = px[mid]
    left_x = px[:mid]
    right_x = px[mid:]

    left_set = set(left_x)
    left_y = []
    right_y = []
    for p in py:
        if p in left_set:
            left_y.append(p)
        else:
            right_y.append(p)

    d_left = closest_pair(left_x, left_y)
    d_right = closest_pair(right_x, right_y)
    d = min(d_left, d_right)

    strip = []
    for p in py:
        if abs(p.x - mid_point.x) < d:
            strip.append(p)

    minimum = d
    for i in range(len(strip)):
        for j in range(i + 1, min(i + 8, len(strip))):
            if strip[j].y - strip[i].y >= minimum:
                break
            current = distance(strip[i], strip[j])
            if current < minimum:
                minimum = current
    return minimum


# File loading

def load_points(file_path):
    if not file_path.lower().endswith(".txt"):
        raise ValueError("Invalid file type. Please select a .txt file.")
    if not os.path.isfile(file_path):
        raise ValueError("The selected file does not exist.")

    points = []
    with open(file_path, "r") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 2:
                raise ValueError(
                    f"Line {line_no} is invalid: expected 'x y' but got '{line}'.")
            try:
                x, y = float(parts[0]), float(parts[1])
            except ValueError:
                raise ValueError(
                    f"Line {line_no} contains non-numeric values: '{line}'.")
            points.append(Point(x, y))

    if len(points) < 2:
        raise ValueError("The file must contain at least 2 points.")
    return points


def format_number(value):
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")



# GUI
class ClosestPairApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Closest Pair of Points")
        self.geometry("480x330")
        self.resizable(False, False)
        self.configure(padx=20, pady=20)

        tk.Label(
            self, text="Closest Pair of Points",
            font=("Helvetica", 16, "bold")
        ).pack(pady=(0, 4))
        tk.Label(
            self,
            text="Select a .txt file with one point per line (x y)",
            fg="#555555"
        ).pack(pady=(0, 14))

        # File selection row
        row = tk.Frame(self)
        row.pack(fill="x")
        self.path_var = tk.StringVar(value="No file selected")
        tk.Label(
            row, textvariable=self.path_var, anchor="w",
            relief="sunken", bd=1, padx=6, pady=4
        ).pack(side="left", fill="x", expand=True)
        tk.Button(row, text="Browse...", command=self.browse).pack(
            side="left", padx=(8, 0)
        )

        self.run_btn = tk.Button(
            self, text="Find Closest Distance", command=self.run,
            state="disabled", pady=6
        )
        self.run_btn.pack(fill="x", pady=14)

        # Results
        results = tk.LabelFrame(self, text="Results", padx=12, pady=10)
        results.pack(fill="both", expand=True)

        self.count_var = tk.StringVar(value="—")
        self.dist_var = tk.StringVar(value="—")

        tk.Label(results, text="Number of points:", anchor="w").grid(
            row=0, column=0, sticky="w", pady=4
        )
        tk.Label(
            results, textvariable=self.count_var,
            font=("Helvetica", 12, "bold")
        ).grid(row=0, column=1, sticky="w", padx=10)

        tk.Label(results, text="Closest distance:", anchor="w").grid(
            row=1, column=0, sticky="w", pady=4
        )
        tk.Label(
            results, textvariable=self.dist_var,
            font=("Helvetica", 12, "bold")
        ).grid(row=1, column=1, sticky="w", padx=10)

        self.file_path = None

    def browse(self):
        path = filedialog.askopenfilename(
            title="Select a text file",
            filetypes=[("Text files", "*.txt")]
        )
        if not path:
            return
        if not path.lower().endswith(".txt"):
            messagebox.showerror("Invalid file", "Only .txt files are allowed.")
            return
        self.file_path = path
        self.path_var.set(os.path.basename(path))
        self.run_btn.config(state="normal")
        self.count_var.set("—")
        self.dist_var.set("—")

    def run(self):
        try:
            points = load_points(self.file_path)
        except ValueError as e:
            messagebox.showerror("Invalid file", str(e))
            return
        except Exception as e:
            messagebox.showerror("Error", f"Could not read file:\n{e}")
            return

        px = sorted(points, key=lambda p: p.x)
        py = sorted(points, key=lambda p: p.y)
        result = closest_pair(px, py)

        self.count_var.set(str(len(points)))
        self.dist_var.set(format_number(result))


if __name__ == "__main__":
    ClosestPairApp().mainloop()