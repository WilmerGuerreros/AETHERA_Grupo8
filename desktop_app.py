"""Interfaz de escritorio para Aethera, construida con Tkinter."""

import queue
import math
import threading
import tkinter as tk
from datetime import date, datetime
from tkinter import ttk

from ChatSession import ChatSession
from tools.calendario_academico import calendario_academico
from tools.evaluar_carga_academica import evaluar_riesgo_sobrecarga
from tools.servicios_ayuda import buscar_servicios_ayuda


COLORS = {
    "background": "#090d1b",
    "sidebar": "#0d1427",
    "surface": "#111a30",
    "surface_light": "#17223c",
    "border": "#263252",
    "text": "#f5f7ff",
    "muted": "#9ba8c7",
    "accent": "#6558f5",
    "accent_light": "#8b83ff",
    "green": "#35d5a0",
    "yellow": "#f6c85f",
    "red": "#ff7885",
}

FONT = "Segoe UI"
SERVICE_CATEGORIES = {
    "Presión académica": "academic_pressure",
    "Apoyo social": "social_support",
    "Orientación vocacional": "career_concern",
    "Sueño y rutinas": "sleep_and_routine",
    "Orientación sobre servicios": "service_navigation",
}
SERVICE_TYPES = {
    "counseling": "Orientación",
    "peer_support": "Acompañamiento entre pares",
    "career_guidance": "Orientación vocacional",
}
SERVICE_DISTRICTS = {
    "Todos los distritos": None,
    "Distrito Gaia": "DIST_GAIA",
    "Distrito Horizon": "DIST_HORIZON",
    "Distrito Nebula": "DIST_NEBULA",
    "Distrito Quantum": "DIST_QUANTUM",
    "Distrito Vector": "DIST_VECTOR",
}
SERVICE_CHANNELS = {
    "in_person": "Presencial",
    "digital": "En línea",
    "phone": "Teléfono",
}
WEEKDAYS = {
    "Mon-Fri": "Lunes a viernes",
    "Mon-Sat": "Lunes a sábado",
    "Mon-Sun": "Todos los días",
}


class RoundedFrame(tk.Frame):
    """Marco con fondo redondeado dibujado en un canvas de Tk."""

    def __init__(self, parent, bg, border, radius=14, **kwargs):
        parent_bg = parent.cget("bg")
        super().__init__(parent, bg=parent_bg, **kwargs)
        self.fill = bg
        self.border = border
        self.radius = radius
        self.canvas = tk.Canvas(self, bg=parent_bg, highlightthickness=0, bd=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.bind("<Configure>", self._draw)

    def _draw(self, _event=None):
        width = self.winfo_width()
        height = self.winfo_height()
        if width < 2 or height < 2:
            return
        radius = min(self.radius, width // 2, height // 2)
        points = []
        for center_x, center_y, start in (
            (width - radius, radius, -90),
            (width - radius, height - radius, 0),
            (radius, height - radius, 90),
            (radius, radius, 180),
        ):
            for step in range(7):
                angle = (start + step * 90 / 6) * 3.141592653589793 / 180
                points.extend(
                    (
                        center_x + radius * math.cos(angle),
                        center_y + radius * math.sin(angle),
                    )
                )
        self.canvas.delete("rounded")
        self.canvas.create_polygon(
            *points,
            smooth=True,
            splinesteps=24,
            fill=self.fill,
            outline=self.border,
            width=1,
            tags="rounded",
        )


class RoundedButton(tk.Canvas):
    """Botón de estilo minimalista con estados hover y presionado."""

    def __init__(self, parent, text, command, primary=False):
        self.primary = primary
        self.command = command
        self.text = text
        self.disabled = False
        self.hovered = False
        self.pressed = False
        self.focused = False
        self.bg_normal = COLORS["accent"] if primary else COLORS["surface_light"]
        self.bg_hover = COLORS["accent_light"] if primary else "#253252"
        width = max(104, len(text) * 7 + 34)
        super().__init__(
            parent,
            width=width,
            height=40,
            bg=getattr(parent, "fill", parent.cget("bg")),
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            takefocus=True,
        )
        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<FocusIn>", self._on_focus)
        self.bind("<FocusOut>", self._on_blur)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Return>", self._invoke)
        self.bind("<space>", self._invoke)

    def _draw(self, _event=None):
        self.delete("button")
        width = self.winfo_width()
        height = self.winfo_height()
        if width < 2 or height < 2:
            return
        radius = min(12, height // 2)
        points = []
        for center_x, center_y, start in (
            (width - radius, radius, -90),
            (width - radius, height - radius, 0),
            (radius, height - radius, 90),
            (radius, radius, 180),
        ):
            for step in range(7):
                angle = (start + step * 15) * 3.141592653589793 / 180
                points.extend(
                    (
                        center_x + radius * math.cos(angle),
                        center_y + radius * math.sin(angle),
                    )
                )
        fill = self.bg_normal
        if self.disabled:
            fill = COLORS["border"]
        elif self.pressed:
            fill = COLORS["accent"]
        elif self.hovered:
            fill = self.bg_hover
        self.create_polygon(
            *points,
            smooth=True,
            splinesteps=20,
            fill=fill,
            outline=COLORS["accent_light"] if self.focused else fill,
            width=2 if self.focused else 1,
            tags="button",
        )
        self.create_text(
            width / 2,
            height / 2,
            text=self.text,
            fill="#8792ad" if self.disabled else "white",
            font=(FONT, 9, "bold"),
            tags="button",
        )

    def _on_enter(self, _event):
        self.hovered = True
        self._draw()

    def _on_leave(self, _event):
        self.hovered = False
        self.pressed = False
        self._draw()

    def _on_focus(self, _event):
        self.focused = True
        self._draw()

    def _on_blur(self, _event):
        self.focused = False
        self._draw()

    def _on_press(self, _event):
        if not self.disabled:
            self.pressed = True
            self._draw()

    def _on_release(self, event):
        was_pressed = self.pressed
        self.pressed = False
        self._draw()
        inside = 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height()
        if was_pressed and inside and not self.disabled:
            self.command()

    def _invoke(self, _event=None):
        if not self.disabled:
            self.command()
        return "break"

    def configure(self, cnf=None, **kwargs):
        state = kwargs.pop("state", None)
        if state is not None:
            self.disabled = state == "disabled"
            self.configure(cursor="arrow" if self.disabled else "hand2")
            self._draw()
        if kwargs or cnf:
            super().configure(cnf, **kwargs)


class AetheraDesktopApp:
    def __init__(self, motor, historial, herramientas, guardar_historial):
        self.root = tk.Tk()
        self.root.title("Aethera | Acompañamiento académico")
        self.root.geometry("1440x900")
        self.root.minsize(1120, 720)
        self.root.configure(bg=COLORS["background"])
        self.event_queue = queue.Queue()
        self.current_page = "Inicio"
        self.busy = False

        self.chat = ChatSession(
            motor,
            historial,
            herramientas,
            al_completar_turno=lambda usuario, respuesta: guardar_historial(
                usuario,
                respuesta,
                motor.modelo,
            ),
        )

        self._configure_styles()
        self._build_shell()
        self.show_page("Inicio")
        self.root.after(80, self._process_queue)

    def _configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "Aethera.TCombobox",
            fieldbackground=COLORS["surface_light"],
            background=COLORS["surface_light"],
            foreground=COLORS["text"],
            arrowcolor=COLORS["text"],
            bordercolor=COLORS["border"],
            lightcolor=COLORS["border"],
            darkcolor=COLORS["border"],
            padding=9,
        )
        style.map(
            "Aethera.TCombobox",
            fieldbackground=[("readonly", COLORS["surface_light"])],
            foreground=[("readonly", COLORS["text"])],
        )

    def _build_shell(self):
        self.sidebar = tk.Frame(self.root, bg=COLORS["sidebar"], width=248)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand = tk.Frame(self.sidebar, bg=COLORS["sidebar"])
        brand.pack(fill="x", padx=22, pady=(25, 30))
        tk.Label(
            brand,
            text="✦",
            bg=COLORS["accent"],
            fg="white",
            font=(FONT, 18, "bold"),
            width=2,
            height=1,
        ).pack(side="left", padx=(0, 11), ipady=5)
        title = tk.Frame(brand, bg=COLORS["sidebar"])
        title.pack(side="left")
        tk.Label(
            title,
            text="AETHERA",
            bg=COLORS["sidebar"],
            fg=COLORS["text"],
            font=(FONT, 14, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title,
            text="Tu espacio académico",
            bg=COLORS["sidebar"],
            fg=COLORS["muted"],
            font=(FONT, 9),
        ).pack(anchor="w", pady=(2, 0))

        tk.Label(
            self.sidebar,
            text="MENÚ PRINCIPAL",
            bg=COLORS["sidebar"],
            fg="#7381a4",
            font=(FONT, 8, "bold"),
        ).pack(anchor="w", padx=24, pady=(0, 10))

        self.nav_buttons = {}
        for page, icon in (
            ("Inicio", "⌂"),
            ("Asistente IA", "✧"),
            ("Calendario", "▦"),
            ("Carga académica", "▤"),
            ("Servicios de apoyo", "♡"),
        ):
            button = tk.Button(
                self.sidebar,
                text=f"  {icon}    {page}",
                anchor="w",
                command=lambda selected=page: self.show_page(selected),
                relief="flat",
                bd=0,
                padx=14,
                pady=12,
                bg=COLORS["sidebar"],
                fg=COLORS["muted"],
                activebackground=COLORS["surface_light"],
                activeforeground=COLORS["text"],
                font=(FONT, 10),
                cursor="hand2",
            )
            button.pack(fill="x", padx=12, pady=2)
            button.bind(
                "<Enter>",
                lambda _event, item=button, selected_page=page: (
                    item.configure(
                        bg=COLORS["accent"] if self.current_page == selected_page else COLORS["surface_light"],
                        fg=COLORS["text"],
                    )
                ),
            )
            button.bind(
                "<Leave>",
                lambda _event, item=button, selected_page=page: (
                    item.configure(
                        bg=COLORS["accent"] if self.current_page == selected_page else COLORS["sidebar"],
                        fg="white" if self.current_page == selected_page else COLORS["muted"],
                    )
                ),
            )
            self.nav_buttons[page] = button

        spacer = tk.Frame(self.sidebar, bg=COLORS["sidebar"])
        spacer.pack(fill="both", expand=True)
        wellbeing = tk.Frame(
            self.sidebar,
            bg=COLORS["surface"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        wellbeing.pack(fill="x", padx=16, pady=(0, 16))
        tk.Label(
            wellbeing,
            text="Un paso a la vez",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=(FONT, 10, "bold"),
        ).pack(anchor="w", padx=13, pady=(12, 4))
        tk.Label(
            wellbeing,
            text="Organizarte también es cuidarte.",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=(FONT, 8),
            wraplength=185,
            justify="left",
        ).pack(anchor="w", padx=13, pady=(0, 12))

        self.main = tk.Frame(self.root, bg=COLORS["background"])
        self.main.pack(side="left", fill="both", expand=True)
        self.header = tk.Frame(
            self.main,
            bg=COLORS["background"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        self.header.pack(fill="x")
        self.page_title = tk.Label(
            self.header,
            text="Inicio",
            bg=COLORS["background"],
            fg=COLORS["text"],
            font=(FONT, 16, "bold"),
        )
        self.page_title.pack(side="left", padx=30, pady=20)
        tk.Label(
            self.header,
            text="Acompañamiento académico personalizado",
            bg=COLORS["background"],
            fg=COLORS["muted"],
            font=(FONT, 9),
        ).pack(side="left", padx=(4, 0), pady=20)
        tk.Label(
            self.header,
            text="●  AETHERA",
            bg=COLORS["background"],
            fg=COLORS["green"],
            font=(FONT, 9, "bold"),
        ).pack(side="right", padx=30, pady=20)

        self.content = tk.Frame(self.main, bg=COLORS["background"])
        self.content.pack(fill="both", expand=True, padx=30, pady=24)

    def _card(self, parent, **kwargs):
        return RoundedFrame(
            parent,
            bg=kwargs.pop("bg", COLORS["surface"]),
            border=kwargs.pop("border", COLORS["border"]),
            radius=kwargs.pop("radius", 14),
            **kwargs,
        )

    def _label(self, parent, text, size=10, color=None, weight="normal", **kwargs):
        return tk.Label(
            parent,
            text=text,
            bg=kwargs.pop("bg", COLORS["surface"]),
            fg=color or COLORS["text"],
            font=(FONT, size, weight),
            **kwargs,
        )

    def _button(self, parent, text, command, primary=False):
        return RoundedButton(parent, text, command, primary=primary)

    def show_page(self, page):
        if self.current_page == "Asistente IA" and page != "Asistente IA":
            for attribute in ("stream_bubble", "stream_text", "stream_content"):
                if hasattr(self, attribute):
                    delattr(self, attribute)
        self.current_page = page
        self.page_title.configure(text=page)
        for name, button in self.nav_buttons.items():
            selected = name == page
            button.configure(
                bg=COLORS["accent"] if selected else COLORS["sidebar"],
                fg="white" if selected else COLORS["muted"],
                font=(FONT, 10, "bold" if selected else "normal"),
            )
        for child in self.content.winfo_children():
            child.destroy()

        if page == "Inicio":
            self._show_dashboard()
        elif page == "Asistente IA":
            self._show_chat()
        elif page == "Calendario":
            self._show_calendar()
        elif page == "Carga académica":
            self._show_workload()
        elif page == "Servicios de apoyo":
            self._show_services()

    def _show_dashboard(self):
        self._label(
            self.content,
            f"Hola, estudiante  {self._greeting()}",
            size=24,
            weight="bold",
            bg=COLORS["background"],
        ).pack(anchor="w")
        self._label(
            self.content,
            "Este es tu espacio para organizarte y avanzar a tu ritmo.",
            color=COLORS["muted"],
            bg=COLORS["background"],
        ).pack(anchor="w", pady=(5, 20))

        welcome = self._card(self.content, bg="#171a3a")
        welcome.pack(fill="x", pady=(0, 18))
        left = tk.Frame(welcome, bg="#171a3a")
        left.pack(side="left", fill="both", expand=True, padx=24, pady=22)
        self._label(
            left,
            "Tu bienestar también forma parte del plan",
            size=16,
            weight="bold",
            bg="#171a3a",
        ).pack(anchor="w")
        self._label(
            left,
            "Cuéntale a Aethera qué tienes pendiente y construyan juntos un siguiente paso.",
            color="#c4c7e7",
            bg="#171a3a",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(7, 15))
        self._button(
            left,
            "Conversar con Aethera  →",
            lambda: self.show_page("Asistente IA"),
            primary=True,
        ).pack(anchor="w")
        self._label(
            welcome,
            "✦",
            size=58,
            color=COLORS["accent_light"],
            bg="#171a3a",
        ).pack(side="right", padx=45, pady=16)

        metrics = tk.Frame(self.content, bg=COLORS["background"])
        metrics.pack(fill="x", pady=(0, 18))
        for column in range(3):
            metrics.grid_columnconfigure(column, weight=1, uniform="metric")
        try:
            events = self._get_upcoming_events()
            risk = evaluar_riesgo_sobrecarga()
            if "error" in risk:
                raise ValueError(risk["error"])
            critical_weeks = len(risk["semanas_con_sobrecarga"])
            cards = [
                ("Próximos eventos", str(len(events)), "En el calendario académico", COLORS["accent_light"]),
                ("Semanas críticas", str(critical_weeks), "Detectadas en el calendario", COLORS["yellow"]),
                ("Planificación", "A tu ritmo", "Un paso concreto cada vez", COLORS["green"]),
            ]
            for index, (title, number, detail, accent) in enumerate(cards):
                self._metric_card(metrics, index, title, number, detail, accent)
        except (OSError, ValueError, KeyError, TypeError) as error:
            self._notice(
                self.content,
                f"No se pudieron cargar los indicadores académicos: {error}",
                COLORS["red"],
            )

        self._label(
            self.content,
            "Próximamente en tu calendario",
            size=14,
            weight="bold",
            bg=COLORS["background"],
        ).pack(anchor="w", pady=(3, 10))
        upcoming = self._card(self.content)
        upcoming.pack(fill="both", expand=True)
        try:
            events = self._get_upcoming_events()
            if not events:
                self._label(
                    upcoming,
                    "No hay eventos próximos en el calendario académico.",
                    color=COLORS["muted"],
                ).pack(anchor="w", padx=18, pady=18)
            else:
                for event in events[:4]:
                    self._event_row(upcoming, event)
        except (OSError, ValueError, KeyError, TypeError) as error:
            self._notice(
                upcoming,
                f"No se pudo leer el calendario académico: {error}",
                COLORS["red"],
            )
        self._button(
            self.content,
            "Ver calendario completo  →",
            lambda: self.show_page("Calendario"),
        ).pack(anchor="e", pady=(12, 0))

    def _greeting(self):
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "☀"
        if 12 <= hour < 19:
            return "☼"
        return "☾"

    def _metric_card(self, parent, column, title, number, detail, accent):
        card = self._card(parent)
        card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 8, 0))
        self._label(card, title, color=COLORS["muted"]).pack(anchor="w", padx=16, pady=(14, 4))
        self._label(card, number, size=20, color=accent, weight="bold").pack(anchor="w", padx=16)
        self._label(card, detail, size=8, color=COLORS["muted"]).pack(anchor="w", padx=16, pady=(4, 14))

    def _get_upcoming_events(self):
        today = date.today().isoformat()
        events = calendario_academico("any", fecha_inicio=today)
        if events and "error" in events[0]:
            raise ValueError(events[0]["error"])
        return sorted(events, key=lambda event: event["fecha_inicio"])

    def _event_row(self, parent, event):
        row = tk.Frame(parent, bg=COLORS["surface"])
        row.pack(fill="x", padx=14, pady=5)
        badge = self._label(
            row,
            event.get("fecha_inicio", "--"),
            size=9,
            color=COLORS["accent_light"],
            weight="bold",
        )
        badge.pack(side="left", padx=(7, 15), pady=8)
        details = tk.Frame(row, bg=COLORS["surface"])
        details.pack(side="left", fill="x", expand=True, pady=6)
        self._label(
            details,
            event.get("resumen") or "Evento académico",
            size=9,
            weight="bold",
        ).pack(anchor="w")
        self._label(
            details,
            event.get("categoria", "").replace("_", " ").title(),
            size=8,
            color=COLORS["muted"],
        ).pack(anchor="w", pady=(3, 0))

    def _show_calendar(self):
        self._label(
            self.content,
            "Organiza lo que viene",
            size=22,
            weight="bold",
            bg=COLORS["background"],
        ).pack(anchor="w")
        self._label(
            self.content,
            "Eventos del calendario académico disponibles para Aethera.",
            color=COLORS["muted"],
            bg=COLORS["background"],
        ).pack(anchor="w", pady=(5, 18))
        panel = self._card(self.content)
        panel.pack(fill="both", expand=True)
        try:
            events = self._get_upcoming_events()
            if not events:
                self._label(
                    panel,
                    "No hay eventos registrados a partir de hoy.",
                    color=COLORS["muted"],
                ).pack(anchor="w", padx=20, pady=20)
            else:
                for event in events:
                    self._event_row(panel, event)
        except (OSError, ValueError, KeyError, TypeError) as error:
            self._notice(panel, f"No se pudo cargar el calendario: {error}", COLORS["red"])

    def _show_workload(self):
        self._label(
            self.content,
            "Revisa la carga académica",
            size=22,
            weight="bold",
            bg=COLORS["background"],
        ).pack(anchor="w")
        self._label(
            self.content,
            "La detección utiliza la intensidad semanal registrada en el calendario.",
            color=COLORS["muted"],
            bg=COLORS["background"],
        ).pack(anchor="w", pady=(5, 18))
        panel = self._card(self.content)
        panel.pack(fill="both", expand=True)
        try:
            report = evaluar_riesgo_sobrecarga()
            if "error" in report:
                raise ValueError(report["error"])
            self._label(
                panel,
                f"{report['total_semanas_analizadas']} semanas analizadas",
                size=15,
                weight="bold",
            ).pack(anchor="w", padx=20, pady=(18, 8))
            self._label(
                panel,
                report["recomendacion"],
                color=COLORS["muted"],
                wraplength=900,
                justify="left",
            ).pack(anchor="w", padx=20, pady=(0, 16))
            for week in report["semanas_con_sobrecarga"]:
                risk_color = COLORS["red"] if week["nivel_riesgo"] == "ALTO" else COLORS["yellow"]
                card = self._card(panel, bg=COLORS["surface_light"])
                card.pack(fill="x", padx=18, pady=6)
                self._label(
                    card,
                    f"{week['semana']}  ·  Riesgo {week['nivel_riesgo']}  ·  "
                    f"Intensidad {week['intensidad_total']}",
                    size=10,
                    color=risk_color,
                    weight="bold",
                    bg=COLORS["surface_light"],
                ).pack(anchor="w", padx=14, pady=(12, 7))
                for event in week["eventos"]:
                    self._label(
                        card,
                        f"• {event['evento']} ({event['fecha_inicio']} – {event['fecha_fin']})",
                        size=9,
                        color=COLORS["muted"],
                        bg=COLORS["surface_light"],
                    ).pack(anchor="w", padx=14, pady=(0, 7))
        except (OSError, ValueError, KeyError, TypeError) as error:
            self._notice(panel, f"No se pudo analizar la carga académica: {error}", COLORS["red"])

    def _show_services(self):
        self._label(
            self.content,
            "Encuentra apoyo disponible",
            size=22,
            weight="bold",
            bg=COLORS["background"],
        ).pack(anchor="w")
        self._label(
            self.content,
            "Explora opciones institucionales según lo que necesites.",
            color=COLORS["muted"],
            bg=COLORS["background"],
        ).pack(anchor="w", pady=(5, 18))

        controls = self._card(self.content)
        controls.pack(fill="x", pady=(0, 14))
        self._label(
            controls,
            "Filtra las opciones para encontrar el apoyo adecuado",
            size=11,
            weight="bold",
        ).pack(anchor="w", padx=18, pady=(16, 12))
        filters = tk.Frame(controls, bg=COLORS["surface"])
        filters.pack(fill="x", padx=18, pady=(0, 16))

        category_filter = tk.Frame(filters, bg=COLORS["surface"])
        category_filter.pack(side="left", padx=(0, 12))
        self._label(category_filter, "TIPO DE APOYO", size=8, color=COLORS["muted"]).pack(
            anchor="w", pady=(0, 5)
        )
        self.category_var = tk.StringVar(value=next(iter(SERVICE_CATEGORIES)))
        self.category_selector = ttk.Combobox(
            category_filter,
            textvariable=self.category_var,
            values=tuple(SERVICE_CATEGORIES),
            state="readonly",
            style="Aethera.TCombobox",
            width=30,
        )
        self.category_selector.pack()

        district_filter = tk.Frame(filters, bg=COLORS["surface"])
        district_filter.pack(side="left", padx=(0, 12))
        self._label(district_filter, "DISTRITO", size=8, color=COLORS["muted"]).pack(
            anchor="w", pady=(0, 5)
        )
        self.district_var = tk.StringVar(value=next(iter(SERVICE_DISTRICTS)))
        self.district_selector = ttk.Combobox(
            district_filter,
            textvariable=self.district_var,
            values=tuple(SERVICE_DISTRICTS),
            state="readonly",
            style="Aethera.TCombobox",
            width=22,
        )
        self.district_selector.pack()

        search_filter = tk.Frame(filters, bg=COLORS["surface"])
        search_filter.pack(side="left", fill="x", expand=True)
        self._label(search_filter, "BUSCAR SERVICIO", size=8, color=COLORS["muted"]).pack(
            anchor="w", pady=(0, 5)
        )
        self.service_search_var = tk.StringVar()
        search_entry = tk.Entry(
            search_filter,
            textvariable=self.service_search_var,
            bg=COLORS["surface_light"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            font=(FONT, 9),
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
        )
        search_entry.pack(fill="x", ipady=9)

        self.category_selector.bind("<<ComboboxSelected>>", self._on_service_filter)
        self.district_selector.bind("<<ComboboxSelected>>", self._on_service_filter)
        self.service_search_var.trace_add("write", self._on_service_search)

        self.services_result = self._card(self.content)
        self.services_result.pack(fill="both", expand=True)
        results_header = tk.Frame(self.services_result, bg=COLORS["surface"])
        results_header.pack(fill="x", padx=16, pady=(12, 5))
        self._label(results_header, "Servicios disponibles", size=11, weight="bold").pack(
            side="left"
        )
        self.service_count = self._label(
            results_header,
            "",
            size=8,
            color=COLORS["accent_light"],
            bg=COLORS["surface_light"],
        )
        self.service_count.pack(side="right", padx=9, pady=3)
        self.services_canvas = tk.Canvas(
            self.services_result,
            bg=COLORS["surface"],
            highlightthickness=0,
            bd=0,
        )
        self.services_scrollbar = ttk.Scrollbar(
            self.services_result,
            orient="vertical",
            command=self.services_canvas.yview,
        )
        self.service_cards_container = tk.Frame(
            self.services_canvas,
            bg=COLORS["surface"],
        )
        self.service_cards_container.bind(
            "<Configure>",
            lambda _event: self.services_canvas.configure(
                scrollregion=self.services_canvas.bbox("all")
            ),
        )
        self.services_canvas.create_window(
            (0, 0),
            window=self.service_cards_container,
            anchor="nw",
            tags="service_cards",
        )
        self.services_canvas.configure(yscrollcommand=self.services_scrollbar.set)
        self.services_canvas.bind(
            "<Configure>",
            lambda event: self.services_canvas.itemconfigure(
                "service_cards",
                width=event.width,
            ),
        )
        self.services_canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 10))
        self.services_scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=(0, 10))
        self._load_services()

    def _on_service_filter(self, _event=None):
        self._load_services()

    def _on_service_search(self, *_args):
        if hasattr(self, "service_cards_container"):
            self._load_services()

    def _load_services(self):
        for child in self.service_cards_container.winfo_children():
            child.destroy()
        self.service_count.configure(text="Cargando…")
        category = SERVICE_CATEGORIES[self.category_var.get()]
        try:
            result = buscar_servicios_ayuda(category)
            if "error" in result:
                raise ValueError(result["error"])
            selected_district = SERVICE_DISTRICTS[self.district_var.get()]
            query = self.service_search_var.get().strip().casefold()
            services = [
                service
                for service in result["servicios"]
                if (
                    selected_district is None
                    or service["ubicacion"]["distrito_id"] == selected_district
                )
                and (
                    not query
                    or query
                    in " ".join(
                        (
                            service["nombre"],
                            service["tipo_servicio"],
                            service["ubicacion"]["distrito_id"],
                        )
                    ).casefold()
                )
            ]
            self.service_count.configure(
                text=f"{len(services)} {'opciones' if len(services) != 1 else 'opción'}"
            )
            if not services:
                self._show_empty_services()
                return
            for index, service in enumerate(services):
                self._service_card(service, index)
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.service_count.configure(text="Error")
            self._notice(
                self.service_cards_container,
                f"No se pudieron cargar los servicios de apoyo: {error}",
                COLORS["red"],
            )

    def _service_card(self, service, index):
        card = self._card(
            self.service_cards_container,
            bg=COLORS["surface_light"],
            radius=12,
        )
        card.grid(
            row=index // 2,
            column=index % 2,
            sticky="nsew",
            padx=(4, 7) if index % 2 == 0 else (7, 4),
            pady=7,
        )
        self.service_cards_container.grid_columnconfigure(0, weight=1, uniform="service")
        self.service_cards_container.grid_columnconfigure(1, weight=1, uniform="service")

        heading = tk.Frame(card, bg=COLORS["surface_light"])
        heading.pack(fill="x", padx=14, pady=(13, 8))
        icon = tk.Label(
            heading,
            text="♡",
            bg="#282650",
            fg=COLORS["accent_light"],
            font=(FONT, 15, "bold"),
            width=2,
            height=1,
        )
        icon.pack(side="left", padx=(0, 10), ipady=3)
        title_area = tk.Frame(heading, bg=COLORS["surface_light"])
        title_area.pack(side="left", fill="x", expand=True)
        self._label(
            title_area,
            service["nombre"],
            size=10,
            weight="bold",
            bg=COLORS["surface_light"],
            wraplength=330,
            justify="left",
        ).pack(anchor="w")
        service_type = SERVICE_TYPES.get(
            service["tipo_servicio"],
            service["tipo_servicio"].replace("_", " ").title(),
        )
        district = self._format_district(service["ubicacion"]["distrito_id"])
        self._label(
            title_area,
            f"{service_type}  ·  {district}",
            size=8,
            color=COLORS["muted"],
            bg=COLORS["surface_light"],
        ).pack(anchor="w", pady=(3, 0))

        self._service_detail(
            card,
            "HORARIO",
            self._format_schedule(service["horario_atencion"]),
        )
        channels = service["canales_atencion"]
        channel_names = [
            SERVICE_CHANNELS.get(channel, channel.replace("_", " ").title())
            for channel in channels
        ]
        self._service_detail(card, "CANALES DE ATENCIÓN", "  ·  ".join(channel_names))
        self._service_detail(
            card,
            "ORIENTACIÓN",
            self._format_referral(service["informacion_requerida_derivacion"]),
        )
        self._label(
            card,
            "Servicio demostrativo · Datos ficticios",
            size=8,
            color=COLORS["muted"],
            bg=COLORS["surface_light"],
        ).pack(anchor="w", padx=14, pady=(4, 12))

    def _service_detail(self, parent, label, value):
        detail = tk.Frame(parent, bg=COLORS["surface_light"])
        detail.pack(fill="x", padx=14, pady=4)
        self._label(
            detail,
            label,
            size=7,
            color=COLORS["accent_light"],
            weight="bold",
            bg=COLORS["surface_light"],
        ).pack(anchor="w")
        self._label(
            detail,
            value,
            size=9,
            color=COLORS["text"],
            bg=COLORS["surface_light"],
            wraplength=360,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

    def _format_district(self, district_id):
        name = district_id.removeprefix("DIST_").title()
        return f"Distrito {name}"

    def _format_schedule(self, schedule):
        day_range, _, hours = schedule.partition(" ")
        readable_days = WEEKDAYS.get(day_range, day_range)
        if not hours:
            return readable_days
        start, separator, end = hours.partition("-")
        if separator:
            return f"{readable_days}  ·  {start}–{end} h"
        return f"{readable_days}  ·  {hours}"

    def _format_referral(self, information):
        labels = {
            "student_id": "identificador del estudiante",
            "preferred channel": "canal de atención preferido",
            "non-clinical reason code": "motivo de orientación (no clínico)",
        }
        parts = [item.strip() for item in information.split(",")]
        return " · ".join(
            labels.get(part.casefold(), part.replace("_", " ").capitalize())
            for part in parts
        )

    def _show_empty_services(self):
        empty = tk.Frame(self.service_cards_container, bg=COLORS["surface"])
        empty.pack(fill="x", padx=8, pady=24)
        tk.Label(
            empty,
            text="⌕",
            bg=COLORS["surface"],
            fg=COLORS["accent_light"],
            font=(FONT, 28),
        ).pack()
        self._label(
            empty,
            "No encontramos servicios con estos filtros",
            size=11,
            weight="bold",
        ).pack(pady=(3, 5))
        self._label(
            empty,
            "Prueba con otro distrito o una búsqueda más amplia.",
            size=9,
            color=COLORS["muted"],
        ).pack()

    def _show_chat(self):
        intro = self._card(self.content)
        intro.pack(fill="x", pady=(0, 12))
        self._label(
            intro,
            "Un espacio para pensar tu siguiente paso",
            size=14,
            weight="bold",
        ).pack(anchor="w", padx=16, pady=(13, 3))
        self._label(
            intro,
            "Aethera te acompaña a organizarte; tú decides cómo avanzar.",
            color=COLORS["muted"],
        ).pack(anchor="w", padx=16, pady=(0, 13))

        transcript = self._card(self.content)
        transcript.pack(fill="both", expand=True)
        canvas = tk.Canvas(transcript, bg=COLORS["background"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(transcript, orient="vertical", command=canvas.yview)
        self.message_list = tk.Frame(canvas, bg=COLORS["background"])
        self.message_list.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas_window = canvas.create_window((0, 0), window=self.message_list, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(canvas_window, width=event.width),
        )
        canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=8)
        self.canvas = canvas

        for message in self.chat.historial:
            if message.get("role") in {"assistant", "user"} and message.get("content"):
                self._append_message(message["role"], message["content"])
        if not self.message_list.winfo_children():
            self._append_message(
                "assistant",
                "¡Hola! Soy Aethera. ¿Qué te gustaría organizar o conversar hoy?",
            )

        composer = self._card(self.content)
        composer.pack(fill="x", pady=(12, 0))
        self.message_input = tk.Text(
            composer,
            height=3,
            wrap="word",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            font=(FONT, 10),
            padx=12,
            pady=10,
        )
        self.message_input.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        self.message_input.bind("<Control-Return>", self._send_from_shortcut)
        send_button = self._button(composer, "Enviar  ↑", self._send_message, primary=True)
        send_button.pack(side="right", padx=10, pady=10)
        self.send_button = send_button
        if self.busy:
            self.send_button.configure(state="disabled")

    def _append_message(self, role, text):
        is_user = role == "user"
        outer = tk.Frame(self.message_list, bg=COLORS["background"])
        outer.pack(fill="x", padx=13, pady=7)
        bubble = tk.Frame(
            outer,
            bg=COLORS["accent"] if is_user else COLORS["surface"],
            highlightbackground=COLORS["accent"] if is_user else COLORS["border"],
            highlightthickness=1,
        )
        bubble.pack(side="right" if is_user else "left")
        tk.Label(
            bubble,
            text="Tú" if is_user else "Aethera",
            bg=COLORS["accent"] if is_user else COLORS["surface"],
            fg="white" if is_user else COLORS["accent_light"],
            font=(FONT, 8, "bold"),
        ).pack(anchor="w", padx=12, pady=(9, 2))
        tk.Label(
            bubble,
            text=text,
            bg=COLORS["accent"] if is_user else COLORS["surface"],
            fg="white" if is_user else COLORS["text"],
            font=(FONT, 10),
            justify="left",
            wraplength=max(340, self.root.winfo_width() - 440),
        ).pack(anchor="w", padx=12, pady=(0, 10))
        self.root.after_idle(lambda: self.canvas.yview_moveto(1))

    def _send_from_shortcut(self, _event):
        self._send_message()
        return "break"

    def _send_message(self):
        if self.busy:
            return
        text = self.message_input.get("1.0", "end").strip()
        if not text:
            return
        self.message_input.delete("1.0", "end")
        self._append_message("user", text)
        self.busy = True
        self.send_button.configure(state="disabled")
        self.status_label = self._label(
            self.content,
            "Aethera está pensando...",
            size=8,
            color=COLORS["accent_light"],
            bg=COLORS["background"],
        )
        self.status_label.pack(anchor="w", pady=(5, 0))
        worker = threading.Thread(
            target=self._run_chat_turn,
            args=(text,),
            daemon=True,
        )
        worker.start()

    def _run_chat_turn(self, text):
        try:
            self.chat.procesar_turno(
                text,
                al_emitir_texto=lambda chunk: self.event_queue.put(("token", chunk)),
                al_actualizar_estado=lambda status: self.event_queue.put(("status", status)),
            )
            self.event_queue.put(("complete", None))
        except Exception as error:
            self.event_queue.put(("error", str(error)))

    def _process_queue(self):
        try:
            while True:
                event, value = self.event_queue.get_nowait()
                if event == "token":
                    if self.current_page == "Asistente IA":
                        self._append_stream_chunk(value)
                elif event == "status":
                    self._set_status(value)
                elif event == "complete":
                    self._finish_chat_turn()
                elif event == "error":
                    self._append_message(
                        "assistant",
                        f"No pude completar la respuesta. Inténtalo de nuevo.\n\nDetalle: {value}",
                    )
                    self._finish_chat_turn()
        except queue.Empty:
            pass
        self.root.after(80, self._process_queue)

    def _append_stream_chunk(self, chunk):
        if not hasattr(self, "stream_bubble"):
            outer = tk.Frame(self.message_list, bg=COLORS["background"])
            outer.pack(fill="x", padx=13, pady=7)
            self.stream_bubble = tk.Frame(
                outer,
                bg=COLORS["surface"],
                highlightbackground=COLORS["border"],
                highlightthickness=1,
            )
            self.stream_bubble.pack(side="left")
            tk.Label(
                self.stream_bubble,
                text="Aethera",
                bg=COLORS["surface"],
                fg=COLORS["accent_light"],
                font=(FONT, 8, "bold"),
            ).pack(anchor="w", padx=12, pady=(9, 2))
            self.stream_text = tk.Label(
                self.stream_bubble,
                text="",
                bg=COLORS["surface"],
                fg=COLORS["text"],
                font=(FONT, 10),
                justify="left",
                wraplength=max(340, self.root.winfo_width() - 440),
            )
            self.stream_text.pack(anchor="w", padx=12, pady=(0, 10))
            self.stream_content = ""
        self.stream_content += chunk
        self.stream_text.configure(text=self.stream_content)
        self.root.after_idle(lambda: self.canvas.yview_moveto(1))

    def _set_status(self, status):
        if hasattr(self, "status_label") and self.status_label.winfo_exists():
            self.status_label.configure(text=status)

    def _finish_chat_turn(self):
        if hasattr(self, "status_label") and self.status_label.winfo_exists():
            self.status_label.destroy()
        self.busy = False
        if hasattr(self, "send_button") and self.send_button.winfo_exists():
            self.send_button.configure(state="normal")
        if hasattr(self, "stream_bubble"):
            del self.stream_bubble
            del self.stream_text
            del self.stream_content

    def _notice(self, parent, text, color):
        tk.Label(
            parent,
            text=text,
            bg=COLORS["surface"],
            fg=color,
            font=(FONT, 9),
            wraplength=900,
            justify="left",
        ).pack(anchor="w", padx=18, pady=16)

    def run(self):
        self.root.mainloop()


def iniciar_app_escritorio(motor, historial, herramientas, guardar_historial):
    AetheraDesktopApp(motor, historial, herramientas, guardar_historial).run()
