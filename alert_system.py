import threading
import winsound
import tkinter as tk
from datetime import datetime

ALERT_SOUNDS = {
    "LOW":      None,
    "MEDIUM":   (800,  300),
    "HIGH":     (1000, 500),
    "CRITICAL": (1200, 800),
}


def play_alert(level):
    """Play alert sound based on cognitive load level"""
    def _play():
        params = ALERT_SOUNDS.get(level)
        if params:
            freq, dur = params
            try:
                if level == "CRITICAL":
                    for _ in range(3):
                        winsound.Beep(freq, dur)
                else:
                    winsound.Beep(freq, dur)
            except Exception as snd_err:
                print(f"[SOUND] {snd_err}")
    threading.Thread(target=_play, daemon=True).start()


def show_alert_overlay(root, level, message, color):
    """Flash alert overlay on screen"""
    try:
        overlay = tk.Toplevel(root)
        overlay.overrideredirect(True)
        overlay.attributes("-topmost", True)
        overlay.attributes("-alpha", 0.88)

        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        w, h = 500, 120
        overlay.geometry(f"{w}x{h}+{(sw-w)//2}+{sh-h-60}")
        overlay.configure(bg=color)

        tk.Label(overlay, text=f"⚠  {level} COGNITIVE LOAD",
                 font=("Segoe UI", 14, "bold"),
                 bg=color, fg="#FFFFFF").pack(pady=(18, 4))
        tk.Label(overlay, text=message,
                 font=("Segoe UI", 10),
                 bg=color, fg="#FFFFFF").pack()

        # Auto-dismiss after 3 seconds
        overlay.after(3000, overlay.destroy)
    except Exception:
        pass