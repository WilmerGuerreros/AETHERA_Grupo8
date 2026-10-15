"""Orquesta la ventana de escritorio y sus secciones."""

import math
import queue
import tempfile
import time
import tkinter as tk
from datetime import date, timedelta
from tkinter import font as tkfont
from tkinter import ttk

from core.chat_manager import ChatManager
from .estado.chat import ChatStore
from .estado.tareas import CORRIENDO, PENDIENTE, TaskManager
from .tema import COLORS, FONT
from .tk_env import configure_tk_environment
from .widgets import (
    RoundedButton,
    RoundedFrame,
    imagen_emoji_color,
    mezclar_color,
    texto_con_elipsis,
)

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
    def __init__(
        self,
        motor,
        historial,
        herramientas,
        guardar_interaccion,
        chat_manager=None,
    ):
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
        self._process_after_id = None
        self.tasks = TaskManager(
            emit=lambda evento, valor=None: self.event_queue.put((evento, valor))
        )
        self._tareas_estado = {}
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

        self._temporary_chat_storage = None
        if chat_manager is None:
            self._temporary_chat_storage = tempfile.TemporaryDirectory(
                prefix="aethera-test-chats-"
            )
            system_prompt = next(
                (
                    message.get("content", "")
                    for message in historial
                    if message.get("role") == "system"
                ),
                "",
            )
            chat_manager = ChatManager(
                motor,
                herramientas,
                system_prompt,
                root=self._temporary_chat_storage.name,
                initial_history=historial,
                initial_save_interaction=guardar_interaccion,
            )
        self.chat_manager = chat_manager
        self._chat_stores = {
            chat_id: ChatStore(session.history)
            for chat_id, session in self.chat_manager.sessions.items()
        }
        self._chat_attachments = {
            chat_id: []
            for chat_id in self.chat_manager.sessions
        }
        self._active_chat_id = next(iter(self.chat_manager.sessions))
        self._activate_chat(self._active_chat_id)

        self._configure_styles()
        self._build_shell()
        self.show_page("Inicio")
        self._process_after_id = self.root.after(80, self._process_queue)

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
        style.configure(
            "Aethera.Vertical.TScrollbar",
            background=COLORS["accent"],
            troughcolor=COLORS["surface_light"],
            bordercolor=COLORS["surface"],
            lightcolor=COLORS["accent_light"],
            darkcolor=COLORS["accent"],
            arrowcolor=COLORS["muted"],
            arrowsize=10,
            width=9,
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
            font=(FONT, 10, "bold"),
        ).pack(anchor="w", padx=24, pady=(0, 10))

        self.nav_buttons = {}
        self.nav_indicators = {}
        for page, icon in (
            ("Inicio", "\U0001F3E0"),
            ("Asistente IA", "\U0001F916"),
            ("Calendario", "\U0001F4C5"),
            ("Carga académica", "\U0001F4DA"),
            ("Servicios de apoyo", "\U0001F499"),
            ("Quiz", "\U0001F9E0"),
        ):
            row = tk.Frame(self.sidebar, bg=COLORS["sidebar"])
            row.pack(fill="x", padx=12, pady=2)
            indicator = tk.Frame(row, bg=COLORS["accent_light"])
            indicator.place(x=0, rely=0.5, anchor="w", width=3, height=0)
            button = RoundedButton(
                row,
                text=page,
                command=lambda selected=page: self.show_page(selected),
                icon=self._emoji_image(icon, size=25),
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
        self.task_indicator = tk.Label(
            self.header,
            text="",
            bg=COLORS["background"],
            fg=COLORS["accent_light"],
            font=(FONT, 9, "bold"),
        )
        self.task_indicator.pack(side="right", padx=(0, 6))
        tk.Label(
            self.header,
            text="●  GuIA",
            bg=COLORS["background"],
            fg=COLORS["green"],
            font=(FONT, 10, "bold"),
        ).pack(side="right", padx=30, pady=20)

        self.content = tk.Frame(self.main, bg=COLORS["background"])
        self.content.pack(fill="both", expand=True, padx=30, pady=24)
        self.page_content = self.content

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

    def _emoji_image(self, emoji, size=22):
        key = (emoji, size)
        if key not in self._emoji_images:
            self._emoji_images[key] = imagen_emoji_color(
                emoji,
                self.root,
                size=size,
            )
        return self._emoji_images[key]

    def _button(self, parent, text, command, primary=False, icon=None):
        return RoundedButton(
            parent,
            text,
            command,
            primary=primary,
            icon=self._emoji_image(icon) if icon else None,
        )

    def _animate_widget_color(self, widget, option, target, steps=20):
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
                    14,
                    lambda next_step=index + 1: step(next_step),
                )
            else:
                self._widget_color_animations.pop(key, None)

        step(1)

    def _bind_native_widget_animations(self, widget):
        if isinstance(widget, tk.Button):
            base_color = widget.cget("bg")
            hover_color = mezclar_color(base_color, COLORS["accent"], 0.5)
            widget.bind(
                "<Enter>",
                lambda _event: self._animate_widget_color(
                    widget, "bg", hover_color, steps=22
                ),
                add="+",
            )
            widget.bind(
                "<Leave>",
                lambda _event: self._animate_widget_color(
                    widget, "bg", base_color, steps=22
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
        if not canvas.winfo_exists():
            return
        key = str(canvas)
        animation = self._scroll_animations.get(key)
        if animation and abs(animation["target"] - target) < 0.001:
            return
        if animation and animation.get("after_id"):
            self.root.after_cancel(animation["after_id"])
        start = canvas.yview()[0] if animation is None else animation["current"]
        if abs(start - target) < 0.001:
            self._scroll_animations.pop(key, None)
            return
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
            for attribute in ("stream_bubble", "stream_text"):
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
        self.content = self.page_content
        for child in self.page_content.winfo_children():
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

    def _activate_chat(self, chat_id):
        session = self.chat_manager.sessions[chat_id]
        self._active_chat_id = chat_id
        self.chat = session.conversation
        self.chat_store = self._chat_stores[chat_id]
        self._attached_pdfs = self._chat_attachments.setdefault(chat_id, [])

    def _create_chat(self):
        if (
            self.current_page == "Asistente IA"
            and not self._flush_chat_quiz_progress_before_navigation()
        ):
            return
        self._discard_stream_widgets()
        self._cancel_chat_typing_indicator()
        session = self.chat_manager.create_session()
        self._chat_stores[session.chat_id] = ChatStore(session.history)
        self._chat_attachments[session.chat_id] = []
        self._activate_chat(session.chat_id)
        self._sync_chat_list()
        self.show_page("Asistente IA")

    def _sync_chat_list(self):
        if not hasattr(self, "chat_list") or not self.chat_list.winfo_exists():
            return
        for item in self.chat_list.winfo_children():
            item.destroy()
        sessions = list(reversed(self.chat_manager.sessions.values()))
        self._chat_ids = [session.chat_id for session in sessions]
        for session in sessions:
            chat_id = session.chat_id
            selected = chat_id == self._active_chat_id
            row = tk.Frame(
                self.chat_list,
                bg=COLORS["surface_light"] if selected else COLORS["surface"],
                height=44,
                cursor="hand2",
            )
            row.pack(fill="x", padx=6, pady=2)
            row.pack_propagate(False)
            indicator = tk.Label(
                row,
                text="●" if self._chat_stores[chat_id].ocupado else "",
                bg=row.cget("bg"),
                fg=COLORS["accent_light"],
                font=(FONT, 8, "bold"),
                width=2,
            )
            indicator.pack(side="left", padx=(5, 0))
            title_label = tk.Label(
                row,
                text=session.title,
                bg=row.cget("bg"),
                fg=COLORS["text"] if selected else COLORS["muted"],
                font=(FONT, 10, "bold" if selected else "normal"),
                anchor="w",
                padx=4,
                cursor="hand2",
            )
            title_label.pack(side="left", fill="both", expand=True, padx=(0, 8))
            title_label.bind(
                "<Configure>",
                lambda event, label=title_label, title=session.title:
                    self._fit_chat_title(label, title),
            )
            actions = tk.Button(
                row,
                text="⋯",
                command=lambda selected_id=chat_id:
                    self._show_chat_actions(selected_id),
                bg=row.cget("bg"),
                fg=COLORS["muted"],
                activebackground=COLORS["border"],
                activeforeground=COLORS["text"],
                relief="flat",
                bd=0,
                padx=7,
                font=(FONT, 15, "bold"),
                cursor="hand2",
            )
            actions.pack(side="right", padx=(0, 5))
            actions.bind(
                "<Enter>",
                lambda _event, button=actions:
                    self._animate_chat_action_button(button, True),
            )
            actions.bind(
                "<Leave>",
                lambda _event, button=actions, parent=row:
                    self._animate_chat_action_button(
                        button,
                        False,
                        parent.cget("bg"),
                    ),
            )
            for widget in (row, indicator, title_label):
                widget.bind(
                    "<Button-1>",
                    lambda _event, selected_id=chat_id: self._activate_from_list(
                        selected_id
                    ),
                )
            for widget in (row, indicator, title_label, actions):
                widget.bind(
                    "<Button-3>",
                    lambda event, selected_id=chat_id:
                        self._show_chat_actions(selected_id, event),
                )
            for widget in (row, title_label):
                widget.bind(
                    "<Enter>",
                    lambda _event, target=row, active=selected:
                        self._set_chat_row_hover(target, active, True),
                )
                widget.bind(
                    "<Leave>",
                    lambda _event, target=row, active=selected:
                        self._set_chat_row_hover(target, active, False),
                )
            self._animate_card_in(row)

    def _set_chat_row_hover(self, row, selected, hovered):
        color = (
            "#26365a"
            if selected or hovered
            else COLORS["surface"]
        )
        self._animate_widget_color(row, "bg", color, steps=22)
        for child in row.winfo_children():
            self._animate_widget_color(child, "bg", color, steps=22)
        title = next(
            (
                child
                for child in row.winfo_children()
                if isinstance(child, tk.Label) and child.cget("anchor") == "w"
            ),
            None,
        )
        if title is not None:
            self._animate_widget_color(
                title,
                "fg",
                COLORS["text"] if selected or hovered else COLORS["muted"],
                steps=22,
            )

    def _animate_chat_action_button(self, button, hovered, base=None):
        self._animate_widget_color(
            button,
            "fg",
            COLORS["accent_light"] if hovered else COLORS["muted"],
            steps=22,
        )
        self._animate_widget_color(
            button,
            "bg",
            "#35466f" if hovered else base or COLORS["surface"],
            steps=22,
        )

    def _fit_chat_title(self, label, title):
        width = label.winfo_width() - 10
        if width > 0:
            label.configure(
                text=texto_con_elipsis(
                    title,
                    tkfont.Font(font=label.cget("font")),
                    width,
                )
            )

    def _activate_from_list(self, chat_id):
        if chat_id == self._active_chat_id:
            return
        if (
            self.current_page == "Asistente IA"
            and not self._flush_chat_quiz_progress_before_navigation()
        ):
            return
        self._discard_stream_widgets()
        self._cancel_chat_typing_indicator()
        self._activate_chat(chat_id)
        self._sync_chat_list()
        if self.current_page == "Asistente IA":
            self.show_page("Asistente IA")

    def _show_chat_actions(self, chat_id, event=None):
        if chat_id not in self.chat_manager.sessions:
            return
        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.configure(bg=COLORS["surface"])
        popup.transient(self.root)
        panel = self._card(
            popup,
            bg=COLORS["surface"],
            border=COLORS["accent"],
            radius=14,
        )
        panel.pack(fill="both", expand=True, padx=1, pady=1)
        rename_button = tk.Button(
            panel,
            text="Renombrar",
            image=self._emoji_image("\U0000270F\ufe0f", size=22),
            compound="left",
            command=lambda: (
                popup.destroy(),
                self._rename_chat_dialog(chat_id),
            ),
            anchor="w",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            activebackground=COLORS["surface_light"],
            activeforeground=COLORS["accent_light"],
            relief="flat",
            bd=0,
            padx=14,
            pady=9,
            font=(FONT, 10),
            cursor="hand2",
        )
        rename_button.pack(fill="x", padx=4, pady=(4, 1))
        delete_button = tk.Button(
            panel,
            text="Eliminar chat",
            image=self._emoji_image("\U0001F5D1\ufe0f", size=22),
            compound="left",
            command=lambda: (
                popup.destroy(),
                self._delete_chat_dialog(chat_id),
            ),
            anchor="w",
            bg=COLORS["surface"],
            fg=COLORS["red"],
            activebackground="#3b1d2a",
            activeforeground="#ffabb3",
            relief="flat",
            bd=0,
            padx=14,
            pady=9,
            font=(FONT, 10),
            cursor="hand2",
        )
        delete_button.pack(fill="x", padx=4, pady=(1, 4))
        for button in (rename_button, delete_button):
            button.bind(
                "<Enter>",
                lambda _event, target=button:
                    self._animate_widget_color(
                        target,
                        "bg",
                        "#303c60"
                        if target is rename_button
                        else "#572331",
                        steps=24,
                    ),
            )
            button.bind(
                "<Leave>",
                lambda _event, target=button:
                    self._animate_widget_color(
                        target,
                        "bg",
                        COLORS["surface"],
                        steps=24,
                    ),
            )

        def close_if_outside(event):
            try:
                clicked_outside = event.widget.winfo_toplevel() is not popup
            except tk.TclError:
                clicked_outside = True
            if clicked_outside and popup.winfo_exists():
                close_popup()

        def close_popup():
            if popup.winfo_exists():
                popup.destroy()
            self.root.unbind_class("all", "<Button-1>", outside_click_binding)

        outside_click_binding = self.root.bind_class(
            "all",
            "<Button-1>",
            close_if_outside,
            add="+",
        )
        popup.bind("<Escape>", lambda _event: close_popup())
        popup.bind(
            "<Destroy>",
            lambda _event: self.root.unbind_class(
                "all",
                "<Button-1>",
                outside_click_binding,
            ),
            add="+",
        )
        popup.update_idletasks()
        width = popup.winfo_reqwidth()
        height = popup.winfo_reqheight()
        if event is not None:
            pointer_x, pointer_y = event.x_root, event.y_root
        else:
            pointer_x, pointer_y = self.root.winfo_pointerxy()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x, y = self._chat_actions_position(
            pointer_x,
            pointer_y,
            width,
            height,
            screen_width,
            screen_height,
        )
        popup.geometry(f"{width}x{height}+{x}+{y}")
        popup.deiconify()
        popup.lift()
        popup.focus_force()
        self._animate_card_in(panel)

    @staticmethod
    def _chat_actions_position(
        pointer_x,
        pointer_y,
        width,
        height,
        screen_width,
        screen_height,
    ):
        x = max(0, min(pointer_x - width, screen_width - width))
        y = pointer_y + 6
        if y + height > screen_height:
            y = pointer_y - height - 6
        y = max(0, min(y, screen_height - height))
        return x, y

    def _rename_chat_dialog(self, chat_id):
        session = self.chat_manager.sessions.get(chat_id)
        if session is None:
            return
        dialog, panel = self._create_chat_dialog("Renombrar conversación", "#6558f5")
        tk.Label(
            panel,
            text="Nombre de la conversación",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=(FONT, 11, "bold"),
        ).pack(anchor="w", padx=20, pady=(20, 8))
        entry = tk.Entry(
            panel,
            bg=COLORS["surface_light"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            font=(FONT, 11),
        )
        entry.pack(fill="x", padx=20, pady=(0, 16), ipady=8)
        entry.insert(0, session.title)
        self._bind_native_widget_animations(entry)
        error_label = tk.Label(
            panel,
            text="",
            bg=COLORS["surface"],
            fg=COLORS["red"],
            font=(FONT, 9),
        )
        error_label.pack(fill="x", padx=20)

        def save():
            title = entry.get().strip()
            if not title:
                error_label.configure(text="Escribe un nombre para continuar.")
                return
            try:
                self.chat_manager.rename_session(chat_id, title)
            except (OSError, ValueError) as error:
                error_label.configure(text=f"No se pudo renombrar: {error}")
                return
            self._sync_chat_list()
            dialog.destroy()

        buttons = tk.Frame(panel, bg=COLORS["surface"])
        buttons.pack(fill="x", padx=16, pady=16)
        self._button(buttons, "Cancelar", dialog.destroy).pack(side="right", padx=(8, 0))
        self._button(buttons, "Guardar", save, primary=True).pack(side="right")
        entry.bind("<Return>", lambda _event: save())
        entry.focus_set()
        entry.selection_range(0, "end")
        dialog.grab_set()
        self._animate_card_in(panel)

    def _delete_chat_dialog(self, chat_id):
        session = self.chat_manager.sessions.get(chat_id)
        if session is None:
            return
        if self._chat_stores[chat_id].ocupado:
            self._show_chat_notice(
                "No se puede eliminar una conversación mientras está respondiendo."
            )
            return
        if any(
            document["state"] == "loading"
            for document in self._chat_attachments.get(chat_id, [])
        ):
            self._show_chat_notice(
                "Espera a que termine el procesamiento de los PDF antes de eliminar el chat."
            )
            return
        dialog, panel = self._create_chat_dialog("Eliminar conversación", COLORS["red"])
        tk.Label(
            panel,
            text="¿Eliminar esta conversación?",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=(FONT, 12, "bold"),
        ).pack(anchor="w", padx=20, pady=(20, 8))
        question = tk.Label(
            panel,
            text="¿Eliminar también la carpeta de memoria del chat?",
            bg="#3b1d2a",
            fg="#ffabb3",
            font=(FONT, 10, "bold"),
            wraplength=390,
            justify="left",
            padx=12,
            pady=12,
            highlightbackground=COLORS["red"],
            highlightthickness=1,
        )
        question.pack(fill="x", padx=20, pady=(0, 12))
        tk.Label(
            panel,
            text="Si eliges No, la memoria se conservará en CHATS ARCHIVADOS.",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=(FONT, 9),
            wraplength=390,
            justify="left",
        ).pack(fill="x", padx=20, pady=(0, 12))
        buttons = tk.Frame(panel, bg=COLORS["surface"])
        buttons.pack(fill="x", padx=14, pady=(0, 16))

        def confirm(keep_memory):
            try:
                self.chat_manager.delete_session(chat_id, keep_memory)
            except (OSError, ValueError, KeyError) as error:
                self._show_chat_notice(f"No se pudo eliminar el chat: {error}")
                return
            dialog.destroy()
            self._chat_stores.pop(chat_id, None)
            self._chat_attachments.pop(chat_id, None)
            if not self.chat_manager.sessions:
                new_session = self.chat_manager.create_session()
                self._chat_stores[new_session.chat_id] = ChatStore(new_session.history)
                self._chat_attachments[new_session.chat_id] = []
            if self._active_chat_id == chat_id:
                next_id = next(reversed(self.chat_manager.sessions))
                self._activate_chat(next_id)
            self._sync_chat_list()
            if self.current_page == "Asistente IA":
                self.show_page("Asistente IA")

        self._button(
            buttons,
            "Retroceder",
            dialog.destroy,
        ).pack(side="right", padx=(6, 0))
        self._button(
            buttons,
            "No, conservar",
            lambda: confirm(True),
        ).pack(side="right", padx=6)
        self._button(
            buttons,
            "Sí, eliminar",
            lambda: confirm(False),
            primary=True,
        ).pack(side="right", padx=6)
        dialog.grab_set()
        self._animate_card_in(panel)

    def _create_chat_dialog(self, title, accent):
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.configure(bg=COLORS["background"])
        dialog.resizable(False, False)
        width, height = 520, 310
        x = self.root.winfo_rootx() + (self.root.winfo_width() - width) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - height) // 2
        dialog.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")
        panel = self._card(
            dialog,
            bg=COLORS["surface"],
            border=accent,
            radius=22,
        )
        panel.pack(fill="both", expand=True, padx=2, pady=2)
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        return dialog, panel

    def _show_chat_notice(self, message):
        dialog, panel = self._create_chat_dialog("Aethera", COLORS["yellow"])
        tk.Label(
            panel,
            text=message,
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=(FONT, 10),
            wraplength=420,
            justify="left",
        ).pack(fill="x", padx=20, pady=20)
        self._button(panel, "Entendido", dialog.destroy, primary=True).pack(
            side="right",
            padx=16,
            pady=12,
        )
        dialog.grab_set()
        self._animate_card_in(panel)

    def _scrollbar_command(self, canvas, *arguments):
        if not canvas.winfo_exists() or not arguments:
            return
        current = canvas.yview()[0]
        if arguments[0] == "moveto":
            target = float(arguments[1])
        elif arguments[0] == "scroll":
            count = int(arguments[1])
            increment = 0.72 if arguments[2] == "pages" else 0.055
            target = current + count * increment
        else:
            canvas.yview(*arguments)
            return
        self._animate_scroll(canvas, min(1.0, max(0.0, target)), duration=130)

    def _cancel_chat_typing_indicator(self):
        after_id = getattr(self, "_typing_after_id", None)
        if after_id:
            try:
                self.root.after_cancel(after_id)
            except tk.TclError:
                pass
            self._typing_after_id = None

    def _discard_stream_widgets(self):
        for attribute in ("stream_bubble", "stream_text"):
            if hasattr(self, attribute):
                delattr(self, attribute)

    def _animate_nav_selection(self, selected_page):
        duration = 0.28
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
                    width=4,
                    height=round(34 * indicator_progress),
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
        self._scroll_targets = [
            (existing_canvas, existing_child)
            for existing_canvas, existing_child in self._scroll_targets
            if existing_canvas.winfo_exists() and existing_child.winfo_exists()
        ]
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

    def _handle_tarea_actualizada(self, snapshot):
        """Refleja el estado de las tareas de fondo en el encabezado."""
        self._tareas_estado[snapshot["id"]] = snapshot
        self._sync_task_indicator()

    def _sync_task_indicator(self):
        if (
            not hasattr(self, "task_indicator")
            or not self.task_indicator.winfo_exists()
        ):
            return
        activas = [
            tarea
            for tarea in self._tareas_estado.values()
            if tarea["estado"] in (PENDIENTE, CORRIENDO)
        ]
        if not activas:
            self.task_indicator.configure(text="")
            return
        texto = activas[0]["mensaje"] or f"{len(activas)} en curso"
        self.task_indicator.configure(
            text=f"⋯  {texto}",
            fg=COLORS["accent_light"],
        )

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

    def _cancelar_pendientes(self):
        """Cancela callbacks recurrentes para cerrar sin errores de Tk."""
        for nombre in (
            "_process_after_id",
            "_typing_after_id",
            "_search_after_id",
            "_service_render_after_id",
            "_calendar_pulse_after_id",
        ):
            after_id = getattr(self, nombre, None)
            if after_id:
                try:
                    self.root.after_cancel(after_id)
                except tk.TclError:
                    pass
                setattr(self, nombre, None)
        for after_id in list(getattr(self, "_nav_animation_ids", {}).values()):
            try:
                self.root.after_cancel(after_id)
            except tk.TclError:
                pass
        for animation in self._scroll_animations.values():
            after_id = animation.get("after_id")
            if after_id:
                try:
                    self.root.after_cancel(after_id)
                except tk.TclError:
                    pass
        self._scroll_animations.clear()

    def cerrar(self):
        self._cancelar_pendientes()
        try:
            # Evita que Tcl reporte callbacks pendientes contra una ventana
            # que ya se está destruyendo.
            self.root.tk.eval("proc bgerror {msg} {}")
        except tk.TclError:
            pass
        self.root.destroy()
        if self._temporary_chat_storage is not None:
            self._temporary_chat_storage.cleanup()

    def run(self):
        self.root.mainloop()


def iniciar_app_escritorio(
    motor,
    historial,
    herramientas,
    guardar_interaccion,
    chat_manager=None,
):
    AetheraDesktopApp(
        motor,
        historial,
        herramientas,
        guardar_interaccion,
        chat_manager=chat_manager,
    ).run()
