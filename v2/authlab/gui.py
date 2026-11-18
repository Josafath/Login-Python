"""Tkinter interface. All decisions live in auth/storage/directory; this only draws.

Screens (each one is a Frame, swapped by App.show like in v1):
    SignUpView -> LoginView -> HomeView -> LabView
"""
from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk
from typing import Optional

from .algorithms import ALGORITHMS, Metrics
from .auth import USERNAME_RE, AccountLocked, AuthError, AuthService, LoginResult, RegistrationError, normalize_username
from .directory import COLUMNS, SEARCH_MODES, Directory, benchmark, demo_users
from .security import password_strength
from .storage import User

# Dark theme; the accent colours are the ones v1 used for its buttons.
BG = "#16181d"
PANEL = "#22252d"
FIELD = "#2c3039"
TEXT = "#eef0f4"
MUTED = "#8b919e"
ACCENT = "#07bedb"
PINK = "#fc92e2"
GOOD = "#4ade80"
BAD = "#f87171"
# Strength meter colours from "very weak" to "very strong".
STRENGTH_COLORS = ("#f87171", "#fb923c", "#facc15", "#4ade80", "#22c55e")
FONT = "Helvetica"
DEMO_USERS = 500


def mask_email(email: str) -> str:
    """'carla@gmail.com' -> 'c****@gmail.com': the Lab never shows full emails."""
    name, _, domain = email.partition("@")
    return f"{name[:1]}{'*' * max(len(name) - 1, 3)}@{domain}"


def pretty_date(iso: Optional[str]) -> str:
    """'2026-11-17T15:30:00' -> '2026-11-17 15:30' ('—' if missing)."""
    return iso.replace("T", " ")[:16] if iso else "—"


class App(tk.Tk):
    def __init__(self, service: AuthService) -> None:
        super().__init__()
        self.service = service
        self.title("AuthLab — v2")
        self.configure(bg=BG)
        # Wide enough for the Lab's table plus its explanation panel.
        self.geometry("1080x700")
        self.minsize(960, 640)
        self._style()
        self._view: Optional[tk.Frame] = None
        # First run (no accounts yet): start on sign up instead of log in.
        self.show(LoginView if len(service.store) else SignUpView)

    def show(self, view_cls: type, **kwargs) -> None:
        """Replace the current screen with a new one (same idea as v1's switch_frames)."""
        # Destroy the old screen first: its destroy() removes key bindings,
        # and it must not remove the ones the new screen is about to add.
        if self._view is not None:
            self._view.destroy()
        self._view = view_cls(self, **kwargs)
        self._view.pack(fill="both", expand=True)

    def _style(self) -> None:
        """Colour the ttk widgets (table, drop-downs) to match the dark theme."""
        style = ttk.Style(self)
        style.theme_use("clam")  # the only built-in theme that accepts custom colours everywhere
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT,
                        rowheight=26, borderwidth=0, font=(FONT, 10))
        style.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", BG)])
        style.configure("Treeview.Heading", background=FIELD, foreground=TEXT, relief="flat",
                        font=(FONT, 10, "bold"))
        style.map("Treeview.Heading", background=[("active", ACCENT)], foreground=[("active", BG)])
        style.configure("TCombobox", fieldbackground=FIELD, background=FIELD, foreground=TEXT,
                        arrowcolor=TEXT, borderwidth=0)
        style.map("TCombobox", fieldbackground=[("readonly", FIELD)], foreground=[("readonly", TEXT)],
                  selectbackground=[("readonly", FIELD)], selectforeground=[("readonly", TEXT)])
        style.configure("Vertical.TScrollbar", background=FIELD, troughcolor=PANEL, arrowcolor=TEXT, borderwidth=0)
        # The list that drops down from a Combobox is a classic Tk widget.
        self.option_add("*TCombobox*Listbox.background", FIELD)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.option_add("*TCombobox*Listbox.selectBackground", ACCENT)


# ------------------------------------------------------------ widget helpers

def label(parent: tk.Widget, text: str = "", size: int = 11, color: str = TEXT,
          bold: bool = False, **kw) -> tk.Label:
    return tk.Label(parent, text=text, bg=parent["bg"], fg=color,
                    font=(FONT, size, "bold" if bold else "normal"), **kw)


def entry(parent: tk.Widget, var: tk.StringVar, secret: bool = False, width: int = 32) -> tk.Entry:
    return tk.Entry(parent, textvariable=var, show="•" if secret else "", width=width,
                    bg=FIELD, fg=TEXT, insertbackground=TEXT, relief="flat",
                    highlightthickness=1, highlightbackground=FIELD, highlightcolor=ACCENT,
                    font=(FONT, 12))


def button(parent: tk.Widget, text: str, command, color: str = ACCENT) -> tk.Button:
    return tk.Button(parent, text=text, command=command, bg=color, fg=BG, activebackground=TEXT,
                     activeforeground=BG, relief="flat", bd=0, padx=16, pady=6,
                     font=(FONT, 11, "bold"), cursor="hand2")


def link(parent: tk.Widget, text: str, command) -> tk.Button:
    """A button that looks like a text link."""
    return tk.Button(parent, text=text, command=command, bg=parent["bg"], fg=ACCENT, bd=0,
                     relief="flat", activebackground=parent["bg"], activeforeground=PINK,
                     highlightthickness=0, font=(FONT, 10, "underline"), cursor="hand2")


def card(parent: tk.Widget) -> tk.Frame:
    """A centred panel that holds a form."""
    frame = tk.Frame(parent, bg=PANEL, padx=36, pady=28)
    frame.place(relx=0.5, rely=0.5, anchor="center")
    return frame


def busy(widget: tk.Widget, on: bool) -> None:
    """Show a waiting cursor while a password is hashed (~0.2 s on purpose)."""
    widget.winfo_toplevel().configure(cursor="watch" if on else "")
    widget.update_idletasks()


# ------------------------------------------------------------------ screens

class SignUpView(tk.Frame):
    def __init__(self, app: App) -> None:
        super().__init__(app, bg=BG)
        self.app = app
        self.username, self.email = tk.StringVar(), tk.StringVar()
        self.password, self.confirm = tk.StringVar(), tk.StringVar()

        box = card(self)
        label(box, "Create your account", 20, bold=True).pack(anchor="w")
        label(box, "Your password is stored as a salted PBKDF2 hash, never as text.", 9, MUTED).pack(anchor="w", pady=(2, 14))

        label(box, "Username", 10, MUTED).pack(anchor="w")
        first = entry(box, self.username)
        first.pack(fill="x")
        self.name_status = label(box, "", 9, MUTED)  # live "available / taken"
        self.name_status.pack(anchor="w", pady=(2, 8))

        label(box, "Email", 10, MUTED).pack(anchor="w")
        entry(box, self.email).pack(fill="x", pady=(0, 10))

        label(box, "Password", 10, MUTED).pack(anchor="w")
        entry(box, self.password, secret=True).pack(fill="x")
        # Strength meter: 5 segments that light up with the score (0-4).
        self.meter = tk.Canvas(box, height=6, bg=PANEL, highlightthickness=0)
        self.meter.pack(fill="x", pady=(6, 2))
        self.strength_text = label(box, "", 9, MUTED, justify="left")
        self.strength_text.pack(anchor="w", pady=(0, 8))

        label(box, "Confirm password", 10, MUTED).pack(anchor="w")
        entry(box, self.confirm, secret=True).pack(fill="x", pady=(0, 10))

        self.errors = label(box, "", 10, BAD, justify="left", wraplength=360)
        self.errors.pack(anchor="w")
        button(box, "Create account", self.submit).pack(fill="x", pady=(8, 10))
        row = tk.Frame(box, bg=PANEL)
        row.pack()
        label(row, "Already have an account?", 10, MUTED).pack(side="left")
        link(row, "Log in", lambda: app.show(LoginView)).pack(side="left")

        # Re-check as the user types.
        self.username.trace_add("write", lambda *_: self._check_username())
        for var in (self.password, self.username):
            var.trace_add("write", lambda *_: self._check_password())
        self.bind_all("<Return>", lambda _e: self.submit())
        first.focus_set()
        self._check_password()

    def destroy(self) -> None:
        self.unbind_all("<Return>")  # don't leave the Enter key pointing to a dead screen
        super().destroy()

    def _check_username(self) -> None:
        name = normalize_username(self.username.get())
        if not name:
            self.name_status.configure(text="", fg=MUTED)
        elif not USERNAME_RE.match(name):
            self.name_status.configure(text="3-20 characters: letters, numbers, '_' and '.'", fg=MUTED)
        else:
            metrics = Metrics()
            taken = self.app.service.store.exists(name, metrics)
            text = "✘ already taken" if taken else "✔ available"
            # Show the algorithm at work: a binary search over every account.
            self.name_status.configure(
                text=f"{text}   ·   binary search over {len(self.app.service.store)} users: "
                     f"{metrics.comparisons} comparisons",
                fg=BAD if taken else GOOD)

    def _check_password(self) -> None:
        s = password_strength(self.password.get(), normalize_username(self.username.get()))
        self.meter.delete("all")
        width = max(self.meter.winfo_width(), 360)
        segment = width / 5
        # Light up score + 1 segments (empty password: none) in the score's colour.
        lit = s.score + 1 if self.password.get() else 0
        for i in range(5):
            color = STRENGTH_COLORS[s.score] if i < lit else FIELD
            self.meter.create_rectangle(i * segment + 1, 0, (i + 1) * segment - 3, 6, fill=color, outline="")
        if not self.password.get():
            self.strength_text.configure(text="Use 8+ characters with a mix of letters, numbers and symbols")
        else:
            tip = f"  ·  {s.problems[0]}" if s.problems else ""
            self.strength_text.configure(text=f"{s.label} (~{s.entropy_bits:.0f} bits){tip}")

    def submit(self) -> None:
        busy(self, True)
        try:
            user = self.app.service.register(self.username.get(), self.email.get(),
                                             self.password.get(), self.confirm.get())
        except RegistrationError as err:
            self.errors.configure(text="\n".join(f"• {p}" for p in err.problems))
            return
        finally:
            busy(self, False)
        self.app.show(LoginView, notice=f"Account created. Welcome, {user.username}! Now log in.",
                      username=user.username)


class LoginView(tk.Frame):
    def __init__(self, app: App, notice: str = "", username: str = "") -> None:
        super().__init__(app, bg=BG)
        self.app = app
        self.username, self.password = tk.StringVar(value=username), tk.StringVar()

        box = card(self)
        label(box, "Log in", 20, bold=True).pack(anchor="w")
        label(box, notice, 10, GOOD, wraplength=340, justify="left").pack(anchor="w", pady=(2, 12))

        label(box, "Username", 10, MUTED).pack(anchor="w")
        name_entry = entry(box, self.username)
        name_entry.pack(fill="x", pady=(0, 10))
        label(box, "Password", 10, MUTED).pack(anchor="w")
        pass_entry = entry(box, self.password, secret=True)
        pass_entry.pack(fill="x", pady=(0, 6))

        self.error = label(box, "", 10, BAD, wraplength=340, justify="left")
        self.error.pack(anchor="w")
        button(box, "Log in", self.submit).pack(fill="x", pady=(8, 10))
        row = tk.Frame(box, bg=PANEL)
        row.pack()
        label(row, "New here?", 10, MUTED).pack(side="left")
        link(row, "Create an account", lambda: app.show(SignUpView)).pack(side="left")

        self.bind_all("<Return>", lambda _e: self.submit())
        (pass_entry if username else name_entry).focus_set()

    def destroy(self) -> None:
        self.unbind_all("<Return>")
        super().destroy()

    def submit(self) -> None:
        busy(self, True)
        try:
            result = self.app.service.login(self.username.get(), self.password.get())
        except AccountLocked as err:
            self.error.configure(text=str(err))
            return
        except AuthError as err:
            self.error.configure(text=str(err))
            self.password.set("")
            return
        finally:
            busy(self, False)
        self.app.show(HomeView, result=result)


class HomeView(tk.Frame):
    def __init__(self, app: App, result: LoginResult) -> None:
        super().__init__(app, bg=BG)
        user = result.user
        box = card(self)
        label(box, f"Welcome, {user.username}!", 22, bold=True).pack(anchor="w")
        label(box, "You're logged in.", 10, MUTED).pack(anchor="w", pady=(0, 16))
        info = tk.Frame(box, bg=PANEL)
        info.pack(anchor="w")
        rows = [
            ("Email", user.email),
            ("Member since", pretty_date(user.created_at)),
            ("Previous login", pretty_date(result.previous_login) if result.previous_login else "This is your first login"),
        ]
        for i, (name, value) in enumerate(rows):
            label(info, name, 10, MUTED).grid(row=i, column=0, sticky="w", pady=3)
            label(info, value, 11).grid(row=i, column=1, sticky="w", padx=(20, 0))
        actions = tk.Frame(box, bg=PANEL)
        actions.pack(fill="x", pady=(22, 0))
        button(actions, "Open Algorithms Lab", lambda: app.show(LabView, result=result)).pack(side="left")
        button(actions, "Log out", lambda: app.show(LoginView, notice="You logged out."), PINK).pack(side="right", padx=(16, 0))


# ----------------------------------------------------------- Algorithms Lab
# The Lab screen is in Spanish. The internal names (search modes, columns,
# algorithms) stay in English because the logic and the tests use them;
# these tables translate them only for display.

SEARCH_LABELS = {
    "Prefix · Trie": "Prefijo · Trie",
    "Prefix · Binary search": "Prefijo · Búsqueda binaria",
}
COLUMN_LABELS = {
    "Username": "Usuario",
    "Email": "Correo",
    "Member since": "Registrado",
    "Last login": "Último acceso",
}

# (title, how it works, cost) for each search mode, shown in the help panel.
SEARCH_HELP = {
    "Prefix · Trie": (
        "Prefijo con Trie",
        "Busca los nombres que EMPIEZAN con lo que escribes. Usa un árbol donde cada "
        "nodo es una letra: baja una letra por cada carácter escrito y luego recoge "
        "todos los nombres que cuelgan de ahí.",
        "Costo: depende de cuántas letras escribes y cuántos resultados hay, "
        "no de cuántos usuarios existen.",
    ),
    "Prefix · Binary search": (
        "Prefijo con búsqueda binaria",
        "Hace la misma búsqueda que el Trie, pero sobre la lista ordenada: mira el "
        "usuario de en medio, descarta la mitad donde no puede estar el resultado y "
        "repite. Deben salir exactamente los mismos resultados que con el Trie.",
        "Costo: O(log n). Con 1,000,000 de usuarios bastan unas 20 comparaciones.",
    ),
}

# (title, how it works, cost and stability) for each sorting algorithm.
SORT_HELP = {
    "Merge sort": (
        "Merge sort (ordenamiento por mezcla)",
        "Divide la lista en mitades, ordena cada mitad y luego las mezcla tomando "
        "siempre el menor de los dos. Para trozos pequeños usa insertion sort, y se "
        "salta las mezclas cuando las mitades ya están en orden.",
        "O(n log n) siempre  ·  Estable: sí",
    ),
    "Quick sort": (
        "Quick sort (ordenamiento rápido)",
        "Elige un pivote al azar y separa la lista en tres grupos: menores, iguales y "
        "mayores que el pivote. Repite con los menores y los mayores. Suele ser el más "
        "rápido en la práctica.",
        "O(n log n) en promedio  ·  Estable: no",
    ),
    "Heap sort": (
        "Heap sort (ordenamiento por montículo)",
        "Convierte la lista en un montículo: un árbol donde cada padre es mayor que sus "
        "hijos. Saca el mayor, lo pone al final y repara el árbol, hasta vaciarlo. "
        "No usa memoria extra.",
        "O(n log n) siempre  ·  Estable: no",
    ),
    "Insertion sort": (
        "Insertion sort (ordenamiento por inserción)",
        "Como ordenar cartas en la mano: toma el siguiente elemento y lo recorre a la "
        "izquierda hasta su lugar. Muy rápido con listas pequeñas o casi ordenadas, "
        "pero muy lento con muchas desordenadas.",
        "O(n²)  ·  Estable: sí",
    ),
}


def report_es(report) -> str:
    """Spanish version of a directory.Report, for the status lines."""
    return (f"{report.results} resultado(s)  ·  {report.work:,} comparaciones "
            f"en {report.millis:.2f} ms")


class LabView(tk.Frame):
    """Search and sort the users with the algorithms written from scratch."""

    def __init__(self, app: App, result: LoginResult) -> None:
        super().__init__(app, bg=BG, padx=20, pady=16)
        self.app, self.result = app, result
        self.query = tk.StringVar()
        # The menus show Spanish names; the variables hold the internal English keys.
        self.mode_label = tk.StringVar(value=SEARCH_LABELS[SEARCH_MODES[0]])
        self.algorithm = tk.StringVar(value="Merge sort")
        self.include_demo = tk.BooleanVar(value=True)
        self.sort_column: Optional[str] = None  # None: natural (username) order
        self.sort_reverse = False

        header = tk.Frame(self, bg=BG)
        header.pack(fill="x")
        label(header, "Laboratorio de algoritmos", 20, bold=True).pack(side="left")
        link(header, "← Volver", lambda: app.show(HomeView, result=result)).pack(side="right")
        label(self, "Todas las búsquedas y ordenamientos usan código escrito desde cero "
                    "(sin sorted() ni bisect).", 9, MUTED).pack(anchor="w", pady=(0, 10))

        controls = tk.Frame(self, bg=BG)
        controls.pack(fill="x")
        label(controls, "Buscar", 10, MUTED).grid(row=0, column=0, sticky="w")
        search = entry(controls, self.query, width=22)
        search.grid(row=1, column=0, sticky="we", padx=(0, 10))
        label(controls, "Buscar con", 10, MUTED).grid(row=0, column=1, sticky="w")
        ttk.Combobox(controls, textvariable=self.mode_label, values=list(SEARCH_LABELS.values()),
                     state="readonly", width=26).grid(row=1, column=1, padx=(0, 10))
        label(controls, "Ordenar con", 10, MUTED).grid(row=0, column=2, sticky="w")
        ttk.Combobox(controls, textvariable=self.algorithm, values=list(ALGORITHMS), state="readonly",
                     width=14).grid(row=1, column=2, padx=(0, 10))
        button(controls, "Comparar algoritmos", self.open_benchmark, PINK).grid(row=1, column=3)
        controls.columnconfigure(0, weight=1)
        tk.Checkbutton(self, text=f"Incluir {DEMO_USERS} usuarios de prueba (solo en memoria, no se guardan)",
                       variable=self.include_demo, command=self.reload, bg=BG, fg=MUTED,
                       selectcolor=FIELD, activebackground=BG, activeforeground=TEXT,
                       highlightthickness=0, font=(FONT, 9)).pack(anchor="w", pady=(8, 6))

        # Body: the table on the left, the explanation panel on the right.
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)
        self._build_help_panel(body)

        # The table: clicking a header sorts by that column with the chosen algorithm.
        table_frame = tk.Frame(body, bg=BG)
        table_frame.pack(side="left", fill="both", expand=True)
        self.table = ttk.Treeview(table_frame, columns=list(COLUMNS), show="headings")
        for col in COLUMNS:
            self.table.heading(col, text=COLUMN_LABELS[col], command=lambda c=col: self.sort_by(c))
            self.table.column(col, width=130, anchor="w")
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        self.table.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Two status lines: what the search did and what the sort did.
        self.search_status = label(self, "", 10, ACCENT)
        self.search_status.pack(anchor="w", pady=(8, 0))
        self.sort_status = label(self, "", 10, PINK)
        self.sort_status.pack(anchor="w")

        self.query.trace_add("write", lambda *_: self.refresh())
        self.mode_label.trace_add("write", lambda *_: self.refresh())
        self.algorithm.trace_add("write", lambda *_: self.refresh())
        search.focus_set()
        self.reload()

    @property
    def mode(self) -> str:
        """Internal search mode for the Spanish label selected in the menu."""
        return next(k for k, v in SEARCH_LABELS.items() if v == self.mode_label.get())

    # ---------- explanation panel ----------

    def _build_help_panel(self, parent: tk.Frame) -> None:
        """Read-only text panel on the right that explains the current choices."""
        panel = tk.Frame(parent, bg=PANEL, padx=14, pady=12, width=300)
        panel.pack(side="right", fill="y", padx=(12, 0))
        panel.pack_propagate(False)  # keep the 300 px width whatever the text length
        self.help = tk.Text(panel, bg=PANEL, fg=TEXT, wrap="word", relief="flat", bd=0,
                            highlightthickness=0, font=(FONT, 10), cursor="arrow",
                            padx=0, pady=0, spacing1=1, spacing3=3)
        # Scrollbar for when the explanation is taller than the window.
        scroll = ttk.Scrollbar(panel, orient="vertical", command=self.help.yview)
        self.help.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.help.pack(side="left", fill="both", expand=True)
        # Text styles ("tags") used to format the explanation.
        self.help.tag_configure("title", font=(FONT, 12, "bold"), foreground=TEXT, spacing3=6)
        self.help.tag_configure("search", font=(FONT, 10, "bold"), foreground=ACCENT, spacing1=10)
        self.help.tag_configure("sort", font=(FONT, 10, "bold"), foreground=PINK, spacing1=10)
        self.help.tag_configure("tips", font=(FONT, 10, "bold"), foreground=GOOD, spacing1=10)
        self.help.tag_configure("cost", foreground=MUTED, font=(FONT, 9, "italic"))
        self.help.tag_configure("result", foreground=TEXT, font=(FONT, 10, "bold"))

    def _explain(self, search_report, sort_report, total: int) -> None:
        """Rewrite the panel for the current search mode, algorithm and results."""
        t = self.help
        t.configure(state="normal")  # a disabled Text can't be edited, even by code
        t.delete("1.0", "end")

        def add(text: str, tag: str = "") -> None:
            t.insert("end", text + "\n", tag)

        add("¿Qué es esta pantalla?", "title")
        add("Aquí ves trabajar a los algoritmos. Cada uno cuenta sus comparaciones "
            "(cuántas veces comparó dos valores): menos = más eficiente.")

        # --- search mode: result first, then how it works ---
        title, how, cost = SEARCH_HELP[self.mode]
        add(f"BUSCAR CON: {title}", "search")
        if search_report is None:
            add("Escribe algo en «Buscar» para probarlo.", "cost")
        else:
            add(f"→ Encontró {search_report.results} resultado(s) con "
                f"{search_report.work:,} comparaciones. Revisar uno por uno "
                f"habría costado hasta {total:,}.", "result")
        add(how)
        add(cost, "cost")

        # --- sorting algorithm: result first, then how it works ---
        title, how, cost = SORT_HELP[self.algorithm.get()]
        add(f"ORDENAR CON: {title}", "sort")
        n = sort_report.results if sort_report else 0
        if sort_report is None:
            add("Pulsa el encabezado de una columna de la tabla para ordenarla.", "cost")
        elif n > 1:
            fast = round(n * math.log2(n))  # what an O(n log n) algorithm needs, roughly
            slow = n * (n - 1) // 2  # insertion sort's worst case
            add(f"→ Ordenó {n:,} usuarios con {sort_report.work:,} comparaciones. "
                f"Referencia: O(n log n) ≈ {fast:,} · O(n²) peor caso = {slow:,}.", "result")
        add(how)
        add(cost, "cost")
        add("Estable = los usuarios con el mismo valor conservan el orden que tenían.", "cost")

        # --- suggestions ---
        add("PRUEBA ESTO", "tips")
        add("1. Escribe «ma» y cambia entre Trie y Búsqueda binaria: mismos resultados, "
            "distinto trabajo.")
        add("2. Ordena por Usuario con Insertion sort y luego con Merge sort, "
            "y compara las comparaciones.")
        add("3. Pulsa «Comparar algoritmos» para ver los 4 lado a lado.")
        t.configure(state="disabled")  # read-only for the user

    # ---------- data ----------

    def reload(self) -> None:
        """Rebuild the directory (real users + optional demo users) and redraw."""
        users = self.app.service.store.all()
        if self.include_demo.get():
            users += demo_users(DEMO_USERS)
        self.directory = Directory(users)
        self.refresh()

    def sort_by(self, column: str) -> None:
        # Clicking the same header again flips the direction.
        self.sort_reverse = not self.sort_reverse if self.sort_column == column else False
        self.sort_column = column
        self.refresh()

    def refresh(self) -> None:
        """Search, then sort, then fill the table and the panel. Called on every change."""
        query = self.query.get().strip()
        total = len(self.directory.users)
        search_report = sort_report = None
        if query:
            rows, search_report = self.directory.search(query, self.mode)
            self.search_status.configure(
                text=f"Búsqueda ({SEARCH_LABELS[self.mode]}): {report_es(search_report)}")
        else:
            rows = self.directory.users
            self.search_status.configure(
                text=f"{total} usuarios · la lista se mantiene ordenada por usuario, "
                     f"por eso las búsquedas pueden ser binarias")
        arrow = " ▼" if self.sort_reverse else " ▲"
        if self.sort_column:
            rows, sort_report = self.directory.sort(rows, self.sort_column, self.algorithm.get(), self.sort_reverse)
            self.sort_status.configure(
                text=f"Orden por {COLUMN_LABELS[self.sort_column]}{arrow} con "
                     f"{self.algorithm.get()}: {report_es(sort_report)}")
        else:
            self.sort_status.configure(text="Pulsa el encabezado de una columna para ordenarla "
                                            "con el algoritmo elegido")
        for col in COLUMNS:
            mark = arrow if col == self.sort_column else ""
            self.table.heading(col, text=COLUMN_LABELS[col] + mark)
        self._fill(rows)
        self._explain(search_report, sort_report, total)

    def _fill(self, rows: list[User]) -> None:
        self.table.delete(*self.table.get_children())
        me = self.result.user.username
        for user in rows:
            values = (user.username, mask_email(user.email), pretty_date(user.created_at), pretty_date(user.last_login))
            # Highlight the logged-in user's own row.
            self.table.insert("", "end", values=values, tags=("me",) if user.username == me else ())
        self.table.tag_configure("me", foreground=ACCENT)

    # ---------- benchmark window ----------

    def open_benchmark(self) -> None:
        win = tk.Toplevel(self, bg=BG, padx=20, pady=16)
        win.title("Comparar algoritmos")
        win.transient(self.winfo_toplevel())
        label(win, "Ordenando 1,500 usuarios desordenados por nombre", 13, bold=True).pack(anchor="w")
        label(win, "Los 4 algoritmos ordenan exactamente la misma lista. "
                   "Menos comparaciones = más eficiente.", 9, MUTED).pack(anchor="w")
        status = label(win, "Ejecutando…", 10, MUTED)
        status.pack(anchor="w", pady=(2, 10))
        cols = ("Algoritmo", "Estable", "Comparaciones", "Tiempo (ms)", "Correcto")
        table = ttk.Treeview(win, columns=cols, show="headings", height=4)
        for c in cols:
            table.heading(c, text=c)
            table.column(c, width=120, anchor="w")
        table.pack()

        def run() -> None:
            rows = benchmark(1500)
            for r in rows:
                table.insert("", "end", values=(r.algorithm, "sí" if r.stable else "no",
                                                f"{r.comparisons:,}", f"{r.millis:.1f}", "✔" if r.correct else "✘"))
            fewest = min(rows, key=lambda r: r.comparisons)
            most = max(rows, key=lambda r: r.comparisons)
            status.configure(
                text=f"Menos comparaciones: {fewest.algorithm}. {most.algorithm} hizo "
                     f"{most.comparisons / fewest.comparisons:.0f} veces más. "
                     f"Resultados verificados con sorted() de Python.")

        # Let the window appear before the (slow) insertion sort starts.
        win.after(50, run)



def run(service: AuthService) -> None:
    """Create the window and start Tk's event loop (blocks until it's closed)."""
    App(service).mainloop()
