"""Orquesta la ventana de escritorio y sus secciones."""

import math
import queue
import time
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk

from core.conversation import Conversacion
from data.app_paths import configure_tk_environment
from .tema import COLORS, FONT
from .widgets import RoundedButton, RoundedFrame, mezclar_color

from .dashboard import DashboardSection
from .calendario import CalendarSection
from .carga_academica import WorkloadSection
from .servicios import ServicesSection
from .chat import ChatSection
from .quiz import QuizSection


class AetheraDesktopApp(
    DashboardSection,
    CalendarSection,
    WorkloadSection,
    ServicesSection,
    ChatSection,
    QuizSection,
):
    def __init__(self, motor, historial, herramientas, guardar_interaccion):
        configure_tk_environment()
        self.root = tk.Tk()
        self.root.title("GuIA | Acompañamiento académico")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = min(1560, max(1, screen_width - 32))
        window_height = min(980, max(1, screen_height - 80))
        self.root.geometry(
            f"{window_width}x{window_height}"
            f"+{max(0, (screen_width - window_width) // 2)}"
            f"+{max(0, (screen_height - window_height) // 2)}"
        )
        self.root.minsize(min(1024, window_width), min(640, window_height))
        self.root.configure(bg=COLORS["background"])
        self._fullscreen = False
        self.root.bind("<F11>", self._toggle_fullscreen)
        self.root.bind("<Escape>", self._exit_fullscreen)
        self.event_queue = queue.Queue()
        self._emoji_images = {}
        self._emoji_font = None
        self._scroll_animations = {}
        self._search_after_id = None
        self._services_request_id = 0
        self._service_render_after_id = None
        self._service_render_index = 0
        self._service_render_services = []
        self._pdf_request_id = 0
        self._attached_pdfs = []
        self._pdf_status_text = "Sin documento adjunto"
        self._pdf_status_color = COLORS["muted"]
        self._widget_color_animations = {}
        self._scroll_targets = []
        self.calendar_week_start = date.today() - timedelta(days=date.today().weekday())
        self.calendar_category_var = None
        self._calendar_animation_ids = []
        self._calendar_pulse_after_id = None
        self._calendar_pulse_phase = 0
        self._nav_animation_ids = {}
        self._nav_animation_tokens = {}
        self._nav_indicator_progress = {}
        self.root.bind_all("<MouseWheel>", self._handle_mousewheel)
        self.current_page = "Inicio"
        self.busy = False

        self.chat = Conversacion(
            motor,
            historial,
            herramientas,
            guardar_interaccion=guardar_interaccion,
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
            padding=12,
        )
        style.map(
            "Aethera.TCombobox",
            fieldbackground=[("readonly", COLORS["surface_light"])],
            foreground=[("readonly", COLORS["text"])],
        )

    def _build_shell(self):
        self.sidebar = tk.Frame(self.root, bg=COLORS["sidebar"], width=276)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand = tk.Frame(self.sidebar, bg=COLORS["sidebar"])
        brand.pack(fill="x", padx=22, pady=(25, 30))
        tk.Label(
            brand,
            text="✦",
            bg=COLORS["accent"],
            fg="white",
            font=(FONT, 21, "bold"),
            width=2,
            height=1,
        ).pack(side="left", padx=(0, 11), ipady=5)
        title = tk.Frame(brand, bg=COLORS["sidebar"])
        title.pack(side="left")
        tk.Label(
            title,
            text="GuIA",
            bg=COLORS["sidebar"],
            fg=COLORS["text"],
            font=(FONT, 16, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title,
            text="Tu espacio académico",
            bg=COLORS["sidebar"],
            fg=COLORS["muted"],
            font=(FONT, 10),
        ).pack(anchor="w", pady=(2, 0))

        tk.Label(
            self.sidebar,
            text="MENÚ PRINCIPAL",
            bg=COLORS["sidebar"],
            fg="#7381a4",
            font=(FONT, 9, "bold"),
        ).pack(anchor="w", padx=24, pady=(0, 10))

        self.nav_buttons = {}
        self.nav_indicators = {}
        for page, icon in (
            ("Inicio", "⌂"),
            ("Asistente IA", "✧"),
            ("Calendario", "▦"),
            ("Carga académica", "▤"),
            ("Servicios de apoyo", "♡"),
            ("Quiz", "⚗"),
        ):
            row = tk.Frame(self.sidebar, bg=COLORS["sidebar"])
            row.pack(fill="x", padx=12, pady=2)
            indicator = tk.Frame(row, bg=COLORS["accent_light"])
            indicator.place(x=0, rely=0.5, anchor="w", width=3, height=0)
            button = RoundedButton(
                row,
                text=f"{icon}    {page}",
                command=lambda selected=page: self.show_page(selected),
            )
            button.pack(side="left", fill="x", expand=True, padx=(10, 0))
            self.nav_buttons[page] = button
            self.nav_indicators[page] = indicator
            self._nav_indicator_progress[page] = 0.0

        spacer = tk.Frame(self.sidebar, bg=COLORS["sidebar"])
        spacer.pack(fill="both", expand=True)
        wellbeing = self._card(
            self.sidebar,
            bg=COLORS["surface"],
            radius=22,
        )
        wellbeing.pack(fill="x", padx=16, pady=(0, 18))
        self._label(
            wellbeing,
            text="Un paso a la vez",
            size=11,
            weight="bold",
        ).pack(anchor="w", padx=16, pady=(14, 5))
        self._label(
            wellbeing,
            text="Organizarte también es cuidarte.",
            size=9,
            color=COLORS["muted"],
            wraplength=185,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 15))

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
            font=(FONT, 19, "bold"),
        )
        self.page_title.pack(side="left", padx=30, pady=20)
        tk.Label(
            self.header,
            text="Acompañamiento académico personalizado",
            bg=COLORS["background"],
            fg=COLORS["muted"],
            font=(FONT, 10),
        ).pack(side="left", padx=(4, 0), pady=20)
        fullscreen_button = tk.Button(
            self.header,
            text="Pantalla completa (F11)",
            command=self._toggle_fullscreen,
            relief="flat",
            bd=0,
            padx=10,
            pady=7,
            bg=COLORS["surface_light"],
            fg=COLORS["text"],
            activebackground=COLORS["border"],
            activeforeground=COLORS["text"],
            font=(FONT, 9),
            cursor="hand2",
        )
        self._bind_native_widget_animations(fullscreen_button)
        fullscreen_button.pack(side="right", padx=(8, 18), pady=12)
        tk.Label(
            self.header,
            text="●  GuIA",
            bg=COLORS["background"],
            fg=COLORS["green"],
            font=(FONT, 10, "bold"),
        ).pack(side="right", padx=30, pady=20)

        self.content = tk.Frame(self.main, bg=COLORS["background"])
        self.content.pack(fill="both", expand=True, padx=30, pady=24)

    def _toggle_fullscreen(self, _event=None):
        self._fullscreen = not self._fullscreen
        self.root.attributes("-fullscreen", self._fullscreen)
        return "break"

    def _exit_fullscreen(self, _event=None):
        if self._fullscreen:
            self._fullscreen = False
            self.root.attributes("-fullscreen", False)
            return "break"

    def _card(self, parent, **kwargs):
        return RoundedFrame(
            parent,
            bg=kwargs.pop("bg", COLORS["surface"]),
            border=kwargs.pop("border", COLORS["border"]),
            radius=kwargs.pop("radius", 20),
            gradient=kwargs.pop("gradient", None),
            **kwargs,
        )

    def _label(self, parent, text, size=10, color=None, weight="normal", **kwargs):
        return tk.Label(
            parent,
            text=text,
            bg=kwargs.pop("bg", COLORS["surface"]),
            fg=color or COLORS["text"],
            font=(FONT, max(8, round(size * 1.16)), weight),
            **kwargs,
        )

    def _button(self, parent, text, command, primary=False):
        return RoundedButton(parent, text, command, primary=primary)

    def _animate_widget_color(self, widget, option, target, steps=12):
        key = (widget, option)
        after_id = self._widget_color_animations.pop(key, None)
        if after_id:
            self.root.after_cancel(after_id)
        try:
            start = widget.cget(option)
        except tk.TclError:
            return
        if not isinstance(start, str) or not start.startswith("#"):
            return

        def step(index):
            try:
                if not widget.winfo_exists():
                    self._widget_color_animations.pop(key, None)
                    return
                progress = min(1.0, index / steps)
                eased = 1 - (1 - progress) ** 3
                widget.configure(**{option: mezclar_color(start, target, eased)})
            except tk.TclError:
                self._widget_color_animations.pop(key, None)
                return
            if progress < 1:
                self._widget_color_animations[key] = self.root.after(
                    16,
                    lambda next_step=index + 1: step(next_step),
                )
            else:
                self._widget_color_animations.pop(key, None)

        step(1)

    def _bind_native_widget_animations(self, widget):
        if isinstance(widget, tk.Button):
            base_color = widget.cget("bg")
            hover_color = mezclar_color(base_color, COLORS["accent"], 0.32)
            widget.bind(
                "<Enter>",
                lambda _event: self._animate_widget_color(
                    widget, "bg", hover_color
                ),
                add="+",
            )
            widget.bind(
                "<Leave>",
                lambda _event: self._animate_widget_color(
                    widget, "bg", base_color
                ),
                add="+",
            )
        elif isinstance(widget, (tk.Entry, tk.Text)):
            widget.configure(
                highlightthickness=1,
                highlightbackground=COLORS["border"],
                highlightcolor=COLORS["border"],
            )
            widget.bind(
                "<FocusIn>",
                lambda _event: self._animate_widget_color(
                    widget, "highlightbackground", COLORS["accent_light"]
                ),
                add="+",
            )
            widget.bind(
                "<FocusIn>",
                lambda _event: self._animate_widget_color(
                    widget, "highlightcolor", COLORS["accent_light"]
                ),
                add="+",
            )
            widget.bind(
                "<FocusOut>",
                lambda _event: self._animate_widget_color(
                    widget, "highlightbackground", COLORS["border"]
                ),
                add="+",
            )
            widget.bind(
                "<FocusOut>",
                lambda _event: self._animate_widget_color(
                    widget, "highlightcolor", COLORS["border"]
                ),
                add="+",
            )

    def _animate_scroll_to_bottom(self, canvas):
        self._animate_scroll(canvas, 1.0, duration=270)

    def _animate_scroll(self, canvas, target, duration=280):
        key = str(canvas)
        animation = self._scroll_animations.get(key)
        if animation and abs(animation["target"] - target) < 0.001:
            return
        if animation and animation.get("after_id"):
            self.root.after_cancel(animation["after_id"])
        start = canvas.yview()[0] if animation is None else animation["current"]
        self._scroll_animations[key] = {
            "start": start,
            "target": target,
            "started": time.monotonic(),
            "duration": duration / 1000,
            "current": start,
            "after_id": None,
        }
        self._step_scroll(canvas, key)

    def _step_scroll(self, canvas, key):
        animation = self._scroll_animations.get(key)
        if animation is None or not canvas.winfo_exists():
            self._scroll_animations.pop(key, None)
            return
        elapsed = time.monotonic() - animation["started"]
        progress = min(1.0, elapsed / animation["duration"])
        eased = (1 - math.cos(math.pi * progress)) / 2
        current = animation["start"] + (
            animation["target"] - animation["start"]
        ) * eased
        animation["current"] = current
        canvas.yview_moveto(current)
        if progress < 1:
            animation["after_id"] = self.root.after(
                12,
                lambda: self._step_scroll(canvas, key),
            )
        else:
            self._scroll_animations.pop(key, None)

    def _on_mousewheel(self, canvas, event):
        delta = -1 if event.delta > 0 else 1
        current = canvas.yview()[0]
        target = min(1.0, max(0.0, current + delta * 0.12))
        self._animate_scroll(canvas, target, duration=225)
        return "break"

    def _handle_mousewheel(self, event):
        widget = event.widget
        for canvas, scrollable in reversed(self._scroll_targets):
            current = widget
            while current is not None:
                if current == scrollable or current == canvas:
                    return self._on_mousewheel(canvas, event)
                current = getattr(current, "master", None)

    def show_page(self, page):
        if (
            self.current_page == "Asistente IA"
            and page != "Asistente IA"
            and not self._flush_chat_quiz_progress_before_navigation()
        ):
            return
        if self.current_page == "Asistente IA" and page != "Asistente IA":
            for attribute in ("stream_bubble", "stream_text", "stream_content"):
                if hasattr(self, attribute):
                    delattr(self, attribute)
        if self.current_page == "Servicios de apoyo" and page != "Servicios de apoyo":
            if self._search_after_id:
                self.root.after_cancel(self._search_after_id)
                self._search_after_id = None
            self._cancel_service_render()
            self._services_request_id += 1
        self.current_page = page
        self.page_title.configure(text=page)
        self._animate_nav_selection(page)
        for child in self.content.winfo_children():
            child.destroy()

        if page == "Inicio":
            self._show_dashboard()
        elif page == "Asistente IA":
            self._show_chat()
            self.message_input.focus_set()
        elif page == "Calendario":
            self._show_calendar()
        elif page == "Carga académica":
            self._show_workload()
        elif page == "Servicios de apoyo":
            self._show_services()
        elif page == "Quiz":
            self._show_quiz()

    def _animate_nav_selection(self, selected_page):
        duration = 0.18
        started = time.monotonic()
        for page, button in self.nav_buttons.items():
            after_id = self._nav_animation_ids.pop(page, None)
            if after_id:
                self.root.after_cancel(after_id)
            token = self._nav_animation_tokens.get(page, 0) + 1
            self._nav_animation_tokens[page] = token
            selected = page == selected_page
            start_progress = self._nav_indicator_progress[page]
            target_progress = 1.0 if selected else 0.0
            button.set_selected(selected)

            def step(
                nav_page=page,
                indicator=self.nav_indicators[page],
                from_progress=start_progress,
                to_progress=target_progress,
                animation_token=token,
                callback=None,
            ):
                if callback is None:
                    callback = step
                if self._nav_animation_tokens.get(nav_page) != animation_token:
                    return
                if not indicator.winfo_exists():
                    self._nav_animation_ids.pop(nav_page, None)
                    return
                progress = min(1.0, (time.monotonic() - started) / duration)
                eased = 1 - (1 - progress) ** 3
                indicator_progress = from_progress + (
                    to_progress - from_progress
                ) * eased
                self._nav_indicator_progress[nav_page] = indicator_progress
                indicator.place(
                    x=0,
                    rely=0.5,
                    anchor="w",
                    width=3,
                    height=round(30 * indicator_progress),
                )
                if progress < 1:
                    self._nav_animation_ids[nav_page] = self.root.after(
                        16,
                        lambda next_step=callback: next_step(
                            callback=next_step
                        ),
                    )
                else:
                    self._nav_animation_ids.pop(nav_page, None)

            step()

    def _bind_smooth_scroll(self, canvas, child):
        self._scroll_targets.append((canvas, child))

    def _animate_card_in(self, widget, grid=False):
        try:
            info = widget.grid_info() if grid else widget.pack_info()
        except tk.TclError:
            return
        padding = info.get("pady", 0)
        if isinstance(padding, tuple):
            final_top, final_bottom = (int(value) for value in padding)
        else:
            final_top = final_bottom = int(padding)
        steps = 15
        widget.configure(highlightthickness=0)
        rounded = next(
            (
                child
                for child in widget.winfo_children()
                if isinstance(child, RoundedFrame)
            ),
            widget if isinstance(widget, RoundedFrame) else None,
        )
        original_border = rounded.border if rounded else None
        parent_bg = widget.master.cget("bg")

        def step(index):
            if not widget.winfo_exists():
                return
            progress = min(1.0, index / steps)
            eased = (1 - math.cos(math.pi * progress)) / 2
            top = round(final_top * eased)
            bottom = round(final_bottom * eased)
            if grid:
                widget.grid_configure(pady=(top, bottom))
            else:
                widget.pack_configure(pady=(top, bottom))
            if rounded:
                rounded.border = mezclar_color(
                    parent_bg,
                    original_border,
                    eased,
                )
                rounded._draw()
            if index < steps:
                self.root.after(16, lambda: step(index + 1))

        self.root.after(0, lambda: step(1))

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


def iniciar_app_escritorio(motor, historial, herramientas, guardar_interaccion):
    AetheraDesktopApp(motor, historial, herramientas, guardar_interaccion).run()
