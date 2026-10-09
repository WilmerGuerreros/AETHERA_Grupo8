"""Interfaz de escritorio para Aethera, construida con Tkinter."""

import queue
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
        return tk.Frame(
            parent,
            bg=kwargs.pop("bg", COLORS["surface"]),
            highlightbackground=COLORS["border"],
            highlightthickness=1,
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
        return tk.Button(
            parent,
            text=text,
            command=command,
            relief="flat",
            bd=0,
            padx=16,
            pady=10,
            bg=COLORS["accent"] if primary else COLORS["surface_light"],
            fg="white" if primary else COLORS["text"],
            activebackground=COLORS["accent_light"],
            activeforeground="white",
            font=(FONT, 9, "bold"),
            cursor="hand2",
        )

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
        self._label(controls, "¿Qué tipo de orientación buscas?", weight="bold").pack(
            anchor="w", padx=18, pady=(16, 7)
        )
        self.category_var = tk.StringVar(value=next(iter(SERVICE_CATEGORIES)))
        selector = ttk.Combobox(
            controls,
            textvariable=self.category_var,
            values=tuple(SERVICE_CATEGORIES),
            state="readonly",
            style="Aethera.TCombobox",
            width=34,
        )
        selector.pack(side="left", padx=18, pady=(0, 16))
        self._button(controls, "Buscar opciones", self._load_services, primary=True).pack(
            side="left", pady=(0, 16)
        )

        self.services_result = self._card(self.content)
        self.services_result.pack(fill="both", expand=True)
        self._label(
            self.services_result,
            "Selecciona una categoría para ver los servicios asociados.",
            color=COLORS["muted"],
        ).pack(anchor="w", padx=18, pady=18)

    def _load_services(self):
        for child in self.services_result.winfo_children():
            child.destroy()
        category = SERVICE_CATEGORIES[self.category_var.get()]
        try:
            result = buscar_servicios_ayuda(category)
            if "error" in result:
                raise ValueError(result["error"])
            services = result["servicios"]
            if not services:
                self._notice(self.services_result, "No se encontraron servicios.", COLORS["yellow"])
                return
            for service in services:
                card = self._card(self.services_result, bg=COLORS["surface_light"])
                card.pack(fill="x", padx=14, pady=7)
                self._label(
                    card,
                    service["nombre"],
                    size=11,
                    weight="bold",
                    bg=COLORS["surface_light"],
                ).pack(anchor="w", padx=14, pady=(12, 5))
                details = (
                    f"{service['tipo_servicio']}  ·  Distrito {service['ubicacion']['distrito_id']}\n"
                    f"Atención: {service['horario_atencion']}\n"
                    f"Canales: {service['canales_atencion']}"
                )
                self._label(
                    card,
                    details,
                    size=9,
                    color=COLORS["muted"],
                    bg=COLORS["surface_light"],
                    justify="left",
                    wraplength=940,
                ).pack(anchor="w", padx=14, pady=(0, 12))
        except (OSError, ValueError, KeyError, TypeError) as error:
            self._notice(
                self.services_result,
                f"No se pudieron cargar los servicios de apoyo: {error}",
                COLORS["red"],
            )

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
