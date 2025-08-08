# rect_packer_gui_multibin.py
# Axis-aligned rectangle packer (0°/90°) with:
# - Inner margin (gap between parts)
# - Kerf (blade thickness) -> counted as extra spacing (half on each piece)
# - Edge margin (trim from bin border)
# - Multi-bin packing (pack all items into multiple sheets)
# - Post-fill (MaxRects): after initial pass, try to fill leftover items (small-first) into remaining space
# - Import CSV (w,h[,qty][,id]), Export JSON
# - Preview each bin with colors, top-left origin toggle
#
# NOTE: Post-fill is implemented for MaxRects algorithms (BSSF/BAF). For BL/Skyline, standard packing is used.
#
from dataclasses import dataclass
from typing import List, Optional, Tuple, Literal, Dict, Any
import json, math, random, csv, io
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Rectangle as MplRect
import matplotlib.cm as cm


# ----------------------- Data types -----------------------

@dataclass
class Rect:
    w: float
    h: float
    rid: int

@dataclass
class PlacedRect:
    x: float
    y: float
    w: float
    h: float
    rid: int
    rotated: bool
    draw_x: float = 0.0
    draw_y: float = 0.0
    draw_w: float = 0.0
    draw_h: float = 0.0

@dataclass
class Node:
    x: float
    y: float
    w: float
    h: float


# ----------------------- Algorithms -----------------------

class MaxRectsBin:
    def __init__(self, width: float, height: float, allow_rotate_90: bool = True):
        self.W = width; self.H = height
        self.allow_rotate = allow_rotate_90
        self.used: List[PlacedRect] = []
        self.free: List[Node] = [Node(0,0,width,height)]

    def insert(self, rect: Rect, mode: Literal["bssf","baf"]="bssf") -> Optional[PlacedRect]:
        best = self._find(rect.w, rect.h, rotated=False, mode=mode)
        if best is None and self.allow_rotate:
            best = self._find(rect.h, rect.w, rotated=True, mode=mode)
        if best is None:
            return None
        p = PlacedRect(best[0], best[1], best[2], best[3], rect.rid, rotated=best[4])
        self._place(p)
        return p

    def _find(self, w: float, h: float, rotated: bool, mode: str):
        bestA = math.inf; bestB = math.inf; best = None
        for fr in self.free:
            if w <= fr.w and h <= fr.h:
                dw, dh = fr.w - w, fr.h - h
                if mode == "bssf":
                    A = min(dw, dh); B = max(dw, dh)
                elif mode == "baf":
                    A = fr.w*fr.h - w*h; B = abs(dw - dh)
                else:
                    raise ValueError("mode?")
                if A < bestA or (A == bestA and B < bestB):
                    bestA, bestB = A, B
                    best = (fr.x, fr.y, w, h, rotated)
        return best

    def _place(self, used: PlacedRect):
        i = 0
        while i < len(self.free):
            if self._split(self.free[i], used):
                self.free.pop(i); i -= 1
            i += 1
        self._prune()
        self.used.append(used)

    @staticmethod
    def _overlap(u: PlacedRect, n: Node) -> bool:
        return not (u.x >= n.x+n.w or u.x+u.w <= n.x or u.y >= n.y+n.h or u.y+u.h <= n.y)

    def _split(self, free: Node, used: PlacedRect) -> bool:
        if not self._overlap(used, free): return False
        # split along X
        if used.x > free.x and used.x < free.x + free.w:
            self.free.append(Node(free.x, free.y, used.x - free.x, free.h))
        if used.x + used.w < free.x + free.w:
            self.free.append(Node(used.x + used.w, free.y, (free.x + free.w) - (used.x + used.w), free.h))
        # split along Y
        if used.y > free.y and used.y < free.y + free.h:
            self.free.append(Node(free.x, free.y, free.w, used.y - free.y))
        if used.y + used.h < free.y + free.h:
            self.free.append(Node(free.x, used.y + used.h, free.w, (free.y + free.h) - (used.y + used.h)))
        return True

    def _prune(self):
        i = 0
        while i < len(self.free):
            j = i + 1
            while j < len(self.free):
                if self._contained(self.free[i], self.free[j]):
                    self.free.pop(i); i -= 1; break
                if self._contained(self.free[j], self.free[i]):
                    self.free.pop(j); j -= 1
                j += 1
            i += 1

    @staticmethod
    def _contained(a: Node, b: Node) -> bool:
        return a.x >= b.x and a.y >= b.y and a.x+a.w <= b.x+b.w and a.y+a.h <= b.y+b.h


class BottomLeftBin:
    def __init__(self, width: float, height: float, allow_rotate_90: bool = True):
        self.W = width; self.H = height
        self.allow_rotate = allow_rotate_90
        self.placed: List[PlacedRect] = []

    def insert(self, rect: Rect) -> Optional[PlacedRect]:
        best: Optional[PlacedRect] = None
        for rot in ([False, True] if self.allow_rotate else [False]):
            w, h = (rect.h, rect.w) if rot else (rect.w, rect.h)
            xs = [0.0] + [p.x for p in self.placed] + [p.x+p.w for p in self.placed]
            xs = [x for x in xs if x + w <= self.W]
            for x in xs:
                y = self._lowest_y(x, w, h)
                if y is None: continue
                cand = PlacedRect(x, y, w, h, rect.rid, rotated=rot)
                if best is None or (cand.y < best.y) or (cand.y == best.y and cand.x < best.x):
                    best = cand
        if best: self.placed.append(best)
        return best

    def _lowest_y(self, x: float, w: float, h: float) -> Optional[float]:
        y = 0.0
        while y + h <= self.H:
            if all(x+w <= p.x or x >= p.x+p.w or y+h <= p.y or y >= p.y+p.h for p in self.placed):
                return y
            for p in self.placed:
                if not (x+w <= p.x or x >= p.x+p.w or y+h <= p.y or y >= p.y+p.h):
                    y = p.y + p.h; break
        return None


class SkylineBin:
    def __init__(self, width: float, height: float, allow_rotate_90: bool = True):
        self.W = width; self.H = height
        self.allow_rotate = allow_rotate_90
        self.sky = [(0.0, 0.0, width)]  # (x, y, seg_w)
        self.placed: List[PlacedRect] = []

    def insert(self, rect: Rect) -> Optional[PlacedRect]:
        best = None
        for rot in ([False, True] if self.allow_rotate else [False]):
            w, h = (rect.h, rect.w) if rot else (rect.w, rect.h)
            i, x, y = self._find(w)
            if i is not None and y + h <= self.H:
                cand = (i, x, y, w, h, rot)
                if best is None or (y < best[2]) or (y == best[2] and x < best[1]):
                    best = cand
        if best is None: return None
        i, x, y, w, h, rot = best
        self._add_level(i, x, y, w, h)
        p = PlacedRect(x, y, w, h, rect.rid, rotated=rot)
        self.placed.append(p)
        return p

    def _find(self, w: float):
        best_y = math.inf; best_x = 0.0; best_i = None
        for i, (sx, sy, sw) in enumerate(self.sky):
            if sw >= w:
                y = self._y_over(i, sx, w)
                if y < best_y or (y == best_y and sx < best_x):
                    best_y = y; best_x = sx; best_i = i
        return best_i, best_x, best_y

    def _y_over(self, idx: int, x: float, w: float):
        end = x + w; y = self.sky[idx][1]; i = idx; cur = x
        while cur < end and i < len(self.sky):
            sx, sy, sw = self.sky[i]
            if sx + sw > cur:
                y = max(y, sy); cur = min(end, sx + sw)
            i += 1
        return y

    def _add_level(self, idx: int, x: float, y: float, w: float, h: float):
        self.sky.insert(idx, (x, y+h, w))
        i = idx + 1; end = x + w
        while i < len(self.sky):
            sx, sy, sw = self.sky[i]
            if sx < end:
                overlap = min(sw, end - sx)
                nx, nw = sx + overlap, sw - overlap
                if nw <= 1e-9: self.sky.pop(i); continue
                else: self.sky[i] = (nx, sy, nw)
            else: break
            i += 1
        i = 0
        while i < len(self.sky) - 1:
            x1, y1, w1 = self.sky[i]; x2, y2, w2 = self.sky[i+1]
            if abs((x1+w1) - x2) < 1e-9 and abs(y1 - y2) < 1e-9:
                self.sky[i] = (x1, y1, w1 + w2); self.sky.pop(i+1)
            else:
                i += 1


# ----------------------- Packing wrappers -----------------------

def inflate_rects_for_spacing(rects: List[Rect], inner_margin: float, kerf: float) -> List[Rect]:
    # Effective spacing per side is (inner_margin + kerf/2)
    s = inner_margin + kerf/2.0
    return [Rect(r.w + 2*s, r.h + 2*s, r.rid) for r in rects], s

def deflate_draw(p: PlacedRect, spacing_per_side: float, edge_margin: float):
    p.draw_x = p.x + spacing_per_side + edge_margin
    p.draw_y = p.y + spacing_per_side + edge_margin
    p.draw_w = max(0.0, p.w - 2*spacing_per_side)
    p.draw_h = max(0.0, p.h - 2*spacing_per_side)


def pack_single_bin_maxrects_postfill(binW: float, binH: float, rects: List[Rect],
                                      inner_margin: float, edge_margin: float, kerf: float,
                                      allow_rotate_90: bool, mode: Literal["bssf","baf"]="baf") -> Tuple[List[PlacedRect], List[Rect]]:
    # Work area after edge margins
    W = max(0.0, binW - 2*edge_margin)
    H = max(0.0, binH - 2*edge_margin)
    inflated, space = inflate_rects_for_spacing(rects, inner_margin, kerf)

    order = sorted(inflated, key=lambda r: r.w*r.h, reverse=True)
    mr = MaxRectsBin(W, H, allow_rotate_90)

    placed: List[PlacedRect] = []
    failed: List[Rect] = []

    # pass 1: big -> small
    for r in order:
        p = mr.insert(r, mode=mode)
        if p is None:
            failed.append(r)
        else:
            deflate_draw(p, space, edge_margin)
            placed.append(p)

    # post-fill: try to insert failed items small -> big
    changed = True
    while changed:
        changed = False
        new_failed: List[Rect] = []
        for r in sorted(failed, key=lambda t: t.w*t.h):  # smallest first
            p = mr.insert(r, mode=mode)
            if p is None:
                new_failed.append(r)
            else:
                deflate_draw(p, space, edge_margin)
                placed.append(p)
                changed = True
        failed = new_failed

    # map failed back to original sizes (approx by removing inflation)
    remaining: List[Rect] = []
    for r in failed:
        remaining.append(Rect(r.w - 2*space, r.h - 2*space, r.rid))
    return placed, remaining


def pack_single_bin_algo(binW: float, binH: float, rects: List[Rect],
                         inner_margin: float, edge_margin: float, kerf: float,
                         algo: Literal["maxrects-bssf","maxrects-baf","bottom-left","skyline-bl"],
                         allow_rotate_90: bool) -> Tuple[List[PlacedRect], List[Rect]]:
    if algo.startswith("maxrects"):
        mode = "bssf" if algo.endswith("bssf") else "baf"
        return pack_single_bin_maxrects_postfill(binW, binH, rects, inner_margin, edge_margin, kerf, allow_rotate_90, mode=mode)

    # For BL/Skyline (no post-fill, but still supports margins/kerf/edge)
    W = max(0.0, binW - 2*edge_margin)
    H = max(0.0, binH - 2*edge_margin)
    inflated, space = inflate_rects_for_spacing(rects, inner_margin, kerf)
    order = sorted(inflated, key=lambda r: r.w*r.h, reverse=True)

    placed: List[PlacedRect] = []; failed: List[Rect] = []
    if algo == "bottom-left":
        bl = BottomLeftBin(W, H, allow_rotate_90)
        for r in order:
            p = bl.insert(r)
            if p is None: failed.append(r)
            else:
                deflate_draw(p, space, edge_margin); placed.append(p)
    else:
        sk = SkylineBin(W, H, allow_rotate_90)
        for r in order:
            p = sk.insert(r)
            if p is None: failed.append(r)
            else:
                deflate_draw(p, space, edge_margin); placed.append(p)

    remaining = [Rect(r.w - 2*space, r.h - 2*space, r.rid) for r in failed]
    return placed, remaining


def pack_multiple_bins(binW: float, binH: float, rects: List[Rect], inner_margin: float, edge_margin: float,
                       kerf: float, allow_rotate_90: bool, algo: str, max_bins: int, seed: int = 42):
    rnd = random.Random(seed)
    remaining = rects[:]
    bins: List[Dict[str, Any]] = []
    b = 0
    while remaining and (max_bins <= 0 or b < max_bins):
        placed, remaining = pack_single_bin_algo(binW, binH, remaining, inner_margin, edge_margin, kerf, algo, allow_rotate_90)
        used_area = sum(p.draw_w*p.draw_h for p in placed)
        fill = used_area / (binW*binH) * 100 if binW*binH > 0 else 0.0
        bins.append({"placed": placed, "fill": fill})
        b += 1
        # optional shuffle between bins to avoid pathological order lock-in
        rnd.shuffle(remaining)
        # break if no item placed this round (avoid infinite loop)
        if not placed:
            break
    return bins, remaining


# ----------------------- GUI -----------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Multi-bin Rectangle Packer — Kerf + Post-fill (MaxRects)")
        self.geometry("1200x760")

        frm = ttk.LabelFrame(self, text="Parameters"); frm.pack(side=tk.TOP, fill=tk.X, padx=8, pady=6)
        self.var_W = tk.StringVar(value="500")
        self.var_H = tk.StringVar(value="300")
        self.var_inner = tk.StringVar(value="1")     # gap between parts (per side)
        self.var_edge = tk.StringVar(value="0")      # trim from sheet border
        self.var_kerf = tk.StringVar(value="0")      # blade thickness
        self.var_rotate = tk.BooleanVar(value=True)
        self.var_algo = tk.StringVar(value="maxrects-baf")
        self.var_top_left = tk.BooleanVar(value=False)
        self.var_maxbins = tk.StringVar(value="0")   # 0 = unlimited

        ttk.Label(frm, text="Bin W").grid(row=0, column=0, padx=4, pady=4, sticky="e")
        ttk.Entry(frm, width=8, textvariable=self.var_W).grid(row=0, column=1, padx=4, pady=4)
        ttk.Label(frm, text="Bin H").grid(row=0, column=2, padx=4, pady=4, sticky="e")
        ttk.Entry(frm, width=8, textvariable=self.var_H).grid(row=0, column=3, padx=4, pady=4)

        ttk.Label(frm, text="Inner margin").grid(row=0, column=4, padx=4, pady=4, sticky="e")
        ttk.Entry(frm, width=6, textvariable=self.var_inner).grid(row=0, column=5, padx=4, pady=4)
        ttk.Label(frm, text="Edge margin").grid(row=0, column=6, padx=4, pady=4, sticky="e")
        ttk.Entry(frm, width=6, textvariable=self.var_edge).grid(row=0, column=7, padx=4, pady=4)
        ttk.Label(frm, text="Kerf").grid(row=0, column=8, padx=4, pady=4, sticky="e")
        ttk.Entry(frm, width=6, textvariable=self.var_kerf).grid(row=0, column=9, padx=4, pady=4)

        ttk.Checkbutton(frm, text="Allow rotate 90°", variable=self.var_rotate).grid(row=0, column=10, padx=8, pady=4)

        ttk.Label(frm, text="Algorithm").grid(row=0, column=11, padx=4, pady=4, sticky="e")
        ttk.Combobox(frm, textvariable=self.var_algo,
                     values=["maxrects-baf","maxrects-bssf","bottom-left","skyline-bl"],
                     width=14, state="readonly").grid(row=0, column=12, padx=4, pady=4)

        ttk.Label(frm, text="Max bins (0=∞)").grid(row=0, column=13, padx=4, pady=4, sticky="e")
        ttk.Entry(frm, width=6, textvariable=self.var_maxbins).grid(row=0, column=14, padx=4, pady=4)

        ttk.Checkbutton(frm, text="Top-left origin", variable=self.var_top_left, command=lambda: self.redraw()).grid(row=0, column=15, padx=8, pady=4)

        # Rect list
        left = ttk.LabelFrame(self, text="Rectangles (w × h)")
        left.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=6)
        cols = ("rid","w","h")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=22)
        for c,w in zip(cols,(60,80,80)):
            self.tree.heading(c,text=c.upper()); self.tree.column(c,width=w,anchor="center")
        self.tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=4, pady=4)

        addfrm = ttk.Frame(left); addfrm.pack(side=tk.TOP, fill=tk.X, padx=4, pady=4)
        self.var_rw = tk.StringVar(value="60"); self.var_rh = tk.StringVar(value="40")
        ttk.Label(addfrm, text="w").grid(row=0, column=0, padx=2, pady=2)
        ttk.Entry(addfrm, width=6, textvariable=self.var_rw).grid(row=0, column=1, padx=2, pady=2)
        ttk.Label(addfrm, text="h").grid(row=0, column=2, padx=2, pady=2)
        ttk.Entry(addfrm, width=6, textvariable=self.var_rh).grid(row=0, column=3, padx=2, pady=2)
        ttk.Button(addfrm, text="Add", command=self.add_rect).grid(row=0, column=4, padx=4, pady=2)
        ttk.Button(addfrm, text="Remove selected", command=self.remove_selected).grid(row=0, column=5, padx=4, pady=2)
        ttk.Button(addfrm, text="Clear", command=self.clear_rects).grid(row=0, column=6, padx=4, pady=2)

        ctrl = ttk.Frame(self); ctrl.pack(side=tk.TOP, fill=tk.X, padx=8, pady=6)
        ttk.Button(ctrl, text="Run (single bin)", command=self.run_single_bin).pack(side=tk.LEFT, padx=4)
        ttk.Button(ctrl, text="Pack ALL (multi-bin)", command=self.run_multi_bin).pack(side=tk.LEFT, padx=8)
        ttk.Button(ctrl, text="Export JSON", command=self.export_json).pack(side=tk.LEFT, padx=8)
        ttk.Button(ctrl, text="Import CSV", command=self.import_csv).pack(side=tk.LEFT, padx=8)

        # Canvas + bin selector
        right = ttk.LabelFrame(self, text="Preview"); right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=8, pady=6)
        topbar = ttk.Frame(right); topbar.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(topbar, text="Bin to view:").pack(side=tk.LEFT, padx=4)
        self.bin_selector = ttk.Combobox(topbar, state="readonly", width=20, values=["bin #1"])
        self.bin_selector.current(0)
        self.bin_selector.bind("<<ComboboxSelected>>", lambda e: self.redraw())
        self.bin_selector.pack(side=tk.LEFT, padx=4)

        self.fig = Figure(figsize=(7.0,4.8), dpi=100); self.ax = self.fig.add_subplot(111); self.ax.set_aspect('equal')
        self.canvas = FigureCanvasTkAgg(self.fig, master=right); self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # State
        self.next_id = 1
        self.bins: List[Dict[str, Any]] = [{"placed": [], "fill": 0.0}]
        self.remaining: List[Rect] = []

        self.redraw()

    # ---------- rect ops ----------
    def add_rect(self):
        try:
            w = float(self.var_rw.get()); h = float(self.var_rh.get())
            if w <= 0 or h <= 0: raise ValueError()
        except Exception:
            messagebox.showerror("Error","Invalid w/h."); return
        rid = self.next_id; self.next_id += 1
        self.tree.insert("", tk.END, values=(rid, w, h))

    def remove_selected(self):
        for it in self.tree.selection(): self.tree.delete(it)

    def clear_rects(self):
        for it in self.tree.get_children(): self.tree.delete(it)
        self.next_id = 1

    def get_rects(self) -> List[Rect]:
        rects: List[Rect] = []
        for it in self.tree.get_children():
            rid, w, h = self.tree.item(it, "values")
            rects.append(Rect(float(w), float(h), int(rid)))
        return rects

    # ---------- CSV import ----------
    def import_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV","*.csv"),("All","*.*")])
        if not path: return
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                data = f.read()
        except Exception as e:
            messagebox.showerror("Error", f"Read failed: {e}"); return
        # sniff delimiter
        try:
            dialect = csv.Sniffer().sniff(data.splitlines()[0] if data else "", delimiters=";,")
            delim = dialect.delimiter
        except Exception:
            delim = ','
        rdr = csv.reader(io.StringIO(data), delimiter=delim)
        rows = list(rdr)
        if not rows: return
        # header?
        def is_num(x):
            try: float(x); return True
            except: return False
        header = rows[0]
        has_header = any(not is_num(x) for x in header)
        idx = 1 if has_header else 0
        # map
        mapcol = {}
        if has_header:
            for i,n in enumerate(header):
                n = n.strip().lower()
                if n in ("w","width"): mapcol["w"]=i
                elif n in ("h","height"): mapcol["h"]=i
                elif n in ("qty","quantity","count"): mapcol["qty"]=i
                elif n in ("id","rid"): mapcol["id"]=i
        added = 0
        for r in rows[idx:]:
            try:
                if has_header:
                    w = float(r[mapcol["w"]]); h = float(r[mapcol["h"]])
                    qty = int(r[mapcol["qty"]]) if "qty" in mapcol and mapcol["qty"] < len(r) and r[mapcol["qty"]] != "" else 1
                    rid_given = r[mapcol["id"]].strip() if "id" in mapcol and mapcol["id"] < len(r) and r[mapcol["id"]] != "" else None
                else:
                    if len(r) < 2: continue
                    w = float(r[0]); h = float(r[1])
                    qty = int(r[2]) if len(r) >= 3 and r[2] != "" else 1
                    rid_given = None
                if w <= 0 or h <= 0 or qty <= 0: continue
            except Exception:
                continue
            for _ in range(qty):
                rid = int(rid_given) if (rid_given and rid_given.replace('.','',1).isdigit()) else self.next_id
                self.next_id = max(self.next_id, rid+1) if rid_given else (self.next_id + 1)
                self.tree.insert("", tk.END, values=(rid, w, h)); added += 1
        messagebox.showinfo("CSV", f"Imported {added} item(s).")

    # ---------- packing ----------
    def run_single_bin(self):
        try:
            W = float(self.var_W.get()); H = float(self.var_H.get())
            inner = float(self.var_inner.get() or 0.0)
            edge = float(self.var_edge.get() or 0.0)
            kerf = float(self.var_kerf.get() or 0.0)
            allow_rot = bool(self.var_rotate.get())
            algo = self.var_algo.get()
        except Exception as e:
            messagebox.showerror("Error", f"Invalid parameters: {e}"); return
        rects = self.get_rects()
        if not rects: messagebox.showinfo("Info","Add some rectangles first."); return
        placed, remaining = pack_single_bin_algo(W,H,rects,inner,edge,kerf,algo,allow_rot)
        used_area = sum(p.draw_w*p.draw_h for p in placed); fill = used_area/(W*H)*100 if W*H>0 else 0.0
        self.bins = [{"placed": placed, "fill": fill}]
        self.remaining = remaining
        self.refresh_bin_selector()
        messagebox.showinfo("Result", f"Single bin: placed {len(placed)}, left {len(remaining)}, fill ~ {fill:.2f}%")
        self.redraw()

    def run_multi_bin(self):
        try:
            W = float(self.var_W.get()); H = float(self.var_H.get())
            inner = float(self.var_inner.get() or 0.0)
            edge = float(self.var_edge.get() or 0.0)
            kerf = float(self.var_kerf.get() or 0.0)
            allow_rot = bool(self.var_rotate.get())
            algo = self.var_algo.get()
            maxbins = int(self.var_maxbins.get() or "0")
        except Exception as e:
            messagebox.showerror("Error", f"Invalid parameters: {e}"); return
        rects = self.get_rects()
        if not rects: messagebox.showinfo("Info","Add some rectangles first."); return

        bins, remaining = pack_multiple_bins(W,H,rects,inner,edge,kerf,allow_rot,algo,maxbins)
        self.bins = bins; self.remaining = remaining
        self.refresh_bin_selector()
        total_fill_area = sum(sum(p.draw_w*p.draw_h for p in b["placed"]) for b in bins)
        total_area = len(bins)*W*H if W*H>0 else 0.0
        avg_fill = (total_fill_area/total_area*100) if total_area>0 else 0.0
        messagebox.showinfo("Result", f"Bins used: {len(bins)} | Remaining: {len(remaining)} | Avg fill: {avg_fill:.2f}%")
        self.redraw()

    def refresh_bin_selector(self):
        items = [f"bin #{i+1} (fill {b['fill']:.1f}%)" for i,b in enumerate(self.bins)]
        if not items: items = ["bin #1"]
        self.bin_selector["values"] = items
        self.bin_selector.current(0)

    def redraw(self):
        self.ax.clear()
        try:
            W = float(self.var_W.get()); H = float(self.var_H.get())
        except Exception:
            W,H = 500,300
        self.ax.set_xlim(0, W); self.ax.set_ylim(0, H)
        if self.var_top_left.get(): self.ax.invert_yaxis()
        self.ax.set_xlabel("X"); self.ax.set_ylabel("Y"); self.ax.set_title("Layout preview")
        self.ax.add_patch(MplRect((0,0), W, H, fill=False, linewidth=1.5))

        # get selected bin
        idx = self.bin_selector.current() if self.bin_selector["values"] else 0
        if 0 <= idx < len(self.bins):
            placed = self.bins[idx]["placed"]
        else:
            placed = []

        cmap = cm.get_cmap('tab20')
        for i,p in enumerate(placed):
            color = cmap(i % cmap.N)
            self.ax.add_patch(MplRect((p.draw_x,p.draw_y), p.draw_w, p.draw_h,
                                      fill=True, alpha=0.55, edgecolor='black', facecolor=color, linewidth=1.0))
            label = f"#{p.rid}{'R' if p.rotated else ''}"
            self.ax.text(p.draw_x + p.draw_w/2, p.draw_y + p.draw_h/2, label, ha='center', va='center', fontsize=8)

        self.canvas.draw_idle()

    # ---------- export ----------
    def export_json(self):
        if not self.bins or all(len(b["placed"])==0 for b in self.bins):
            messagebox.showinfo("Info","Nothing to export. Run packing first."); return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json")])
        if not path: return
        data: Dict[str, Any] = {
            "bin": {"W": float(self.var_W.get()), "H": float(self.var_H.get()),
                    "inner_margin": float(self.var_inner.get() or 0.0),
                    "edge_margin": float(self.var_edge.get() or 0.0),
                    "kerf": float(self.var_kerf.get() or 0.0),
                    "top_left_origin": bool(self.var_top_left.get())},
            "algo": self.var_algo.get(),
            "bins": [
                {
                    "fill": b["fill"],
                    "placements": [
                        {"rid": p.rid, "x": p.draw_x, "y": p.draw_y, "w": p.draw_w, "h": p.draw_h, "rotated": p.rotated}
                        for p in b["placed"]
                    ]
                } for b in self.bins
            ],
            "remaining": [{"rid": r.rid, "w": r.w, "h": r.h} for r in self.remaining]
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Saved", f"Exported to {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")


if __name__ == "__main__":
    App().mainloop()
