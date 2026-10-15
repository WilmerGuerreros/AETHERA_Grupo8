"""Orquestación de los componentes de la sección de chat."""

import tkinter as tk
from tkinter import ttk

from .components import ChatHeader, ChatHistory, ChatInput, ChatQuizView
from .logica import ChatLogic
from ..tema import COLORS, FONT


class ChatSection(ChatHeader, ChatHistory, ChatQuizView, ChatInput, ChatLogic):
    def _show_chat(self):
        layout = tk.Frame(self.page_content, bg=COLORS["background"])
        layout.pack(fill="both", expand=True)
        sidebar = tk.Frame(
            layout,
            bg=COLORS["surface"],
            width=226,
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        sidebar.pack(side="left", fill="y", padx=(0, 14))
        sidebar.pack_propagate(False)
        tk.Label(
            sidebar,
            text="Recientes",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=(FONT, 9, "bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(16, 10))
        self._button(
            sidebar,
            "＋ Nuevo chat",
            self._create_chat,
            primary=True,
        ).pack(fill="x", padx=10, pady=(0, 8))
        recent_frame = tk.Frame(sidebar, bg=COLORS["surface"])
        recent_frame.pack(fill="both", expand=True, padx=(5, 3), pady=(0, 8))
        self.chat_list_canvas = tk.Canvas(
            recent_frame,
            bg=COLORS["surface"],
            highlightthickness=0,
            bd=0,
        )
        self.chat_list_scrollbar = ttk.Scrollbar(
            recent_frame,
            orient="vertical",
            style="Aethera.Vertical.TScrollbar",
            command=lambda *args: self._scrollbar_command(
                self.chat_list_canvas,
                *args,
            ),
        )
        self.chat_list = tk.Frame(self.chat_list_canvas, bg=COLORS["surface"])
        self.chat_list.bind(
            "<Configure>",
            lambda _event: self.chat_list_canvas.configure(
                scrollregion=self.chat_list_canvas.bbox("all")
            ),
        )
        list_window = self.chat_list_canvas.create_window(
            (0, 0),
            window=self.chat_list,
            anchor="nw",
        )
        self.chat_list_canvas.configure(
            yscrollcommand=self.chat_list_scrollbar.set,
        )
        self.chat_list_canvas.bind(
            "<Configure>",
            lambda event: self.chat_list_canvas.itemconfigure(
                list_window,
                width=event.width,
            ),
        )
        self.chat_list_canvas.pack(side="left", fill="both", expand=True)
        self.chat_list_scrollbar.pack(side="right", fill="y")
        self._bind_smooth_scroll(self.chat_list_canvas, self.chat_list)
        self.chat_list_canvas.bind(
            "<Enter>",
            lambda _event: self.chat_list_canvas.focus_set(),
            add="+",
        )
        workspace = tk.Frame(layout, bg=COLORS["background"])
        workspace.pack(side="left", fill="both", expand=True)
        self.content = workspace
        self._render_chat_header()
        self._render_chat_history()
        self._render_chat_input()
        self._sync_chat_list()
        if self.chat_store.ocupado:
            # El turno siguió corriendo fuera de la página: retomamos el aviso.
            self._typing_phase = 0
            self._pulse_typing_indicator()
