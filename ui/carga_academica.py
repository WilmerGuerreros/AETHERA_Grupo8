"""Sección carga academica de la interfaz de Aethera."""

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
            for week in report["semanas_con_sobrecarga"]:
                risk_color = COLORS["red"] if week["nivel_riesgo"] == "ALTO" else COLORS["yellow"]
                card = self._card(panel, bg=COLORS["surface_light"])
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
