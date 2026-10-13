"""Orquestación de la sección de calendario."""

import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk

from ..tema import COLORS, FONT
from .components import CalendarGrid, CalendarHeader, CalendarModal
from .logica import obtener_eventos_semana


class CalendarSection(CalendarHeader, CalendarGrid, CalendarModal):
    def _go_to_calendar_today(self):
        today = date.today()
        self.calendar_week_start = today - timedelta(days=today.weekday())
        self._refresh_calendar(direction=0)

    def _shift_calendar_week(self, days):
        self.calendar_week_start += timedelta(days=days)
        self._refresh_calendar(direction=1 if days > 0 else -1)

    def _refresh_calendar(self, direction=0):
        if not hasattr(self, "calendar_canvas") or not self.calendar_canvas.winfo_exists():
            return
        self._calendar_transition_direction = direction or 1
        for after_id in self._calendar_animation_ids:
            self.root.after_cancel(after_id)
        self._calendar_animation_ids.clear()
        start = self.calendar_week_start
        end = start + timedelta(days=6)
        self.calendar_range_label.configure(
            text=self._format_calendar_range(start, end)
        )
        self.calendar_canvas.delete("all")
        try:
            events = obtener_eventos_semana(
                start,
                end,
                self.calendar_source_var.get(),
                self.calendar_category_var.get(),
            )
            self.calendar_events = events
            self.calendar_count_label.configure(
                text=f"·  {len(events)} "
                f"{'eventos' if len(events) != 1 else 'evento'} esta semana"
            )
            self._draw_calendar(direction=direction)
            self.calendar_canvas.yview_moveto(0)
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.calendar_count_label.configure(text="·  No disponible")
            self.calendar_canvas.delete("all")
            self.calendar_canvas.create_text(
                36,
                42,
                text=f"No se pudo cargar el calendario: {error}",
                anchor="nw",
                fill=COLORS["red"],
                font=(FONT, 12),
            )

    def _show_calendar(self):
        self._render_calendar_header()
        calendar_panel = self._card(
            self.content,
            radius=24,
            bg=COLORS["surface"],
            border="#343653",
        )
        calendar_panel.pack(fill="both", expand=True)
        self.calendar_canvas = tk.Canvas(
            calendar_panel,
            bg=COLORS["surface"],
            highlightthickness=0,
            bd=0,
        )
        self.calendar_scrollbar = ttk.Scrollbar(
            calendar_panel,
            orient="vertical",
            command=self.calendar_canvas.yview,
        )
        self.calendar_canvas.configure(
            yscrollcommand=self.calendar_scrollbar.set,
        )
        self.calendar_canvas.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(8, 0),
            pady=8,
        )
        self.calendar_scrollbar.pack(
            side="right",
            fill="y",
            padx=(0, 8),
            pady=8,
        )
        self._bind_smooth_scroll(self.calendar_canvas, self.calendar_canvas)
        self.calendar_canvas.bind("<Configure>", self._draw_calendar)
        self._refresh_calendar()
