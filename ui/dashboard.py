"""Sección dashboard de la interfaz de Aethera."""

import tkinter as tk
from datetime import date, datetime

from dominio.calendario import buscar_eventos
from dominio.carga_academica import evaluar_riesgo_sobrecarga
from .tema import COLORS


class DashboardSection:
    def _show_dashboard(self):
        self._label(
            self.content,
            f"Hola de nuevo!  {self._greeting()}",
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

        welcome = self._card(
            self.content,
            bg="#171a3a",
            border="#4d4c99",
            radius=30,
            gradient=("#171a3a", "#171a3a", "#30245f"),
        )
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
            "Cuéntale a GuIA qué tienes pendiente y construyan juntos un siguiente paso.",
            color="#c4c7e7",
            bg="#171a3a",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(7, 15))
        self._button(
            left,
            "Conversar con GuIA  →",
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
        events = buscar_eventos("any", fecha_inicio=today, origen="academico")
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
