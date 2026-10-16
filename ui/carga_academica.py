"""Sección carga academica de la interfaz de Aethera."""

import tkinter as tk
from tkinter import ttk

from core.workload import evaluar_riesgo_sobrecarga
from .tema import COLORS


class WorkloadSection:
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
            results_frame = tk.Frame(panel, bg=COLORS["surface"])
            results_frame.pack(
                fill="both",
                expand=True,
                padx=(12, 8),
                pady=(0, 10),
            )
            results_canvas = tk.Canvas(
                results_frame,
                bg=COLORS["surface"],
                highlightthickness=0,
                bd=0,
            )
            results_scrollbar = ttk.Scrollbar(
                results_frame,
                orient="vertical",
                style="Aethera.Vertical.TScrollbar",
                command=lambda *args: self._scrollbar_command(
                    results_canvas,
                    *args,
                ),
            )
            results_list = tk.Frame(results_canvas, bg=COLORS["surface"])
            results_window = results_canvas.create_window(
                (0, 0),
                window=results_list,
                anchor="nw",
            )
            results_list.bind(
                "<Configure>",
                lambda _event: results_canvas.configure(
                    scrollregion=results_canvas.bbox("all")
                ),
            )
            results_canvas.bind(
                "<Configure>",
                lambda event: results_canvas.itemconfigure(
                    results_window,
                    width=event.width,
                ),
            )
            results_canvas.configure(
                yscrollcommand=results_scrollbar.set,
            )
            self._bind_smooth_scroll(results_canvas, results_list)
            results_canvas.pack(side="left", fill="both", expand=True)
            results_scrollbar.pack(side="right", fill="y", padx=(5, 0))
            for week in report["semanas_con_sobrecarga"]:
                risk_color = COLORS["red"] if week["nivel_riesgo"] == "ALTO" else COLORS["yellow"]
                card = self._card(results_list, bg=COLORS["surface_light"])
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
