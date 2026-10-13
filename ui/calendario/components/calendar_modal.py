"""Diálogos para crear, consultar y eliminar eventos."""

import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from ...tema import COLORS, EVENT_STYLES, FONT
from ..logica import borrar_evento_personal, guardar_evento_personal


class CalendarModal:
    def _show_create_calendar_event(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Crear evento personal")
        dialog.configure(bg=COLORS["background"])
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("560x700")
        dialog.resizable(False, False)
        panel = self._card(
            dialog,
            radius=28,
            bg="#17213b",
            gradient=("#17213b", "#17213b", "#25204c"),
        )
        panel.pack(fill="both", expand=True, padx=14, pady=14)
        self._label(
            panel,
            "Nuevo evento personal",
            size=20,
            weight="bold",
            bg="#17213b",
        ).pack(anchor="w", padx=24, pady=(22, 4))
        self._label(
            panel,
            "Fechas AAAA-MM-DD. Deja ambas horas vacías para un evento de día completo.",
            size=9,
            color=COLORS["muted"],
            bg="#17213b",
        ).pack(anchor="w", padx=24, pady=(0, 16))

        fields = tk.Frame(panel, bg="#17213b")
        fields.pack(fill="x", padx=24)

        def add_entry(label, initial=""):
            self._label(
                fields,
                label,
                size=9,
                color=COLORS["muted"],
                bg="#17213b",
            ).pack(anchor="w", pady=(8, 4))
            entry = tk.Entry(
                fields,
                bg=COLORS["surface_light"],
                fg=COLORS["text"],
                insertbackground=COLORS["text"],
                relief="flat",
                font=(FONT, 11),
            )
            entry.pack(fill="x", ipady=8)
            if initial:
                entry.insert(0, initial)
            return entry

        title_entry = add_entry("Título")
        start_entry = add_entry("Fecha de inicio", date.today().isoformat())
        end_entry = add_entry("Fecha de fin (opcional)")
        time_start_entry = add_entry("Hora de inicio (opcional, HH:MM)")
        time_end_entry = add_entry("Hora de fin (opcional, HH:MM)")
        self._label(
            fields,
            "Descripción (opcional)",
            size=9,
            color=COLORS["muted"],
            bg="#17213b",
        ).pack(anchor="w", pady=(12, 4))
        description_entry = tk.Text(
            fields,
            height=4,
            wrap="word",
            bg=COLORS["surface_light"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            font=(FONT, 10),
            padx=9,
            pady=8,
        )
        description_entry.pack(fill="x")
        error_label = self._label(
            panel,
            "",
            size=9,
            color=COLORS["red"],
            bg="#17213b",
            wraplength=470,
            justify="left",
        )
        error_label.pack(anchor="w", padx=24, pady=(8, 0))

        def save_event():
            result = guardar_evento_personal(
                title_entry.get(),
                start_entry.get().strip(),
                end_entry.get().strip(),
                description_entry.get("1.0", "end").strip(),
                time_start_entry.get().strip(),
                time_end_entry.get().strip(),
            )
            if "error" in result:
                error_label.configure(text=result["error"])
                return
            dialog.destroy()
            self.calendar_source_var.set("Personal")
            self.calendar_category_var.set("Todos los eventos")
            self._refresh_calendar()

        buttons = tk.Frame(panel, bg="#17213b")
        buttons.pack(fill="x", padx=24, pady=(12, 18))
        self._button(buttons, "Cancelar", dialog.destroy).pack(side="left")
        self._button(
            buttons,
            "Guardar evento",
            save_event,
            primary=True,
        ).pack(side="right")
        title_entry.focus_set()

    def _show_calendar_event(self, event):
        dialog_anterior = getattr(self, "_calendar_event_dialog", None)
        if dialog_anterior is not None and dialog_anterior.winfo_exists():
            dialog_anterior.destroy()

        dialog = tk.Toplevel(self.root)
        self._calendar_event_dialog = dialog
        origen = event.get("origen", "academico")
        nombre_calendario = "Personal" if origen == "personal" else "Académico"
        dialog.title(event.get("resumen", "Evento"))
        dialog.configure(bg=COLORS["background"])
        dialog.transient(self.root)
        dialog.geometry("600x480")
        dialog.minsize(520, 400)
        dialog.protocol(
            "WM_DELETE_WINDOW",
            lambda: self._close_calendar_event_dialog(dialog),
        )
        panel = self._card(
            dialog,
            radius=28,
            bg="#17213b",
            gradient=("#17213b", "#17213b", "#25204c"),
        )
        panel.pack(fill="both", expand=True, padx=14, pady=14)
        details = tk.Frame(panel, bg="#17213b")
        details.pack(fill="both", expand=True, padx=24, pady=(20, 8))
        category = event.get("categoria", "")
        _, accent, _ = EVENT_STYLES.get(
            category,
            (COLORS["surface_light"], COLORS["accent_light"], COLORS["border"]),
        )
        self._label(
            details,
            (
                "PERSONAL"
                if origen == "personal"
                else self._format_calendar_category(category).upper()
            ),
            size=9,
            color=accent,
            weight="bold",
            bg="#17213b",
        ).pack(anchor="w", pady=(0, 7))
        self._label(
            details,
            event.get("resumen", "Evento"),
            size=20,
            weight="bold",
            bg="#17213b",
            wraplength=500,
            justify="left",
        ).pack(anchor="w", fill="x")
        start = date.fromisoformat(event["fecha_inicio"])
        end = date.fromisoformat(event["fecha_fin"])
        dates = start.strftime("%d/%m/%Y")
        if end != start:
            dates += f"  —  {end.strftime('%d/%m/%Y')}"
        if event.get("hora_inicio") and event.get("hora_fin"):
            dates += f"  ·  {event['hora_inicio']}–{event['hora_fin']}"
        self._label(
            details,
            f"◷   {dates}",
            size=12,
            color=COLORS["muted"],
            bg="#17213b",
        ).pack(anchor="w", pady=(14, 10))
        if origen == "personal":
            descripcion = event.get("descripcion")
            detalle = "Descripción"
            detalle_texto = descripcion or "Evento personal"
        else:
            district = event.get("distrito_id") or "ALL"
            detalle = f"Ubicación: {district.replace('DIST_', 'Distrito ').title()}"
        self._label(
            details,
            detalle,
            size=9,
            color=COLORS["accent_light"],
            weight="bold",
            bg="#17213b",
        ).pack(anchor="w", pady=(0, 5))
        if origen == "personal":
            description_frame = tk.Frame(details, bg="#17213b")
            description_frame.pack(fill="both", expand=True)
            description = tk.Text(
                description_frame,
                height=8,
                wrap="word",
                bg=COLORS["surface_light"],
                fg=COLORS["muted"],
                relief="flat",
                font=(FONT, 10),
                padx=10,
                pady=8,
            )
            description.insert("1.0", detalle_texto)
            description.configure(state="disabled")
            description.pack(side="left", fill="both", expand=True)
            description_scrollbar = ttk.Scrollbar(
                description_frame,
                orient="vertical",
                command=description.yview,
            )
            description.configure(yscrollcommand=description_scrollbar.set)
            description_scrollbar.pack(side="right", fill="y")
        self._label(
            details,
            f"Calendario: {nombre_calendario}",
            size=9,
            color=COLORS["muted"],
            bg="#17213b",
        ).pack(anchor="w", pady=(10, 0))
        buttons = tk.Frame(panel, bg="#17213b")
        buttons.pack(fill="x", padx=24, pady=(8, 18))
        self._button(
            buttons,
            "Cerrar",
            lambda: self._close_calendar_event_dialog(dialog),
        ).pack(side="right")
        if origen == "personal":
            tk.Button(
                buttons,
                text="Eliminar evento",
                command=lambda: self._delete_personal_event(event, dialog),
                bg=COLORS["red"],
                fg="#ffffff",
                activebackground="#e85f70",
                activeforeground="#ffffff",
                relief="flat",
                borderwidth=0,
                padx=16,
                pady=10,
                font=(FONT, 10, "bold"),
                cursor="hand2",
            ).pack(side="left")
        dialog.lift()

    def _close_calendar_event_dialog(self, dialog):
        if getattr(self, "_calendar_event_dialog", None) is dialog:
            self._calendar_event_dialog = None
        if dialog.winfo_exists():
            dialog.destroy()

    def _delete_personal_event(self, event, dialog):
        if not messagebox.askyesno(
            "Eliminar evento",
            f"¿Quieres eliminar «{event.get('resumen', 'este evento')}» "
            "del calendario Personal?",
            parent=dialog,
        ):
            return
        result = borrar_evento_personal(event)
        if "error" in result:
            messagebox.showerror("No se pudo eliminar", result["error"], parent=dialog)
            return
        self._close_calendar_event_dialog(dialog)
        self._refresh_calendar()
