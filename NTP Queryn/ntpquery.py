import socket
import struct
import time
import threading
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, messagebox

# --- Màu sắc và giao diện cơ bản ---
BG = "#EEF1F5"        # nền app
CARD_BG = "#FFFFFF"   # nền thẻ kết quả
TEXT_FG = "#222222"   # màu chữ
ACCENT = "#0078D7"    # màu xanh Microsoft
ACCENT_HOVER = "#005A9E"

# --- Hàm truy vấn NTP ---
def ntp_query(host="pool.ntp.org"):
    """Truy vấn thời gian từ máy chủ NTP."""
    NTP_TIMESTAMP_DELTA = 2208988800
    packet = b'\x1b' + 47 * b'\0'
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(3)  # timeout nhanh hơn 3s
        s.sendto(packet, (host, 123))
        data, _ = s.recvfrom(1024)
    unpacked = struct.unpack('!12I', data[0:48])
    transmit_timestamp = unpacked[10] + float(unpacked[11]) / 2**32
    unix_time = transmit_timestamp - NTP_TIMESTAMP_DELTA
    utc_time = datetime.fromtimestamp(unix_time, tz=timezone.utc)
    local_time = utc_time.astimezone()
    return unix_time, utc_time, local_time


# --- Giao diện chính ---
def query_time():
    """Hàm xử lý khi bấm Query."""
    host = entry_server.get().strip() or "pool.ntp.org"

    result_label.config(
        text=f"🔄 Đang truy vấn máy chủ NTP ({host})...",
        fg="#555"
    )
    disable_button(True)

    def worker():
        try:
            ntp_unix, utc_time, local_time = ntp_query(host)
            system_time = time.time()
            diff = system_time - ntp_unix

            # xử lý sai lệch rõ ràng hơn
            if abs(diff) < 0.000001:
                status = "- Hệ thống trùng khớp hoàn toàn."
            elif diff > 0:
                status = "- Hệ thống CHẠY NHANH hơn."
            else:
                status = "- Hệ thống CHẠY CHẬM hơn."

            lines = [
                f"- Máy chủ NTP: {host}",
                f"- NTP (UTC):   {utc_time.strftime('%Y-%m-%d %H:%M:%S %Z')}",
                f"- NTP (Local): {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')}",
                f"- Hệ thống:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                f"- Sai lệch: {diff:.6f} giây",
                status
            ]

            root.after(0, lambda: result_label.config(
                text="\n".join(lines),
                fg=TEXT_FG
            ))

        except socket.timeout:
            root.after(0, lambda: messagebox.showerror(
                "Lỗi", "Không nhận được phản hồi từ máy chủ NTP (timeout)."))
        except Exception as e:
            root.after(0, lambda: messagebox.showerror("Lỗi khác", str(e)))
        finally:
            root.after(0, lambda: disable_button(False))

    threading.Thread(target=worker, daemon=True).start()


def disable_button(state=True):
    """Khóa / mở nút Query."""
    btn_query.config(state=tk.DISABLED if state else tk.NORMAL)


# === TẠO CỬA SỔ CHÍNH ===
root = tk.Tk()
root.title("🕒 NTP Time Query Tool")
root.geometry("580x380")
root.resizable(False, False)
root.configure(bg=BG)

# --- Style ttk ---
style = ttk.Style()
style.theme_use("clam")
style.configure("TFrame", background=BG)
style.configure("TLabel", background=BG, foreground=TEXT_FG, font=("Segoe UI", 11))
style.configure("Accent.TButton",
                background=ACCENT,
                foreground="white",
                font=("Segoe UI", 10, "bold"),
                padding=6,
                borderwidth=0)
style.map("Accent.TButton",
          background=[("active", ACCENT_HOVER), ("pressed", "#003E73")])

# --- Tiêu đề ---
ttk.Label(root, text="Query time from NTP server",
          font=("Segoe UI", 14, "bold")).pack(pady=(16, 10))

# --- Ô nhập ---
row = ttk.Frame(root)
row.pack(pady=4)
ttk.Label(row, text="NTP Server:").pack(side="left", padx=(0, 6))
entry_server = ttk.Entry(row, width=32, font=("Segoe UI", 10))
entry_server.pack(side="left")
entry_server.insert(0, "pool.ntp.org")

# --- Nút Query ---
btn_query = ttk.Button(root, text="Query", command=query_time, style="Accent.TButton")
btn_query.pack(pady=12)

# --- Thẻ hiển thị kết quả ---
outer = tk.Frame(root, bg=BG)
outer.pack(fill="both", expand=False, padx=16, pady=(6, 12))
result_card = tk.Frame(outer, bg=CARD_BG, bd=2, relief="ridge", width=520, height=180)
result_card.pack(anchor="center")
result_card.pack_propagate(False)

inner = tk.Frame(result_card, bg=CARD_BG)
inner.pack(padx=12, pady=10, fill="both", expand=True)

result_label = tk.Label(inner,
                        text="(Results will be displayed here)",
                        justify="left",
                        anchor="nw",
                        bg=CARD_BG,
                        fg="#555",
                        font=("Consolas", 10))
result_label.pack(anchor="nw", fill="both")

# --- Footer ---
ttk.Label(root, text="Made with ❤  |  Haizitne",
          font=("Segoe UI", 8)).pack(side="bottom", pady=6)

root.mainloop()
