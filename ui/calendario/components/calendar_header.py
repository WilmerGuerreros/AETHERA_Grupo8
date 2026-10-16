"""Controles de encabezado y filtros del calendario."""

import tkinter as tk
from tkinter import font as tkfont

from core.calendar import categorias_disponibles, origenes_disponibles
from ...tema import COLORS, MONTH_NAMES, opciones_por_etiqueta
from ...widgets import AnimatedDropdown, texto_con_elipsis


class CalendarHeader:
    def _origenes_calendario(self):
        try:
            return origenes_disponibles()
        except (OSError, ValueError, KeyError, TypeError):
            return ()

    def _categorias_calendario(self):
        try:
            return categorias_disponibles()
        except (OSError, ValueError, KeyError, TypeError):
            return ()

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
        self.calendar_range_label.pack(side="left", fill="x", expand=True, padx=18)
        self.calendar_range_label.bind(
            "<Configure>",
            self._fit_calendar_range,
        )
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
        self.calendar_source_var = tk.StringVar()
        self._calendar_source_options = opciones_por_etiqueta(
            self._origenes_calendario(), etiqueta_vacia="Todos los calendarios"
        )
        self.calendar_source_var.set(next(iter(self._calendar_source_options)))
        self.calendar_source_selector = AnimatedDropdown(
            filter_area,
            textvariable=self.calendar_source_var,
            values=tuple(self._calendar_source_options),
            width=145,
            on_select=lambda _value: self._refresh_calendar(),
        )
        self.calendar_source_selector.pack(side="left", padx=(0, 7))
        self._calendar_all_categories_label = "Todas las categorías"
        self._calendar_category_options = opciones_por_etiqueta(
            self._categorias_calendario(),
            etiqueta_vacia=self._calendar_all_categories_label,
        )
        self.calendar_category_var = tk.StringVar(
            value=self._calendar_all_categories_label
        )
        self.calendar_category_selector = AnimatedDropdown(
            filter_area,
            textvariable=self.calendar_category_var,
            values=tuple(self._calendar_category_options),
            width=205,
            on_select=lambda _value: self._refresh_calendar(),
        )
        self.calendar_category_selector.pack(side="left")
        self._calendar_filter_area = filter_area
        self._calendar_toolbar = toolbar
        self._calendar_toolbar_layout = None
        self._calendar_toolbar_after_id = None
        toolbar.bind("<Configure>", self._schedule_calendar_toolbar_layout)

    def _set_calendar_range(self, text):
        self._calendar_range_text = text
        self._fit_calendar_range()

    def _fit_calendar_range(self, _event=None):
        if not hasattr(self, "calendar_range_label"):
            return
        text = getattr(self, "_calendar_range_text", "")
        label = self.calendar_range_label
        width = label.winfo_width() - 8
        if width > 0:
            label.configure(
                text=texto_con_elipsis(
                    text,
                    tkfont.Font(font=label.cget("font")),
                    width,
                )
            )

    def _schedule_calendar_toolbar_layout(self, _event=None):
        if self._calendar_toolbar_after_id:
            self.root.after_cancel(self._calendar_toolbar_after_id)
        self._calendar_toolbar_after_id = self.root.after_idle(
            self._layout_calendar_toolbar
        )

    def _layout_calendar_toolbar(self):
        self._calendar_toolbar_after_id = None
        if not self._calendar_toolbar.winfo_exists():
            return
        narrow = self._calendar_toolbar.winfo_width() < 1010
        layout = "stacked" if narrow else "inline"
        if layout != self._calendar_toolbar_layout:
            if narrow:
                self.calendar_count_label.pack_forget()
                self._calendar_filter_area.pack_configure(
                    side="bottom",
                    fill="x",
                    anchor="w",
                )
            else:
                self._calendar_filter_area.pack_configure(
                    side="right",
                    fill="none",
                    anchor="center",
                )
                self.calendar_count_label.pack(
                    side="left",
                    padx=6,
                )
            self._calendar_toolbar_layout = layout
        self.root.after_idle(self._fit_calendar_filters)

    def _fit_calendar_filters(self):
        area_width = self._calendar_filter_area.winfo_width()
        if area_width < 1:
            return
        label_width = 70
        selector_width = min(
            220,
            max(110, (area_width - label_width - 38) // 2),
        )
        if self._calendar_toolbar_layout == "stacked":
            self.calendar_source_selector.set_width(selector_width)
            self.calendar_category_selector.set_width(selector_width)
        else:
            self.calendar_source_selector.set_width(145)
            self.calendar_category_selector.set_width(205)
