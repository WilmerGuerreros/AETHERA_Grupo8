"""Título, subtítulo e estado del chat."""

import tkinter as tk

from ...tema import COLORS, FONT


class ChatHeader:
    def _render_chat_header(self):
        intro = self._card(self.content)
        intro.pack(fill="x", pady=(0, 12))
        title_area = tk.Frame(intro, bg=COLORS["surface"])
        title_area.pack(side="left", fill="x", expand=True)
        self._label(
            title_area,
            "Un espacio para pensar tu siguiente paso",
            size=14,
            weight="bold",
        ).pack(anchor="w", padx=16, pady=(13, 3))
        self._label(
            title_area,
            "GuIA te acompaña a organizarte; tú decides cómo avanzar.",
            color=COLORS["muted"],
        ).pack(anchor="w", padx=16, pady=(0, 13))
        self.status_base = (
            "✦  GuIA está pensando" if self.busy else "●  Disponible"
        )
        status_color = COLORS["accent_light"] if self.busy else COLORS["green"]
        self.chat_status_label = tk.Label(
            intro,
            text=self.status_base,
            bg=COLORS["surface"],
            fg=status_color,
            font=(FONT, 9, "bold"),
        )
        self.chat_status_label.pack(side="right", padx=16)
        self.status_label = self.chat_status_label
