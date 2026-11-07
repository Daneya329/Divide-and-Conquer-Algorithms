import os
import tkinter as tk
from tkinter import ttk,messagebox
def karatsuba(n, m, depth=0):
    # Visual indentation helper for recursion tracking
    indent = "  " * depth
    # Base case for single-digit multiplication
    if n < 10 or m < 10:
        print(f"{indent}▶  Base Case reached: {n} * {m} = {n * m}")
        return n * m
    num_digits = max(len(str(n)), len(str(m)))
    half = (num_digits + 1) // 2
    split = 10 ** half
    # Split the numbers into high and low parts
    a = n // split
    b = n % split
    c = m // split
    d = m % split
    # PRINT 1: Show how the numbers are split at this level
    print(f"\n{indent}▶  Level {depth}: Multiplying {n} x {m}")
    print(f"{indent}   Split point (10^{half}):")
    print(f"{indent}   n -> a = {a}, b = {b}")
    print(f"{indent}   m -> c = {c}, d = {d}")
    # Recursive steps
    print(f"{indent}   [Recurse] Calculating w = karatsuba(a, c)...")
    w = karatsuba(a, c, depth + 1)
    print(f"{indent}   [Recurse] Calculating y = karatsuba(b, d)...")
    y = karatsuba(b, d, depth + 1)
    print(f"{indent}   [Recurse] Calculating z = karatsuba(a+b, c+d)...")
    z = karatsuba((a + b), (c + d), depth + 1) - w - y
    # Calculate reconstruction components for explicit presentation
    high_term = w * (10 ** (2 * half))
    mid_term = z * (10 ** half)
    final_result = high_term + mid_term + y
    # PRINT 2: Show the exact reconstruction equation back up the tree
    print(f"{indent}▶  Level {depth} Reconstruction Equation:")
    print(f"{indent}   Formula: (w * 10^{2 * half}) + (z * 10^{half}) + y")
    print(f"{indent}   Values:  ({w} * {10 ** (2 * half)}) + ({z} * {10 ** half}) + {y}")
    print(f"{indent}   Sum:     {high_term} + {mid_term} + {y} = {final_result}")
    return final_result

# =====================================================================
# USER INTERFACE: TKINTER INTEGRATION
# =====================================================================
class KaratsubaRunnerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DAA Project - Karatsuba Integer Multiplication")
        self.root.geometry("750x600")
        self.root.minsize(600, 500)

        # Configure layout styles
        style = ttk.Style()
        style.theme_use('clam')

        # State variable for the dropdown menu
        self.selected_file = tk.StringVar()

        self.create_widgets()
        self.load_dataset_menu()

    def create_widgets(self):
        # --- Top Section: Dataset Selection Menu ---
        top_frame = ttk.LabelFrame(self.root, text="Select Karatsuba Input File ", padding=15)
        top_frame.pack(fill="x", padx=15, pady=15)

        ttk.Label(top_frame, text="Available Datasets:").pack(side="left", padx=5)

        # This dropdown menu list holds the files found in the directory
        self.file_menu = ttk.Combobox(top_frame, textvariable=self.selected_file, state="readonly", width=45)
        self.file_menu.pack(side="left", padx=5)

        btn_load = ttk.Button(top_frame, text="Load & Run Karatsuba", command=self.process_and_run)
        btn_load.pack(side="left", padx=10)

        # --- Bottom Section: Display Layout Workspace ---
        display_frame = ttk.LabelFrame(self.root, text=" 🖥️ Workspace Visualizer ", padding=15)
        display_frame.pack(fill="both", expand=True, padx=15, pady=10)

        # Preview pane showing what the inputs are
        ttk.Label(display_frame, text="Dataset Preview (Truncated text if too large):").pack(anchor="w")
        self.txt_input = tk.Text(display_frame, height=6, wrap="char", background="#f8f9fa")
        self.txt_input.pack(fill="x", pady=5)

        # Output pane showing calculation results
        ttk.Label(display_frame, text="Computed Product Output:").pack(anchor="w", pady=(10, 0))
        self.txt_output = tk.Text(display_frame, height=10, wrap="char", background="#e9ecef",
                                  font=("Courier", 11, "bold"))
        self.txt_output.pack(fill="both", expand=True, pady=5)

    def load_dataset_menu(self):
        """Scans the dataset folder dynamically to populate the dropdown menu menu"""
        folder = "karatsuba_datasets"
        if os.path.exists(folder):
            # Grab all text files in the target directory
            files = [f for f in os.listdir(folder) if f.endswith('.txt')]
            # Simple sorting logic to organize files numerically (input_1.txt before input_10.txt)
            try:
                files.sort(key=lambda x: int(''.join(filter(str.isdigit, x))))
            except ValueError:
                files.sort()

            # Form complete path targets
            paths = [os.path.join(folder, f) for f in files]
            self.file_menu['values'] = paths

            if paths:
                self.selected_file.set(paths[0])  # Default to the first file
            else:
                self.selected_file.set("")
                self.file_menu['values'] = ["No text files found in folder"]
        else:
            self.file_menu['values'] = [f"Directory '{folder}/' missing! Run generator script first."]
            self.selected_file.set(self.file_menu['values'][0])

    def process_and_run(self):
        filepath = self.selected_file.get()

        # Safety validation checks
        if not filepath or not os.path.exists(filepath) or "missing" in filepath or "No text" in filepath:
            messagebox.showerror("Error", "Please select a valid dataset file path from the menu options.")
            return

        # Clean workspace views
        self.txt_input.delete("1.0", tk.END)
        self.txt_output.delete("1.0", tk.END)

        try:
            # Read input dataset
            with open(filepath, "r") as f:
                raw_data = f.read().strip()

            # Display truncated version of the raw digits in preview panel (Up to 300 chars)
            self.txt_input.insert(tk.END, raw_data[:300] + (
                "\n... [TRUNCATED FOR SCREEN DISPLAY]" if len(raw_data) > 300 else ""))

            # Extract the numbers from lines
            lines = raw_data.splitlines()
            if len(lines) < 2:
                raise ValueError("The selected text file format must have two numbers on separate lines.")

            n = int(lines[0].strip())
            m = int(lines[1].strip())

            # Run calculation
            # Run calculation with clean trace printing to the terminal/IDE console
            print("\n" + "=" * 60)
            print("STARTING KARATSUBA RECURSION TRACE VISUALIZER")
            print("=" * 60)

            calculated_product = karatsuba(n, m, depth=0)

            print("\n" + "=" * 60)
            print("END OF RECURSION TRACE")
            print("=" * 60)

            # Format UI summary report
            report = f"SUCCESS: Karatsuba Algorithm Executed\n"
            report += f"--------------------------------------------------\n"
            report += f"Multiplicand (N): {len(lines[0])} digits\n"
            report += f"Multiplier   (M): {len(lines[1])} digits\n"
            report += f"--------------------------------------------------\n"
            report += f"Product:\n{calculated_product}\n"

            self.txt_output.insert(tk.END, report)

        except Exception as e:
            messagebox.showerror("Execution Error", f"Failed to parse and calculate input numbers:\n{str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = KaratsubaRunnerApp(root)
    root.mainloop()