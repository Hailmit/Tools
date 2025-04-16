import tkinter as tk
from tkinter import messagebox
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ==== LANGUAGE PACK ====
LANGUAGES = {
    'vi': {
        'title': " CÔNG CỤ SẮP XẾP VẬT THỂ",
        'frame_input': "Thông số",
        'btn_calc': "Tính & Vẽ sơ đồ",
        'plane_length': "Chiều dài mặt phẳng (mm):",
        'plane_width': "Chiều rộng mặt phẳng (mm):",
        'obj_length': "Chiều dài vật thể (mm):",
        'obj_width': "Chiều rộng vật thể (mm):",
        'spacing': "Khoảng cách giữa vật thể (mm):",
        'frame_canvas': "Sơ đồ minh họa",
        'result': lambda mode, count, percent, rows, cols, extra: (
            f" Chế độ: {mode.upper()} \n"
            f" Số lượng tối đa: {count}\n"
            f" Diện tích phủ: {percent:.2f}%\n"
            f" Số hàng: {rows}  |  Số cột: {cols}" +
            (f"\n Thêm hàng xoay: {extra[0]} x {extra[1]}" if extra else "")
        ),
        'btn_lang': "🌐 English",
    },
    'en': {
        'title': " OBJECT LAYOUT TOOL",
        'frame_input': "Input Parameters",
        'btn_calc': "Calculate & Draw",
        'plane_length': "Plane length (mm):",
        'plane_width': "Plane width (mm):",
        'obj_length': "Object length (mm):",
        'obj_width': "Object width (mm):",
        'spacing': "Spacing between objects (mm):",
        'frame_canvas': "Illustration",
        'result': lambda mode, count, percent, rows, cols, extra: (
            f" Mode: {mode.upper()} \n"
            f" Max count: {count}\n"
            f" Coverage: {percent:.2f}%\n"
            f" Rows: {rows}  |  Columns: {cols}" +
            (f"\n Extra rotated rows: {extra[0]} x {extra[1]}" if extra else "")
        ),
        'btn_lang': "🌐 Tiếng Việt",
    }
}

current_lang = 'vi'

# ==== CORE LOGIC ====
def count_fit(pw, pl, ow, ol, spacing):
    cols = int((pw + spacing) // (ow + spacing))
    rows = int((pl + spacing) // (ol + spacing))
    count = cols * rows
    return cols, rows, count

def calculate_best_layout(pw, pl, ow, ol, spacing):
    cols_v, rows_v, count_v = count_fit(pw, pl, ow, ol, spacing)
    cols_h, rows_h, count_h = count_fit(pw, pl, ol, ow, spacing)

    main_rows = int((pl + spacing) // (ol + spacing))
    remaining_len = pl - main_rows * (ol + spacing)
    extra_rows = int((remaining_len + spacing) // (ow + spacing))
    extra_cols = int((pw + spacing) // (ol + spacing))
    count_c = (cols_v * main_rows) + (extra_rows * extra_cols)

    if count_v >= count_h and count_v >= count_c:
        return 'vertical', cols_v, rows_v, ow, ol, count_v
    elif count_h >= count_c:
        return 'horizontal', cols_h, rows_h, ol, ow, count_h
    else:
        return 'combined', cols_v, main_rows, ow, ol, count_c, extra_rows, extra_cols

# ==== DRAW FUNCTION ====
def draw_objects(ax, cols, rows, ow, ol, start_y, spacing, color):
    for i in range(cols):
        for j in range(rows):
            x = i * (ow + spacing)
            y = start_y - (j + 1) * (ol + spacing) + spacing
            rect = patches.Rectangle((x, y), ow, ol, edgecolor='black', facecolor=color)
            ax.add_patch(rect)

def draw_layout(mode, pw, pl, spacing, cols, rows, ow, ol, extra_rows=0, extra_cols=0):
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.set_facecolor('#2E2E2E')
    ax.set_xlim(0, pw)
    ax.set_ylim(0, pl)
    ax.set_aspect('equal')
    ax.axis('off')

    color_v = '#6EC1E4'
    color_h = '#9EE09E'

    if mode == "vertical":
        draw_objects(ax, cols, rows, ow, ol, pl, spacing, color_v)
    elif mode == "horizontal":
        draw_objects(ax, cols, rows, ow, ol, pl, spacing, color_h)
    elif mode == "combined":
        draw_objects(ax, cols, rows, ow, ol, pl, spacing, color_v)
        draw_objects(ax, extra_cols, extra_rows, ol, ow,
                     pl - (rows * (ol + spacing)) - spacing, spacing, color_h)

    border = patches.Rectangle((0, 0), pw, pl, edgecolor='red', facecolor='none', linewidth=2)
    ax.add_patch(border)
    return fig

# ==== LANGUAGE SWITCH ====
def update_language():
    lang = LANGUAGES[current_lang]
    lbl_title.config(text=lang['title'])
    frame_input.config(text=lang['frame_input'])
    btn_calc.config(text=lang['btn_calc'])
    frame_canvas.config(text=lang['frame_canvas'])
    lang_btn.config(text=lang['btn_lang'])

    lbls[0].config(text=lang['plane_length'])
    lbls[1].config(text=lang['plane_width'])
    lbls[2].config(text=lang['obj_length'])
    lbls[3].config(text=lang['obj_width'])
    lbls[4].config(text=lang['spacing'])

def toggle_language():
    global current_lang
    current_lang = 'en' if current_lang == 'vi' else 'vi'
    update_language()

# ==== GUI SETUP ====
root = tk.Tk()
root.title(" Object Layout Tool")
root.geometry("640x800")
root.configure(bg="#2E2E2E")

bg_dark = '#2E2E2E'
fg_light = '#FFFFFF'
label_fg = '#D3D3D3'
entry_bg = '#3C3C3C'
entry_fg = '#FFFFFF'

lbl_title = tk.Label(root, font=("Segoe UI", 18, "bold"), bg=bg_dark, fg="#00D6D6")
lbl_title.pack(pady=12)

frame_input = tk.LabelFrame(root, padx=15, pady=10, bg=bg_dark, fg=label_fg, bd=2, relief="groove")
frame_input.pack(padx=12, pady=8, fill="x")

lbls = []
def create_input_row(label_key, var, row):
    lbl = tk.Label(frame_input, anchor="w", bg=bg_dark, fg=label_fg, font=("Segoe UI", 10))
    lbl.grid(row=row, column=0, sticky="w", padx=5, pady=6)
    lbls.append(lbl)
    entry = tk.Entry(frame_input, textvariable=var, width=12, font=("Segoe UI", 10),
                     bg=entry_bg, fg=entry_fg, insertbackground=entry_fg, relief="flat")
    entry.grid(row=row, column=1, sticky="w", padx=5)
    return entry

var_plane_length = tk.DoubleVar(value=180)
var_plane_width = tk.DoubleVar(value=180)
var_obj_length = tk.DoubleVar(value=102)
var_obj_width = tk.DoubleVar(value=54.5)
var_spacing = tk.DoubleVar(value=3)

entry_plane_length = create_input_row("plane_length", var_plane_length, 0)
entry_plane_width = create_input_row("plane_width", var_plane_width, 1)
entry_obj_length = create_input_row("obj_length", var_obj_length, 2)
entry_obj_width = create_input_row("obj_width", var_obj_width, 3)
entry_spacing = create_input_row("spacing", var_spacing, 4)

frame_btn = tk.Frame(root, bg=bg_dark)
frame_btn.pack(pady=10)

btn_calc = tk.Button(frame_btn, command=lambda: calculate_and_draw(), text="",
                     bg="#00BFA5", fg="white", font=("Segoe UI", 10, "bold"),
                     padx=12, pady=6, relief="flat", cursor="hand2", activebackground="#00A890")
btn_calc.grid(row=0, column=0, padx=8)

lang_btn = tk.Button(frame_btn, command=toggle_language, text="",
                     bg="#555", fg=fg_light, font=("Segoe UI", 10),
                     padx=12, pady=6, relief="flat", cursor="hand2", activebackground="#777")
lang_btn.grid(row=0, column=1)

result_label = tk.Label(root, text="", font=("Segoe UI", 11), bg=bg_dark, fg="#E0E0E0", justify="left")
result_label.pack(pady=6)

frame_canvas = tk.LabelFrame(root, padx=10, pady=10, bg=bg_dark, fg=label_fg,
                             text="", font=("Segoe UI", 10, "bold"), bd=2, relief="groove")
frame_canvas.pack(padx=10, pady=10, fill="both", expand=True)

# ==== CALCULATE HANDLER ====
def calculate_and_draw():
    try:
        pw = float(entry_plane_width.get())
        pl = float(entry_plane_length.get())
        ol = float(entry_obj_length.get())
        ow = float(entry_obj_width.get())
        spacing = float(entry_spacing.get())
    except ValueError:
        messagebox.showerror("Lỗi", "Vui lòng nhập số hợp lệ")
        return

    result = calculate_best_layout(pw, pl, ow, ol, spacing)

    if result[0] == "combined":
        mode, cols, rows, ow, ol, count, extra_rows, extra_cols = result
    else:
        mode, cols, rows, ow, ol, count = result
        extra_rows = extra_cols = 0

    best_area = count * ow * ol
    plane_area = pw * pl
    coverage_percent = (best_area / plane_area) * 100

    fig = draw_layout(mode, pw, pl, spacing, cols, rows, ow, ol, extra_rows, extra_cols)

    for widget in frame_canvas.winfo_children():
        widget.destroy()

    canvas = FigureCanvasTkAgg(fig, master=frame_canvas)
    canvas.draw()
    canvas.get_tk_widget().pack()

    lang = LANGUAGES[current_lang]
    extra = (extra_rows, extra_cols) if mode == "combined" else None
    result_label.config(text=lang['result'](mode, count, coverage_percent, rows, cols, extra))

# Load ngôn ngữ ban đầu
update_language()
root.mainloop()
