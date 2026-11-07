// Builds report/DAA_Project_Report.docx from results/benchmark_results.csv
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, AlignmentType,
  WidthType, ShadingType, BorderStyle, LevelFormat, HeadingLevel,
} = require("docx");

const ROOT = path.resolve(__dirname, "..", "..");
const csv = fs.readFileSync(path.join(ROOT, "results", "benchmark_results.csv"), "utf8").trim().split(/\r?\n/);
const head = csv[0].split(",");
const rows = csv.slice(1).map((line) => {
  const cells = []; let cur = ""; let q = false;
  for (const ch of line) {
    if (ch === '"') q = !q; else if (ch === "," && !q) { cells.push(cur); cur = ""; } else cur += ch;
  }
  cells.push(cur);
  const o = {}; head.forEach((h, i) => (o[h] = cells[i])); return o;
});
const cp = rows.filter((r) => r.algorithm === "Closest Pair");
const ks = rows.filter((r) => r.algorithm === "Karatsuba");

// dataset details (computed by the python helper)
const ds = JSON.parse(fs.readFileSync(path.join(__dirname, "datasets.json"), "utf8"));

const FONT = "Calibri";
const SZ = 19; // 9.5 pt
const r = (text, o = {}) => new TextRun({ text, font: FONT, size: SZ, ...o });
const P = (children, o = {}) => new Paragraph({
  children: typeof children === "string" ? [r(children)] : children,
  spacing: { after: 70, line: 252 }, alignment: AlignmentType.JUSTIFIED, ...o,
});
const H = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text })] });
const bullet = (children) => new Paragraph({
  numbering: { reference: "b", level: 0 }, spacing: { after: 30, line: 245 },
  alignment: AlignmentType.JUSTIFIED, children: typeof children === "string" ? [r(children)] : children,
});

const border = { style: BorderStyle.SINGLE, size: 4, color: "B8BFCC" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(widths, header, body, opts = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (t, w, isHead, fill) => new TableCell({
    width: { size: w, type: WidthType.DXA }, borders,
    shading: isHead ? { fill: "E7E6FD", type: ShadingType.CLEAR, color: "auto" }
      : (fill ? { fill, type: ShadingType.CLEAR, color: "auto" } : undefined),
    margins: { top: 20, bottom: 20, left: 50, right: 50 },
    children: [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 0 },
      children: [new TextRun({ text: t, font: FONT, size: opts.size || 15, bold: isHead })] })],
  });
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: header.map((t, i) => cell(t, widths[i], true)) }),
      ...body.map((row, ri) => new TableRow({
        children: row.map((t, i) => cell(t, widths[i], false, ri % 2 ? "F6F7FA" : undefined)) }))],
  });
}
const caption = (t) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 40, after: 90 },
  children: [r(t, { italics: true, size: 16, color: "444444" })] });

const ms = (v) => { const x = parseFloat(v); return x < 0.01 ? x.toFixed(4) : x < 10 ? x.toFixed(3) : x.toFixed(1); };
const fmtd = (v) => v;

// ---------------- content
const children = [];
children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 },
  children: [new TextRun({ text: "Visualizing Divide-and-Conquer: Closest Pair of Points and Karatsuba Integer Multiplication",
    font: FONT, size: 30, bold: true, color: "1F2A44" })] }));
children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 20 },
  children: [r("Daneya Shafiq (24K-3037)  ·  Erfa Kashif (24K-3010)  ·  Anshrah Shafique (24K-3092)", { bold: true })] }));
children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "4F46E5", space: 4 } },
  children: [r("Design and Analysis of Algorithms – Course Project", { italics: true, color: "555555" })] }));

children.push(H("Abstract"));
children.push(P("This project studies two classical divide-and-conquer (D&C) algorithms – the closest pair of points " +
  "problem and Karatsuba’s fast integer multiplication – through a working desktop application. Both algorithms were " +
  "written in Python and are used exactly as implemented by the group; a thin recording layer observes every recursive " +
  "call without altering the code. A Tkinter interface lets the user pick any input file and then watch the recursion: " +
  "dividing lines and the δ-strip on a scatter plot for the geometric problem, and an interactive recursion tree with " +
  "split/conquer/combine panels for multiplication. Twenty input files (ten per problem) were processed; all twenty answers " +
  "matched an independent baseline, and the measured growth agrees with the theoretical O(n log n) and O(n^1.585) bounds."));

children.push(H("1. Introduction"));
children.push(P("Divide and conquer solves a problem by breaking it into smaller instances of itself, solving those " +
  "recursively and merging the partial answers. Its benefit is easiest to appreciate when the naive method is quadratic. " +
  "Finding the two nearest points among n points by checking every pair costs Θ(n²) distance evaluations, while the " +
  "Shamos–Hoey style recursion reduces this to O(n log n) by proving that, after the two halves are solved, only a narrow " +
  "vertical strip needs re-examination and each strip point has at most seven relevant neighbours [2]. Likewise, the " +
  "school method multiplies two n-digit numbers with Θ(n²) digit products, whereas Karatsuba observed that the cross term " +
  "ad + bc can be obtained from one extra product, (a+b)(c+d) − ac − bd, so only three half-size multiplications are " +
  "required, giving T(n) = 3T(n/2) + O(n) = O(n^log₂3) [3]."));
children.push(P("Recursion is hard to follow on paper, so the aim of this work is a tool that executes the real " +
  "implementations on user-chosen data and exposes each divide, conquer and combine step visually, while also " +
  "benchmarking the algorithms and checking every answer for correctness."));

children.push(H("2. Proposed System"));
children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 0 }, children: [new ImageRun({
  type: "png", data: fs.readFileSync(path.join(__dirname, "system_diagram.png")),
  transformation: { width: 640, height: 227 } })] }));
children.push(caption("Figure 1. Architecture of the proposed system."));
children.push(P("The system (Figure 1) is a Python 3 / Tkinter program organised in four layers:"));
children.push(bullet([r("Input layer. ", { bold: true }), r("Plain-text files. A closest-pair file holds one “x y” " +
  "point per line; a Karatsuba file holds two integers on separate lines. Files are listed from the datasets folder, " +
  "and any other file can be opened with Browse – its type is detected automatically from its first lines.")]));
children.push(bullet([r("Algorithm layer. ", { bold: true }), r("The group’s original functions closest_pair(), " +
  "brute_force(), distance(), load_points() and karatsuba() were copied verbatim into the algorithms package; the " +
  "untouched source files are also kept in original_code/.")]));
children.push(bullet([r("Recording layer (core.py). ", { bold: true }), r("Because each original function calls itself " +
  "through its global name, temporarily replacing that name with a wrapper lets every recursive call pass through a " +
  "recorder that stores its arguments, depth and return value and then calls the real function. The print() trace " +
  "produced by karatsuba() is captured instead of being lost in the console. Timings are taken from separate, un-wrapped runs.")]));
children.push(bullet([r("Presentation layer (gui.py). ", { bold: true }), r("A sidebar for choosing the algorithm and " +
  "file, and two tabs. The Closest Pair tab animates the recorded calls (Play/Step/Finish with adjustable speed): the " +
  "current sub-problem, the median line, the 2δ strip and the best pair of every call, ending with the global closest " +
  "pair. The Karatsuba tab shows a lazily expanded recursion tree; selecting a call draws its split into a, b, c, d, the " +
  "three sub-products w, y, z and the reconstruction w·10^2h + z·10^h + y, with a walk-through mode and a calls-per-level " +
  "chart. Each tab shows the answer, its running time and whether it matches an independent check. A separate script, " +
  "run_benchmarks.py, applies both algorithms to all 20 files and saves the timings to a CSV file.")]));

children.push(H("3. Experimental Setup"));
children.push(P("Experiments were run with Python 3.12 on a Linux x86-64 machine. Each algorithm was run once without " +
  "recording for timing (time.perf_counter); Karatsuba’s print statements were redirected to os.devnull so that console " +
  "output does not dominate the measurement. Closest-pair answers were checked against the original O(n²) brute_force(), " +
  "and Karatsuba products against Python’s built-in integer multiplication. Files karatsuba_input_2–4 and " +
  "testcase8–10 hold random values that we generated once and saved as fixed text files; the rest were written by the group. Table 1 lists every input."));
const t1 = [];
for (let i = 0; i < 10; i++) {
  const a = ds.closest[i], b = ds.karatsuba[i];
  t1.push([a.file, String(a.n), a.xr, a.yr, a.sample, b.file, String(b.digits), b.n10 + "…", b.m10 + "…"]);
}
children.push(table([1050, 520, 1000, 1050, 1500, 1650, 560, 1150, 1150],
  ["Closest-pair file", "Points", "x range", "y range", "First point(s)", "Karatsuba file", "Digits", "N begins", "M begins"], t1));
children.push(caption("Table 1. Input datasets (testcase1–4 are the same 1450-point grid with duplicate points; testcase5–7 are 10-point hand-made cases)."));

children.push(H("4. Results and Discussion"));
const t2 = [];
for (let i = 0; i < 10; i++) {
  const a = cp[i], b = ks[i];
  t2.push([a.file, fmtd(a.result), a.detail, ms(a.time_ms), ms(a.baseline_ms), a.verified === "True" ? "✔" : "✘",
    b.file, b.result.replace("-digit product", ""), ms(b.time_ms), Number(b.calls).toLocaleString("en-US"),
    b.verified === "True" ? "✔" : "✘"]);
}
children.push(table([1060, 800, 1950, 620, 640, 360, 1650, 560, 680, 720, 360],
  ["File", "δ", "Closest pair", "D&C ms", "Brute ms", "OK", "Karatsuba file", "Digits out", "Time ms", "Calls", "OK"], t2));
children.push(caption("Table 2. Benchmark results. All 20 outputs agree with the baseline."));
const c8 = cp[7], c10 = cp[9], k4 = ks[3], k10 = ks[9];
children.push(P([r("Correctness. ", { bold: true }), r("Every closest distance equals the brute-force minimum and every " +
  "Karatsuba product equals the built-in product (Table 2), so the implementations are correct on all files, including " +
  "edge cases such as duplicate points (δ = 0 in testcase1–4), vertical alignments (testcase5) and odd digit lengths " +
  "(products of 999 and 1399 digits).")]));
children.push(P([r("Closest pair. ", { bold: true }), r(`The D&C version beats the quadratic baseline once n is no longer tiny: ` +
  `${ms(c8.time_ms)} ms vs ${ms(c8.baseline_ms)} ms for 200 points and ${ms(c10.time_ms)} ms vs ${ms(c10.baseline_ms)} ms ` +
  `for 1000 points (about ${Math.round(c10.baseline_ms / c10.time_ms)}× faster). For 10 points the brute force wins because ` +
  `sorting and recursion overhead outweigh 45 comparisons. The number of calls stays close to n (975 calls for 1000 points), ` +
  `as expected for a balanced recursion that stops at n ≤ 3, and the recursion depth grows as log₂ n.`)]));
children.push(P([r("Karatsuba. ", { bold: true }), r(`When the operand size triples from 300 to 900 digits, the number of ` +
  `recursive calls grows from ${Number(k4.calls).toLocaleString("en-US")} to ${Number(k10.calls).toLocaleString("en-US")} ` +
  `(${(k10.calls / k4.calls).toFixed(1)}×) and time from ${ms(k4.time_ms)} ms to ${ms(k10.time_ms)} ms ` +
  `(${(k10.time_ms / k4.time_ms).toFixed(1)}×), close to the predicted 3^1.585 ≈ 5.7× and well below the 9× of the ` +
  `school method. The calls-per-level chart confirms the 1, 3, 9, 27 … pattern of three sub-problems per call. Python’s ` +
  `own multiplication is far faster in absolute terms because it is implemented in C and itself switches to Karatsuba ` +
  `for large operands; our pure-Python version also pays for converting numbers to strings to count digits.`)]));

children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60, after: 0 }, children: [
  new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "ui_cp_final.png")), transformation: { width: 318, height: 187 } }),
  new TextRun({ text: "  " }),
  new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "ui_ks_child.png")), transformation: { width: 318, height: 187 } }),
] }));
children.push(caption("Figure 2. The interface: closest pair found for testcase8 (left) and one Karatsuba call opened from the recursion tree for karatsuba_input_2 (right)."));

children.push(H("5. Conclusion"));
children.push(P("We built a complete, interactive environment in which the group’s own closest-pair and Karatsuba " +
  "implementations are executed unchanged on any valid input file and their recursion is visualised step by step. " +
  "Across 20 datasets every result was verified, and the measurements reproduce the theoretical advantage of " +
  "divide and conquer: near-linear growth for the closest pair against quadratic brute force, and roughly n^1.585 growth " +
  "for Karatsuba. Future work could add larger random point clouds, a digit-list Karatsuba that avoids big-integer " +
  "shortcuts, and export of the animations for teaching."));

children.push(H("References"));
const refs = [
  "T. H. Cormen, C. E. Leiserson, R. L. Rivest and C. Stein, Introduction to Algorithms, 4th ed. MIT Press, 2022.",
  "M. I. Shamos and D. Hoey, “Closest-point problems,” in Proc. 16th IEEE Symp. Foundations of Computer Science, 1975, pp. 151–162.",
  "A. Karatsuba and Yu. Ofman, “Multiplication of multidigit numbers on automata,” Soviet Physics Doklady, vol. 7, pp. 595–596, 1963.",
  "J. Kleinberg and É. Tardos, Algorithm Design. Pearson/Addison-Wesley, 2006, ch. 5.",
  "Python Software Foundation, “tkinter – Python interface to Tcl/Tk,” Python 3 documentation, docs.python.org.",
];
refs.forEach((t, i) => children.push(new Paragraph({ spacing: { after: 20 }, indent: { left: 360, hanging: 360 },
  children: [r(`[${i + 1}]  ${t}`, { size: 17 })] })));

const doc = new Document({
  creator: "Daneya Shafiq, Erfa Kashif, Anshrah Shafique",
  title: "DAA Project Report",
  styles: {
    default: { document: { run: { font: FONT, size: SZ } } },
    paragraphStyles: [{
      id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { font: FONT, size: 23, bold: true, color: "3730A3" },
      paragraph: { spacing: { before: 110, after: 50 }, keepNext: true, outlineLevel: 0 },
    }],
  },
  numbering: { config: [{ reference: "b", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
    alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 300, hanging: 200 } } } }] }] },
  sections: [{ properties: { page: { size: { width: 11906, height: 16838 },
    margin: { top: 850, bottom: 850, left: 850, right: 850 } } }, children }],
});
Packer.toBuffer(doc).then((buf) => {
  const out = path.join(ROOT, "report", "DAA_Project_Report.docx");
  fs.writeFileSync(out, buf); console.log("wrote", out);
});
