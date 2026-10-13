"""Controles de encabezado y filtros del calendario."""

import tkinter as tk

from ...tema import COLORS, MONTH_NAMES
from ...widgets import AnimatedDropdown


class CalendarHeader:
    def _format_calendar_range(self, start, end):
        start_month = MONTH_NAMES[start.month - 1]
        end_month = MONTH_NAMES[end.month - 1]
        if start.year != end.year:
            return (
                f"{start.day} {start_month[:3]} {start.year}  —  "
                f"{end.day} {end_month[:3]} {end.year}"
            )
        if start.month == end.month:
            return f"{start.day} – {end.day} de {start_month} {start.year}"
        return (
            f"{start.day} {start_month[:3]}  —  "
            f"{end.day} {end_month[:3]} {end.year}"
        )

    def _render_calendar_header(self):
        heading = tk.Frame(self.content, bg=COLORS["background"])
        heading.pack(fill="x", pady=(0, 14))
        title_area = tk.Frame(heading, bg=COLORS["background"])
        title_area.pack(side="left")
        self._label(
            title_area,
            "Tu calendario",
            size=24,
            weight="bold",
            bg=COLORS["background"],
        ).pack(anchor="w")
        self._label(
            title_area,
            "Organiza tus eventos académicos y personales en una sola vista.",
            size=10,
            color=COLORS["muted"],
            bg=COLORS["background"],
        ).pack(anchor="w", pady=(4, 0))
        self._button(
            heading,
            "＋ Crear evento",
            self._show_create_calendar_event,
            primary=True,
        ).pack(side="right", anchor="center", padx=(12, 0))

        toolbar = self._card(
            self.content,
            radius=22,
            bg=COLORS["surface"],
            gradient=("#141d34", "#11182b", "#191a38"),
        )
        toolbar.pack(fill="x", pady=(0, 14))
        navigation = tk.Frame(toolbar, bg=COLORS["surface"])
        navigation.pack(side="left", padx=14, pady=11)
        self._button(
            navigation,
            "‹",
            lambda: self._shift_calendar_week(-7),
        ).pack(side="left", padx=(0, 6))
        self._button(
            navigation,
            "Hoy",
            self._go_to_calendar_today,
        ).pack(side="left", padx=5)
        self._button(
            navigation,
            "›",
            lambda: self._shift_calendar_week(7),
        ).pack(side="left", padx=(6, 0))

        self.calendar_range_label = self._label(
            toolbar,
            "",
            size=14,
            weight="bold",
            bg=COLORS["surface"],
        )
        self.calendar_range_label.pack(side="left", padx=18)
        self.calendar_count_label = self._label(
            toolbar,
            "",
            size=9,
            color=COLORS["muted"],
            bg=COLORS["surface"],
        )
        self.calendar_count_label.pack(side="left", padx=6)

        filter_area = tk.Frame(toolbar, bg=COLORS["surface"])
        filter_area.pack(side="right", padx=15, pady=11)
        self._label(
            filter_area,
            "MOSTRAR",
            size=8,
            color=COLORS["muted"],
            bg=COLORS["surface"],
        ).pack(side="left", padx=(0, 8))
        self.calendar_source_var = tk.StringVar(value="Ambos")
        self.calendar_source_selector = AnimatedDropdown(
            filter_area,
            textvariable=self.calendar_source_var,
            values=("Ambos", "Académico", "Personal"),
            width=145,
            on_select=lambda _value: self._refresh_calendar(),
        )
        self.calendar_source_selector.pack(side="left", padx=(0, 7))
        self.calendar_category_var = tk.StringVar(value="Todos los eventos")
        self.calendar_category_selector = AnimatedDropdown(
            filter_area,
            textvariable=self.calendar_category_var,
            values=(
                "Todos los eventos",
                "Evaluaciones",
                "Bienestar",
                "Períodos académicos",
                "Actividades",
            ),
            width=205,
            on_select=lambda _value: self._refresh_calendar(),
        )
        self.calendar_category_selector.pack(side="left")

