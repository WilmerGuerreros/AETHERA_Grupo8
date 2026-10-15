"""Título, subtítulo e estado del chat."""

import tkinter as tk
from tkinter import font as tkfont

from ...tema import COLORS, FONT
from ...widgets import texto_con_elipsis


class ChatHeader:
    def _render_chat_header(self):
        intro = self._card(self.content)
        intro.pack(fill="x", pady=(0, 12))
        title_area = tk.Frame(intro, bg=COLORS["surface"])
        title_area.pack(side="left", fill="x", expand=True)
        heading = self._label(
            title_area,
            "Un espacio para pensar tu siguiente paso",
            size=14,
            weight="bold",
        )
        heading.pack(fill="x", padx=16, pady=(13, 3))
        heading.bind(
            "<Configure>",
            lambda event: self._fit_chat_heading(
                event.widget,
                "Un espacio para pensar tu siguiente paso",
            ),
        )
        subtitle = self._label(
            title_area,
            "GuIA te acompaña a organizarte; tú decides cómo avanzar.",
            color=COLORS["muted"],
        )
        subtitle.pack(fill="x", padx=16, pady=(0, 13))
        subtitle.bind(
            "<Configure>",
            lambda event: self._fit_chat_heading(
                event.widget,
                "GuIA te acompaña a organizarte; tú decides cómo avanzar.",
            ),
        )
        self.status_base = (
            f"✦  {self.chat_store.estado}"
            if self.chat_store.ocupado
            else "●  Disponible"
        )
        status_color = (
            COLORS["accent_light"] if self.chat_store.ocupado else COLORS["green"]
        )
        self.chat_status_label = tk.Label(
            intro,
            text=self.status_base,
            bg=COLORS["surface"],
            fg=status_color,
            font=(FONT, 9, "bold"),
        )
        self.chat_status_label.pack(side="right", padx=16)
        self.status_label = self.chat_status_label

    @staticmethod
    def _fit_chat_heading(label, text):
        width = label.winfo_width() - 32
        if width > 0:
            label.configure(
                text=texto_con_elipsis(
                    text,
                    tkfont.Font(font=label.cget("font")),
                    width,
                )
            )
