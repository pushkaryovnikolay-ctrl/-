import os
import string
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from queue import Queue, Empty

APP = "SharpGrief Checker"
BG, PANEL, PANEL2 = "#10141d", "#191f2b", "#222d3d"
ACCENT, TEXT, MUTED, WARN = "#63e6be", "#edf2f7", "#9aa8b8", "#f6c177"

CATEGORIES = {
    "ExLoader": ["exloader"],
    "Чит-клиенты Minecraft": [
        "vape", "raven", "liquidbounce", "meteor", "wurst", "aristois",
        "impact", "bleachhack", "thunderhack", "future", "rusherhack",
        "rise", "augustus", "fdp", "sigma", "tenacity", "horion",
        "astolfo", "moon", "dortware", "exhibition"
    ],
    "Загрузчики и инжекторы": ["injector", "client loader", "cheat loader"],
}
SKIP_DIRS = {
    "$recycle.bin", "system volume information", "windows",
    "program files", "program files (x86)", "programdata",
    "recovery", "perflogs", "winsxs", "windowsapps",
    "node_modules", ".git"
}
# Search likely user-data roots on each drive; do not enter OS/program installation trees.
SCAN_ROOTS = ["Users", "Documents", "Downloads", "Desktop", "Games", "Minecraft",
              "PrismLauncher", "MultiMC", "PCL", "HMCL", "TLauncher"]

class App:
    def __init__(self, root):
        self.root = root
        root.title(APP)
        root.geometry("1060x720")
        root.minsize(900, 620)
        root.configure(bg=BG)
        self.q = Queue()
        self.results = []
        self.scanning = False
        self.stop_flag = threading.Event()
        self.current_section = "Обзор"

        st = ttk.Style()
        st.theme_use("clam")
        st.configure(".", font=("Segoe UI", 10))
        st.configure("TFrame", background=BG)
        st.configure("TLabel", background=BG, foreground=TEXT)
        st.configure("Treeview", background=PANEL, fieldbackground=PANEL,
                     foreground=TEXT, rowheight=26)
        st.configure("Treeview.Heading", background=PANEL2, foreground=TEXT)
        st.configure("TButton", background=PANEL2, foreground=TEXT, padding=9)
        st.map("TButton", background=[("active", "#34465a")])
        st.configure("Accent.TButton", background=ACCENT, foreground="#08140f",
                     font=("Segoe UI", 10, "bold"), padding=10)
        st.map("Accent.TButton", background=[("active", "#8af0d2")])

        head = tk.Frame(root, bg=BG)
        head.pack(fill="x", padx=24, pady=(18, 12))
        tk.Label(head, text="SHARPGRIEF", bg=BG, fg=ACCENT,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(head, text="Checker", bg=BG, fg=TEXT,
                 font=("Segoe UI", 25, "bold")).pack(anchor="w")
        tk.Label(head, text="Локальная диагностика Windows и Minecraft",
                 bg=BG, fg=MUTED).pack(anchor="w")

        shell = tk.Frame(root, bg=BG)
        shell.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        self.nav = tk.Frame(shell, bg=PANEL, width=205)
        self.nav.pack(side="left", fill="y")
        self.nav.pack_propagate(False)
        tk.Label(self.nav, text="РАЗДЕЛЫ", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=15, pady=(18, 10))
        self.main = tk.Frame(shell, bg=BG)
        self.main.pack(side="left", fill="both", expand=True, padx=(18, 0))
        for name in ["Обзор", "Полная проверка", "ExLoader", "Чит-клиенты",
                     "Процессы", "Установленные программы", "Отчёт"]:
            tk.Button(self.nav, text=name, anchor="w", relief="flat",
                      bg=PANEL, fg=TEXT, activebackground=PANEL2, activeforeground=TEXT,
                      padx=15, pady=11, command=lambda n=name: self.show(n)).pack(fill="x", padx=7, pady=2)

        self.show("Обзор")
        self.root.after(150, self.poll_queue)

    def clear(self):
        for w in self.main.winfo_children():
            w.destroy()

    def card(self, title, desc, button, command):
        box = tk.Frame(self.main, bg=PANEL, padx=17, pady=14)
        box.pack(fill="x", pady=6)
        tk.Label(box, text=title, bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(box, text=desc, bg=PANEL, fg=MUTED, justify="left",
                 wraplength=700).pack(anchor="w", pady=(5, 10))
        ttk.Button(box, text=button, command=command, style="Accent.TButton").pack(anchor="w")

    def show(self, name):
        self.current_section = name
        self.clear()
        tk.Label(self.main, text=name, bg=BG, fg=TEXT,
                 font=("Segoe UI", 21, "bold")).pack(anchor="w", pady=(8, 12))
        if name == "Обзор":
            self.card("Автоматическая полная проверка",
                      "Самостоятельно найдёт доступные диски и проверит пользовательские папки, "
                      "Minecraft, загрузки и папки лаунчеров. Никакого выбора папок.",
                      "Начать полную проверку", self.confirm_scan)
            self.card("Быстрые системные сведения",
                      "Покажет процессы и список установленных программ отдельными разделами.",
                      "Открыть процессы", lambda: self.show("Процессы"))
            tk.Label(self.main,
                     text="Проверяются имена файлов и папок. Содержимое документов не читается, "
                          "данные никуда не отправляются. Системные каталоги Windows и Program Files "
                          "пропускаются. Запускайте только на своём ПК или с разрешения владельца.",
                     bg=BG, fg=WARN, wraplength=720, justify="left").pack(anchor="w", pady=15)
            self.status_panel()
        elif name == "Полная проверка":
            self.card("Полное сканирование",
                      "Обходит доступные пользовательские каталоги на всех найденных дисках. "
                      "Проверка может занять много времени.",
                      "Начать проверку", self.confirm_scan)
            ttk.Button(self.main, text="Остановить проверку", command=self.stop_scan).pack(anchor="w", pady=8)
            self.status_panel()
            self.table()
        elif name in ("ExLoader", "Чит-клиенты"):
            self.card("Сканирование: " + name,
                      "Показывает совпадения по названиям. Наличие файла само по себе не доказывает использование читов.",
                      "Проверить автоматически", lambda: self.start_scan(name))
            self.table()
        elif name == "Процессы":
            ttk.Button(self.main, text="Обновить список процессов",
                       command=self.load_processes, style="Accent.TButton").pack(anchor="w", pady=(0, 10))
            self.proc_text = tk.Text(self.main, bg=PANEL, fg=TEXT, insertbackground=TEXT,
                                     relief="flat", height=22, wrap="none")
            self.proc_text.pack(fill="both", expand=True)
            self.load_processes()
        elif name == "Установленные программы":
            ttk.Button(self.main, text="Открыть список приложений Windows",
                       command=lambda: self.launch(["cmd", "/c", "start", "ms-settings:appsfeatures"]),
                       style="Accent.TButton").pack(anchor="w", pady=(0, 10))
            tk.Label(self.main, text="Для приватности программа не выгружает полный список приложений "
                     "в отчёт. Откроется штатная страница Windows.",
                     bg=BG, fg=MUTED, wraplength=700).pack(anchor="w")
        elif name == "Отчёт":
            ttk.Button(self.main, text="Сохранить отчёт TXT", command=self.save_report,
                       style="Accent.TButton").pack(anchor="w", pady=(0, 12))
            self.table()

    def status_panel(self):
        panel = tk.Frame(self.main, bg=PANEL, padx=15, pady=12)
        panel.pack(fill="x", pady=8)
        self.status = tk.Label(panel, text="Ожидание", bg=PANEL, fg=ACCENT,
                               font=("Segoe UI", 11, "bold"))
        self.status.pack(anchor="w")
        self.progress = ttk.Progressbar(panel, mode="indeterminate")
        self.progress.pack(fill="x", pady=(10, 0))
        self.count = tk.Label(panel, text="Найдено совпадений: 0",
                              bg=PANEL, fg=MUTED)
        self.count.pack(anchor="w", pady=(7, 0))

    def table(self):
        frame = tk.Frame(self.main, bg=BG)
        frame.pack(fill="both", expand=True, pady=(10, 0))
        self.tree = ttk.Treeview(frame, columns=("category", "term", "path"),
                                 show="headings")
        for col, label, width in [("category", "Раздел", 155),
                                  ("term", "Совпадение", 140),
                                  ("path", "Путь", 560)]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.refresh_table()

    def refresh_table(self):
        if not hasattr(self, "tree") or not self.tree.winfo_exists():
            return
        self.tree.delete(*self.tree.get_children())
        for r in self.results[-500:]:
            self.tree.insert("", "end", values=(r["category"], r["term"], r["path"]))

    def confirm_scan(self):
        if self.scanning:
            return
        ok = messagebox.askyesno(APP,
            "Начать проверку доступных пользовательских папок на всех найденных дисках?\n\n"
            "Проверяются только названия файлов и папок. Проверка может занять много времени.")
        if ok:
            self.start_scan("Все")

    def stop_scan(self):
        self.stop_flag.set()
        if hasattr(self, "status"):
            self.status.config(text="Остановка после текущей операции…")

    def start_scan(self, mode):
        if self.scanning:
            messagebox.showinfo(APP, "Проверка уже выполняется.")
            return
        self.results = []
        self.scanning = True
        self.stop_flag.clear()
        self.show("Полная проверка" if mode == "Все" else mode)
        if not hasattr(self, "status"):
            self.status_panel()
        self.status.config(text="Подготовка…")
        self.progress.start(12)
        threading.Thread(target=self.worker, args=(mode,), daemon=True).start()

    def find_roots(self):
        roots = []
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.isdir(drive):
                # Search user data folders only; do not crawl Windows/system or app-installation folders.
                for item in SCAN_ROOTS:
                    candidate = os.path.join(drive, item)
                    if os.path.isdir(candidate):
                        roots.append(candidate)
                # On system drive, include each profile's AppData and .minecraft explicitly.
                users = os.path.join(drive, "Users")
                if os.path.isdir(users):
                    try:
                        for user in os.listdir(users):
                            up = os.path.join(users, user)
                            if not os.path.isdir(up):
                                continue
                            for rel in [".minecraft", "AppData\\Roaming", "AppData\\Local",
                                        "Downloads", "Desktop", "Documents"]:
                                p = os.path.join(up, rel)
                                if os.path.isdir(p):
                                    roots.append(p)
                    except OSError:
                        pass
        # Remove duplicate and nested roots to avoid scanning same content repeatedly.
        unique = []
        for p in sorted(set(roots), key=lambda x: (x.count(os.sep), x.lower())):
            if not any(os.path.commonpath([p, r]).lower() == r.lower() for r in unique):
                unique.append(p)
        return unique

    def worker(self, mode):
        groups = CATEGORIES
        if mode == "ExLoader":
            groups = {"ExLoader": CATEGORIES["ExLoader"]}
        elif mode == "Чит-клиенты":
            groups = {"Чит-клиенты Minecraft": CATEGORIES["Чит-клиенты Minecraft"]}
        roots = self.find_roots() if mode == "Все" else self.find_roots()
        count = 0
        found = []
        seen = set()
        for base in roots:
            if self.stop_flag.is_set():
                break
            for current, dirs, files in os.walk(base, onerror=lambda e: None):
                if self.stop_flag.is_set():
                    break
                dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS and not d.startswith(".")]
                for name, kind in [(d, "Папка") for d in dirs] + [(f, "Файл") for f in files]:
                    count += 1
                    low = name.lower()
                    for category, terms in groups.items():
                        for term in terms:
                            if term in low:
                                path = os.path.join(current, name)
                                key = (category, term, path)
                                if key not in seen:
                                    seen.add(key)
                                    found.append({"category": category, "term": term,
                                                  "path": path, "kind": kind})
                if count % 500 == 0:
                    self.q.put(("progress", count, len(found), base))
        self.q.put(("done", count, found, self.stop_flag.is_set()))

    def poll_queue(self):
        try:
            while True:
                item = self.q.get_nowait()
                if item[0] == "progress":
                    _, count, hits, path = item
                    if hasattr(self, "status") and self.status.winfo_exists():
                        self.status.config(text=f"Проверяется: {path}")
                        self.count.config(text=f"Объектов просмотрено: {count:,} • Совпадений: {hits}")
                elif item[0] == "done":
                    _, count, found, stopped = item
                    self.results = found
                    self.scanning = False
                    if hasattr(self, "progress") and self.progress.winfo_exists():
                        self.progress.stop()
                    if hasattr(self, "status") and self.status.winfo_exists():
                        self.status.config(text="Остановлено" if stopped else "Проверка завершена")
                        self.count.config(text=f"Объектов просмотрено: {count:,} • Совпадений: {len(found)}")
                    self.refresh_table()
                    messagebox.showinfo(APP,
                        f"Проверено объектов: {count:,}\nСовпадений: {len(found)}\n\n"
                        "Совпадения по названиям не доказывают запуск или использование читов.")
        except Empty:
            pass
        self.root.after(150, self.poll_queue)

    def load_processes(self):
        if not hasattr(self, "proc_text") or not self.proc_text.winfo_exists():
            return
        self.proc_text.delete("1.0", "end")
        try:
            out = subprocess.check_output(["tasklist"], text=True, errors="replace",
                                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.proc_text.insert("end", out)
        except Exception as e:
            self.proc_text.insert("end", f"Не удалось получить список процессов: {e}")

    def launch(self, cmd):
        try:
            subprocess.Popen(cmd, shell=False)
        except Exception as e:
            messagebox.showerror(APP, str(e))

    def save_report(self):
        if not self.results:
            messagebox.showinfo(APP, "Совпадений для отчёта нет.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt",
            filetypes=[("Текстовый отчёт", "*.txt")],
            initialfile="SharpGrief_Checker_Report.txt")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"{APP}\nДата: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
            f.write("Проверялись только имена файлов и папок в выбранных приложением пользовательских каталогах.\n")
            f.write("Содержимое файлов не читалось. Совпадение не является доказательством нарушения.\n\n")
            for r in self.results:
                f.write(f"[{r['category']}] {r['term']} ({r['kind']}) — {r['path']}\n")
        messagebox.showinfo(APP, "Отчёт сохранён.")

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
