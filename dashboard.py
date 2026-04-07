import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import openpyxl, csv, os
from db_config import get_connection

BG_DARK   = "#0A0A0A"
BG_PANEL  = "#111111"
BG_CARD   = "#1A1A1A"
TESLA_RED = "#E31937"
TEXT_WHITE= "#FFFFFF"
TEXT_GRAY = "#8E8E93"
SUCCESS   = "#00C896"
DANGER    = "#FF4C4C"
WARNING   = "#FFB84C"


class Dashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Cognitive Load Monitor — Dashboard")
        self.root.geometry("1100x700")
        self.root.configure(bg=BG_DARK)
        self.center(1100, 700)
        self.build_ui()
        self.load_stats()

    def center(self, w, h):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def build_ui(self):
        sidebar = tk.Frame(self.root, bg=BG_PANEL, width=215)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="T",
                 font=("Segoe UI", 28, "bold"),
                 bg=BG_PANEL, fg=TESLA_RED).pack(pady=(25, 4))
        tk.Label(sidebar, text="COGNITIVE MONITOR",
                 font=("Segoe UI", 10, "bold"),
                 bg=BG_PANEL, fg=TEXT_WHITE).pack()
        tk.Label(sidebar, text="Admin Dashboard",
                 font=("Segoe UI", 9),
                 bg=BG_PANEL, fg=TEXT_GRAY).pack(pady=(0, 20))
        tk.Frame(sidebar, bg=TESLA_RED, height=1).pack(fill="x", padx=20)

        self.nav_btns = {}
        for label, key in [
            ("📊  Overview",    "overview"),
            ("🚗  Sessions",    "sessions"),
            ("📋  Readings",    "readings"),
            ("⚠️   Alerts",     "alerts"),
            ("📤  Export",      "export"),
        ]:
            btn = tk.Button(sidebar, text=label,
                            font=("Segoe UI", 10),
                            bg=BG_PANEL, fg=TEXT_GRAY,
                            relief="flat", cursor="hand2",
                            anchor="w", padx=20,
                            activebackground=BG_CARD,
                            activeforeground=TEXT_WHITE,
                            command=lambda k=key: self.show_page(k))
            btn.pack(fill="x", ipady=10, pady=1)
            self.nav_btns[key] = btn

        tk.Frame(sidebar, bg=BG_CARD, height=1).pack(fill="x", padx=20, pady=15)
        tk.Button(sidebar, text="🚗  New Session",
                  font=("Segoe UI", 10, "bold"),
                  bg=TESLA_RED, fg=TEXT_WHITE, relief="flat",
                  cursor="hand2", padx=20,
                  activebackground="#C01530",
                  command=self.new_session).pack(fill="x", ipady=10)
        tk.Button(sidebar, text="🚪  Logout",
                  font=("Segoe UI", 10),
                  bg=BG_PANEL, fg=DANGER, relief="flat",
                  cursor="hand2", padx=20,
                  command=self.logout).pack(fill="x", ipady=8, pady=5)

        self.content = tk.Frame(self.root, bg=BG_DARK)
        self.content.pack(side="left", fill="both", expand=True)

        self.pages = {}
        self.build_overview()
        self.build_sessions()
        self.build_readings()
        self.build_alerts()
        self.build_export()
        self.show_page("overview")

    def show_page(self, key):
        for f in self.pages.values():
            f.pack_forget()
        for k, b in self.nav_btns.items():
            b.config(bg=BG_PANEL, fg=TEXT_GRAY)
        self.pages[key].pack(fill="both", expand=True)
        self.nav_btns[key].config(bg=BG_CARD, fg=TEXT_WHITE)
        refresh = {
            "overview": self.load_stats,
            "sessions": self.load_sessions,
            "readings": self.load_readings,
            "alerts":   self.load_alerts,
        }
        if key in refresh:
            refresh[key]()

    def _make_tree(self, parent, cols, widths, height=10):
        style = ttk.Style()
        style.configure("Tesla.Treeview",
                         background=BG_CARD, foreground=TEXT_WHITE,
                         fieldbackground=BG_CARD, rowheight=30,
                         font=("Segoe UI", 9))
        style.configure("Tesla.Treeview.Heading",
                         background=BG_PANEL, foreground=TESLA_RED,
                         font=("Segoe UI", 9, "bold"))
        style.map("Tesla.Treeview",
                  background=[("selected", TESLA_RED)])

        frame = tk.Frame(parent, bg=BG_DARK)
        frame.pack(fill="both", expand=True, padx=22, pady=(0, 15))

        tree = ttk.Treeview(frame, columns=cols,
                             show="headings",
                             style="Tesla.Treeview", height=height)
        for col, w in zip(cols, widths):
            tree.heading(col, text=col)
            tree.column(col, width=w)

        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return tree

    def _hdr(self, parent, title):
        hdr = tk.Frame(parent, bg=BG_PANEL, height=68)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text=title, font=("Segoe UI", 14, "bold"),
                 bg=BG_PANEL, fg=TEXT_WHITE).pack(side="left", padx=25, pady=20)
        tk.Button(hdr, text="🔄 Refresh",
                  font=("Segoe UI", 9),
                  bg=TESLA_RED, fg=TEXT_WHITE, relief="flat",
                  cursor="hand2",
                  command=lambda: self.show_page(
                      [k for k,v in self.pages.items()
                       if v.winfo_ismapped()][0] if self.pages else "overview"
                  )).pack(side="right", padx=20, pady=18)

    def build_overview(self):
        page = tk.Frame(self.content, bg=BG_DARK)
        self.pages["overview"] = page

        hdr = tk.Frame(page, bg=BG_PANEL, height=68)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📊  System Overview",
                 font=("Segoe UI", 14, "bold"),
                 bg=BG_PANEL, fg=TEXT_WHITE).pack(side="left", padx=25, pady=20)
        tk.Button(hdr, text="🔄 Refresh",
                  font=("Segoe UI", 9),
                  bg=TESLA_RED, fg=TEXT_WHITE, relief="flat",
                  cursor="hand2",
                  command=self.load_stats).pack(side="right", padx=20, pady=18)

        cards = tk.Frame(page, bg=BG_DARK)
        cards.pack(fill="x", padx=22, pady=18)

        self.stat_vars = {}
        for i, (icon, label, key, color) in enumerate([
            ("🚗", "Total Sessions",  "sessions",  TESLA_RED),
            ("⚠️",  "Total Alerts",   "alerts",    WARNING),
            ("😴", "Critical Events", "critical",  DANGER),
            ("📅", "Sessions Today",  "today",     SUCCESS),
        ]):
            card = tk.Frame(cards, bg=BG_CARD, height=110)
            card.grid(row=0, column=i, padx=8, sticky="nsew")
            card.pack_propagate(False)
            cards.columnconfigure(i, weight=1)
            tk.Frame(card, bg=color, width=4).pack(side="left", fill="y")
            inner = tk.Frame(card, bg=BG_CARD)
            inner.pack(side="left", fill="both", expand=True, padx=14, pady=14)
            tk.Label(inner, text=icon, font=("Segoe UI", 22),
                     bg=BG_CARD, fg=color).pack(anchor="w")
            var = tk.StringVar(value="0")
            self.stat_vars[key] = var
            tk.Label(inner, textvariable=var,
                     font=("Segoe UI", 22, "bold"),
                     bg=BG_CARD, fg=TEXT_WHITE).pack(anchor="w")
            tk.Label(inner, text=label, font=("Segoe UI", 8),
                     bg=BG_CARD, fg=TEXT_GRAY).pack(anchor="w")

        tk.Label(page, text="Recent Sessions",
                 font=("Segoe UI", 11, "bold"),
                 bg=BG_DARK, fg=TEXT_WHITE).pack(anchor="w", padx=22, pady=(8,5))

        self.ov_tree = self._make_tree(page,
            ("Driver", "Start", "Duration", "Avg Load", "Max Load", "Alerts"),
            (150, 150, 80, 80, 80, 60))

    def load_stats(self):
        try:
            conn   = get_connection()
            cursor = conn.cursor()
            today  = datetime.now().strftime("%Y-%m-%d")

            cursor.execute("SELECT COUNT(*) FROM DrivingSessions")
            self.stat_vars["sessions"].set(str(cursor.fetchone()[0]))
            cursor.execute("SELECT COUNT(*) FROM AlertLogs")
            self.stat_vars["alerts"].set(str(cursor.fetchone()[0]))
            cursor.execute("SELECT COUNT(*) FROM AlertLogs WHERE LoadLevel='CRITICAL'")
            self.stat_vars["critical"].set(str(cursor.fetchone()[0]))
            cursor.execute("SELECT COUNT(*) FROM DrivingSessions WHERE CAST(StartTime AS DATE)=?", today)
            self.stat_vars["today"].set(str(cursor.fetchone()[0]))

            cursor.execute("""
                SELECT TOP 10 DriverName, StartTime, SessionDuration,
                       AvgCognitiveLoad, MaxCognitiveLoad, AlertsTriggered
                FROM DrivingSessions ORDER BY StartTime DESC
            """)
            for item in self.ov_tree.get_children():
                self.ov_tree.delete(item)
            for row in cursor.fetchall():
                vals    = list(row)
                vals[3] = f"{vals[3]:.2f}" if vals[3] else "—"
                vals[4] = f"{vals[4]:.2f}" if vals[4] else "—"
                vals[2] = f"{vals[2]}s"    if vals[2] else "—"
                self.ov_tree.insert("", "end", values=vals)
            conn.close()
        except Exception as e:
            print(f"Stats error: {e}")

    def build_sessions(self):
        page = tk.Frame(self.content, bg=BG_DARK)
        self.pages["sessions"] = page
        self._hdr(page, "🚗  Driving Sessions")
        self.sess_tree = self._make_tree(page,
            ("ID","Driver","Start","End","Duration","Avg Load","Max Load","Alerts"),
            (40,140,150,150,70,80,80,60))

    def load_sessions(self):
        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT TOP 200 SessionID, DriverName, StartTime, EndTime,
                       SessionDuration, AvgCognitiveLoad,
                       MaxCognitiveLoad, AlertsTriggered
                FROM DrivingSessions ORDER BY StartTime DESC
            """)
            for item in self.sess_tree.get_children():
                self.sess_tree.delete(item)
            for row in cursor.fetchall():
                vals    = list(row)
                vals[5] = f"{vals[5]:.2f}" if vals[5] else "—"
                vals[6] = f"{vals[6]:.2f}" if vals[6] else "—"
                self.sess_tree.insert("", "end", values=vals)
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def build_readings(self):
        page = tk.Frame(self.content, bg=BG_DARK)
        self.pages["readings"] = page
        self._hdr(page, "📋  Cognitive Readings")
        self.read_tree = self._make_tree(page,
            ("ID","Session","Load","Level","Blink","Fatigue","Steer Var","Autopilot","Time"),
            (40,60,70,80,60,70,80,80,140))

    def load_readings(self):
        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT TOP 300 ReadingID, SessionID, CognitiveLoad, LoadLevel,
                       BlinkRate, FatigueScore, SteeringVariance,
                       AutopilotLevel, Timestamp
                FROM CognitiveReadings ORDER BY Timestamp DESC
            """)
            for item in self.read_tree.get_children():
                self.read_tree.delete(item)
            for row in cursor.fetchall():
                vals    = list(row)
                vals[2] = f"{vals[2]:.3f}" if vals[2] else "—"
                vals[4] = f"{vals[4]:.1f}" if vals[4] else "—"
                vals[5] = f"{vals[5]:.2f}" if vals[5] else "—"
                tag = "critical" if row[3] in ("HIGH","CRITICAL") else "normal"
                self.read_tree.insert("", "end", values=vals, tags=(tag,))
            self.read_tree.tag_configure("critical", foreground=DANGER)
            self.read_tree.tag_configure("normal",   foreground=TEXT_WHITE)
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def build_alerts(self):
        page = tk.Frame(self.content, bg=BG_DARK)
        self.pages["alerts"] = page
        self._hdr(page, "⚠️  Alert Logs")
        self.alert_tree = self._make_tree(page,
            ("ID","Session","Alert Type","Load","Level","Action","Time"),
            (40,60,160,70,80,200,140))

    def load_alerts(self):
        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT TOP 300 AlertID, SessionID, AlertType,
                       CognitiveLoad, LoadLevel, AutopilotAction, AlertTime
                FROM AlertLogs ORDER BY AlertTime DESC
            """)
            for item in self.alert_tree.get_children():
                self.alert_tree.delete(item)
            for row in cursor.fetchall():
                vals    = list(row)
                vals[3] = f"{vals[3]:.3f}" if vals[3] else "—"
                tag = "critical" if row[4] == "CRITICAL" else "high" \
                      if row[4] == "HIGH" else "normal"
                self.alert_tree.insert("", "end", values=vals, tags=(tag,))
            self.alert_tree.tag_configure("critical", foreground=DANGER)
            self.alert_tree.tag_configure("high",     foreground=WARNING)
            self.alert_tree.tag_configure("normal",   foreground=TEXT_WHITE)
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def build_export(self):
        page = tk.Frame(self.content, bg=BG_DARK)
        self.pages["export"] = page

        hdr = tk.Frame(page, bg=BG_PANEL, height=68)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📤  Export Reports",
                 font=("Segoe UI", 14, "bold"),
                 bg=BG_PANEL, fg=TEXT_WHITE).pack(side="left", padx=25, pady=20)

        cards = tk.Frame(page, bg=BG_DARK)
        cards.pack(fill="both", expand=True, padx=40, pady=35)

        for i, (icon, title, cmd) in enumerate([
            ("🚗", "All Sessions",      self.exp_sessions),
            ("📋", "All Readings",      self.exp_readings),
            ("⚠️",  "All Alerts",       self.exp_alerts),
            ("📅", "Today's Report",    self.exp_today),
        ]):
            card = tk.Frame(cards, bg=BG_CARD, height=165)
            card.grid(row=i//2, column=i%2, padx=14, pady=14, sticky="nsew")
            card.pack_propagate(False)
            cards.columnconfigure(i%2, weight=1)
            tk.Label(card, text=icon, font=("Segoe UI", 34),
                     bg=BG_CARD, fg=TESLA_RED).pack(pady=(18, 4))
            tk.Label(card, text=title,
                     font=("Segoe UI", 11, "bold"),
                     bg=BG_CARD, fg=TEXT_WHITE).pack()
            br = tk.Frame(card, bg=BG_CARD)
            br.pack(pady=10)
            tk.Button(br, text="Excel", font=("Segoe UI", 9),
                      bg=SUCCESS, fg=BG_DARK, relief="flat",
                      cursor="hand2", padx=10,
                      command=lambda c=cmd: c("xlsx")).pack(side="left", padx=3)
            tk.Button(br, text="CSV", font=("Segoe UI", 9),
                      bg=TESLA_RED, fg=TEXT_WHITE, relief="flat",
                      cursor="hand2", padx=10,
                      command=lambda c=cmd: c("csv")).pack(side="left", padx=3)

    def _save(self, fmt, name):
        ext = ".xlsx" if fmt == "xlsx" else ".csv"
        return filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[("Excel","*.xlsx"),("CSV","*.csv")],
            initialfile=name)

    def _write(self, path, headers, rows, fmt):
        if not path: return
        if fmt == "xlsx":
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.append(headers)
            for r in rows: ws.append(list(r))
            wb.save(path)
        else:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(headers)
                w.writerows(rows)
        messagebox.showinfo("Exported", f"Saved:\n{path}")
        os.startfile(path)

    def _fetch(self, table, where=""):
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table} {where} ORDER BY 1 DESC")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def exp_sessions(self, fmt):
        path = self._save(fmt, "DrivingSessions")
        self._write(path,
            ["ID","Driver","Start","End","Avg Load","Max Load",
             "Alerts","Autopilot","Duration"],
            self._fetch("DrivingSessions"), fmt)

    def exp_readings(self, fmt):
        path = self._save(fmt, "CognitiveReadings")
        self._write(path,
            ["ID","Session","Load","Level","Blink","Eye Open",
             "Pitch","Yaw","Roll","Fatigue","Steer Var","Brake Freq",
             "Autopilot","Time"],
            self._fetch("CognitiveReadings"), fmt)

    def exp_alerts(self, fmt):
        path = self._save(fmt, "AlertLogs")
        self._write(path,
            ["ID","Session","Type","Load","Level","Action","Time"],
            self._fetch("AlertLogs"), fmt)

    def exp_today(self, fmt):
        today = datetime.now().strftime("%Y-%m-%d")
        path  = self._save(fmt, f"TodayReport_{today}")
        self._write(path,
            ["ID","Session","Load","Level","Time"],
            self._fetch("CognitiveReadings",
                         f"WHERE CAST(Timestamp AS DATE)='{today}'"), fmt)

    def new_session(self):
        self.root.destroy()
        import main_app
        main_app.launch()

    def logout(self):
        if messagebox.askyesno("Logout", "Return to login?"):
            self.root.destroy()
            import main_app
            main_app.launch()


def launch():
    root = tk.Tk()
    Dashboard(root)
    root.mainloop()

if __name__ == "__main__":
    launch()