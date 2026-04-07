import tkinter as tk
from tkinter import messagebox
from db_config import get_connection
from datetime import datetime

BG_DARK   = "#0A0A0A"
BG_PANEL  = "#111111"
BG_CARD   = "#1A1A1A"
TESLA_RED = "#E31937"
TEXT_WHITE= "#FFFFFF"
TEXT_GRAY = "#8E8E93"
DANGER    = "#FF4C4C"

ADMIN_PASSWORD = "admin123"


class LoginWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Tesla Cognitive Load Monitor")
        self.root.geometry("500x620")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_DARK)
        self.center(500, 620)
        self.build_ui()

    def center(self, w, h):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def build_ui(self):
        # Header
        hdr = tk.Frame(self.root, bg=BG_PANEL, height=180)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="T",
                 font=("Segoe UI", 55, "bold"),
                 bg=BG_PANEL, fg=TESLA_RED).pack(pady=(20, 0))
        tk.Label(hdr, text="COGNITIVE LOAD MONITOR",
                 font=("Segoe UI", 13, "bold"),
                 bg=BG_PANEL, fg=TEXT_WHITE).pack()
        tk.Label(hdr, text="Real-Time Driver Fatigue Detection System",
                 font=("Segoe UI", 9),
                 bg=BG_PANEL, fg=TEXT_GRAY).pack()

        tk.Frame(self.root, bg=TESLA_RED, height=2).pack(fill="x")

        form = tk.Frame(self.root, bg=BG_DARK, padx=50)
        form.pack(fill="both", expand=True, pady=20)

        # Role selection
        tk.Label(form, text="SELECT MODE",
                 font=("Segoe UI", 9, "bold"),
                 bg=BG_DARK, fg=TEXT_GRAY).pack(anchor="w", pady=(0, 10))

        self.role_var = tk.StringVar(value="driver")
        for role, label, icon in [
            ("driver", "Start Driving Session", "🚗"),
            ("admin",  "Admin Dashboard",        "⚙️"),
        ]:
            rf = tk.Frame(form, bg=BG_CARD, cursor="hand2")
            rf.pack(fill="x", pady=4, ipady=10)
            tk.Label(rf, text=icon, font=("Segoe UI", 18),
                     bg=BG_CARD, fg=TESLA_RED).pack(side="left", padx=(15, 10))
            tk.Label(rf, text=label, font=("Segoe UI", 10, "bold"),
                     bg=BG_CARD, fg=TEXT_WHITE).pack(side="left")
            tk.Radiobutton(rf, variable=self.role_var, value=role,
                           bg=BG_CARD, fg=TESLA_RED,
                           selectcolor=BG_DARK,
                           activebackground=BG_CARD,
                           cursor="hand2").pack(side="right", padx=15)

        # Driver name
        tk.Label(form, text="DRIVER NAME",
                 font=("Segoe UI", 9, "bold"),
                 bg=BG_DARK, fg=TEXT_GRAY).pack(anchor="w", pady=(15, 5))

        name_frame = tk.Frame(form, bg=BG_CARD)
        name_frame.pack(fill="x")
        tk.Label(name_frame, text="👤", bg=BG_CARD, fg=TEXT_GRAY,
                 font=("Segoe UI", 12)).pack(side="left", padx=10)
        self.name_entry = tk.Entry(name_frame, bg=BG_CARD,
                                    fg=TEXT_WHITE,
                                    insertbackground=TEXT_WHITE,
                                    relief="flat",
                                    font=("Segoe UI", 12), bd=0)
        self.name_entry.pack(side="left", fill="x",
                              expand=True, ipady=10)
        self.name_entry.insert(0, "e.g. John Silva")
        self.name_entry.bind("<FocusIn>",
                              lambda ev: self.name_entry.delete(0, "end")
                              if self.name_entry.get() == "e.g. John Silva"
                              else None)

        # Password
        tk.Label(form, text="PASSWORD",
                 font=("Segoe UI", 9, "bold"),
                 bg=BG_DARK, fg=TEXT_GRAY).pack(anchor="w", pady=(12, 5))

        pw_frame = tk.Frame(form, bg=BG_CARD)
        pw_frame.pack(fill="x")
        tk.Label(pw_frame, text="🔒", bg=BG_CARD, fg=TEXT_GRAY,
                 font=("Segoe UI", 12)).pack(side="left", padx=10)
        self.pw = tk.Entry(pw_frame, show="●", bg=BG_CARD,
                            fg=TEXT_WHITE,
                            insertbackground=TEXT_WHITE,
                            relief="flat",
                            font=("Segoe UI", 12), bd=0)
        self.pw.pack(side="left", fill="x", expand=True, ipady=10)
        self.pw.bind("<Return>", lambda ev: self.login())

        tk.Button(form, text="START",
                  font=("Segoe UI", 12, "bold"),
                  bg=TESLA_RED, fg=TEXT_WHITE, relief="flat",
                  cursor="hand2", activebackground="#C01530",
                  command=self.login).pack(fill="x",
                  pady=(18, 0), ipady=13)

        self.status = tk.Label(form, text="",
                                font=("Segoe UI", 9),
                                bg=BG_DARK, fg=DANGER)
        self.status.pack(pady=5)

        tk.Label(self.root,
                 text="© 2025 Cognitive Load Monitor  |  Research Use Only",
                 font=("Segoe UI", 7),
                 bg=BG_DARK, fg=TEXT_GRAY).pack(pady=8)

    def login(self):
        pw   = self.pw.get()
        name = self.name_entry.get().strip()
        role = self.role_var.get()

        if pw != ADMIN_PASSWORD:
            self.status.config(text="❌ Incorrect password.")
            return

        if role == "driver":
            if name in ["", "e.g. John Silva"]:
                self.status.config(text="❌ Please enter driver name.")
                return
            session_id = self._create_session(name)
            self.root.destroy()
            import driver_monitor
            driver_monitor.launch(name, session_id)
        else:
            self.root.destroy()
            import dashboard
            dashboard.launch()

    def _create_session(self, name):
        """Create new driving session in DB"""
        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO DrivingSessions (DriverName)
                OUTPUT INSERTED.SessionID
                VALUES (?)
            """, name)
            session_id = cursor.fetchone()[0]
            conn.commit()
            conn.close()
            return session_id
        except Exception as db_err:
            print(f"[ERROR] Create session: {db_err}")
            return 1


def launch():
    root = tk.Tk()
    LoginWindow(root)
    root.mainloop()

if __name__ == "__main__":
    launch()