"""Sección servicios de la interfaz de Aethera."""

import tkinter as tk
from tkinter import ttk

from core.services import buscar_servicios_ayuda
from .tema import (
    COLORS,
    FONT,
    SERVICE_CATEGORIES,
    SERVICE_CHANNELS,
    SERVICE_DISTRICTS,
    SERVICE_TYPES,
    WEEKDAYS,
)
from .widgets import AnimatedDropdown


class ServicesSection:
    def _show_services(self):
        self._label(
            self.content,
            "Encuentra apoyo disponible",
            size=22,
            weight="bold",
            bg=COLORS["background"],
        ).pack(anchor="w")
        self._label(
            self.content,
            "Explora opciones institucionales según lo que necesites.",
            color=COLORS["muted"],
            bg=COLORS["background"],
        ).pack(anchor="w", pady=(5, 18))

        controls = self._card(self.content)
        controls.pack(fill="x", pady=(0, 14))
        self._label(
            controls,
            "Filtra las opciones para encontrar el apoyo adecuado",
            size=11,
            weight="bold",
        ).pack(anchor="w", padx=18, pady=(16, 12))
        filters = tk.Frame(controls, bg=COLORS["surface"])
        filters.pack(fill="x", padx=18, pady=(0, 16))

        category_filter = tk.Frame(filters, bg=COLORS["surface"])
        category_filter.pack(side="left", padx=(0, 12))
        self._label(category_filter, "TIPO DE APOYO", size=8, color=COLORS["muted"]).pack(
            anchor="w", pady=(0, 5)
        )
        self.category_var = tk.StringVar(value=next(iter(SERVICE_CATEGORIES)))
        self.category_selector = AnimatedDropdown(
            category_filter,
            textvariable=self.category_var,
            values=tuple(SERVICE_CATEGORIES),
            width=320,
            on_select=lambda _value: self._on_service_filter(),
        )
        self.category_selector.pack()

        district_filter = tk.Frame(filters, bg=COLORS["surface"])
        district_filter.pack(side="left", padx=(0, 12))
        self._label(district_filter, "DISTRITO", size=8, color=COLORS["muted"]).pack(
            anchor="w", pady=(0, 5)
        )
        self.district_var = tk.StringVar(value=next(iter(SERVICE_DISTRICTS)))
        self.district_selector = AnimatedDropdown(
            district_filter,
            textvariable=self.district_var,
            values=tuple(SERVICE_DISTRICTS),
            width=250,
            on_select=lambda _value: self._on_service_filter(),
        )
        self.district_selector.pack()

        search_filter = tk.Frame(filters, bg=COLORS["surface"])
        search_filter.pack(side="left", fill="x", expand=True)
        self._label(search_filter, "BUSCAR SERVICIO", size=8, color=COLORS["muted"]).pack(
            anchor="w", pady=(0, 5)
        )
        self.service_search_var = tk.StringVar()
        search_entry = tk.Entry(
            search_filter,
            textvariable=self.service_search_var,
            bg=COLORS["surface_light"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            font=(FONT, 9),
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
        )
        search_entry.pack(fill="x", ipady=9)
        self._bind_native_widget_animations(search_entry)

        self.service_search_var.trace_add("write", self._on_service_search)

        self.services_result = self._card(self.content)
        self.services_result.pack(fill="both", expand=True)
        results_header = tk.Frame(self.services_result, bg=COLORS["surface"])
        results_header.pack(fill="x", padx=16, pady=(12, 5))
        self._label(results_header, "Servicios disponibles", size=11, weight="bold").pack(
            side="left"
        )
        self.service_count = self._label(
            results_header,
            "",
            size=8,
            color=COLORS["accent_light"],
            bg=COLORS["surface_light"],
        )
        self.service_count.pack(side="right", padx=9, pady=3)
        self.services_canvas = tk.Canvas(
            self.services_result,
            bg=COLORS["surface"],
            highlightthickness=0,
            bd=0,
        )
        self.services_scrollbar = ttk.Scrollbar(
            self.services_result,
            orient="vertical",
            command=self.services_canvas.yview,
        )
        self.service_cards_container = tk.Frame(
            self.services_canvas,
            bg=COLORS["surface"],
        )
        self.service_cards_container.bind(
            "<Configure>",
            lambda _event: self.services_canvas.configure(
                scrollregion=self.services_canvas.bbox("all")
            ),
        )
        self.services_canvas.create_window(
            (0, 0),
            window=self.service_cards_container,
            anchor="nw",
            tags="service_cards",
        )
        self.services_canvas.configure(yscrollcommand=self.services_scrollbar.set)
        self.services_canvas.bind(
            "<Configure>",
            lambda event: self.services_canvas.itemconfigure(
                "service_cards",
                width=event.width,
            ),
        )
        self._bind_smooth_scroll(self.services_canvas, self.service_cards_container)
        self.services_canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 10))
        self.services_scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=(0, 10))
        self._load_services()

    def _on_service_filter(self, _event=None):
        self._load_services()

    def _on_service_search(self, *_args):
        if hasattr(self, "service_cards_container"):
            if self._search_after_id:
                self.root.after_cancel(self._search_after_id)
            self._cancel_service_render()
            self._services_request_id += 1
            self._search_after_id = self.root.after(140, self._load_services)

    def _cancel_service_render(self):
        if self._service_render_after_id:
            self.root.after_cancel(self._service_render_after_id)
            self._service_render_after_id = None
        self._service_render_services = []
        self._service_render_index = 0

    def _load_services(self):
        self._search_after_id = None
        self._cancel_service_render()
        for child in self.service_cards_container.winfo_children():
            child.destroy()
        self.service_count.configure(text="Cargando…")
        category = SERVICE_CATEGORIES[self.category_var.get()]
        selected_district = SERVICE_DISTRICTS[self.district_var.get()]
        query = self.service_search_var.get().strip().casefold()
        self._services_request_id += 1
        request_id = self._services_request_id
        self.tasks.lanzar(
            "buscar_servicios",
            lambda _tarea: self._search_services(
                request_id, category, selected_district, query
            ),
            contexto={"consulta": query},
        )

    def _search_services(self, request_id, category, selected_district, query):
        try:
            result = buscar_servicios_ayuda(category, selected_district)
            if "error" in result:
                raise ValueError(result["error"])
            services = [
                service
                for service in result["servicios"]
                if (
                    not query
                    or query
                    in " ".join(
                        (
                            service["nombre"],
                            service["tipo_servicio"],
                            service["ubicacion"]["distrito_id"],
                        )
                    ).casefold()
                )
            ]
            self.event_queue.put(("services", (request_id, services, None)))
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.event_queue.put(("services", (request_id, None, str(error))))

    def _display_services(self, request_id, services, error):
        if (
            request_id != self._services_request_id
            or self.current_page != "Servicios de apoyo"
        ):
            return
        if error is not None:
            self.service_count.configure(text="Error")
            self._notice(
                self.service_cards_container,
                f"No se pudieron cargar los servicios de apoyo: {error}",
                COLORS["red"],
            )
            return
        self.service_count.configure(
            text=f"{len(services)} {'opciones' if len(services) != 1 else 'opción'}"
        )
        if not services:
            self._show_empty_services()
            return
        self._service_render_services = services
        self._service_render_index = 0
        self._service_render_after_id = self.root.after_idle(
            lambda: self._render_service_batch(request_id)
        )

    def _render_service_batch(self, request_id):
        self._service_render_after_id = None
        if (
            request_id != self._services_request_id
            or self.current_page != "Servicios de apoyo"
        ):
            return
        batch_size = 2
        batch_end = min(
            self._service_render_index + batch_size,
            len(self._service_render_services),
        )
        for index in range(self._service_render_index, batch_end):
            self._service_card(self._service_render_services[index], index)
        self._service_render_index = batch_end
        if batch_end < len(self._service_render_services):
            self._service_render_after_id = self.root.after(
                1,
                lambda: self._render_service_batch(request_id),
            )

    def _service_card(self, service, index):
        card = self._card(
            self.service_cards_container,
            bg=COLORS["surface_light"],
            radius=22,
            gradient=("#202d4b", COLORS["surface_light"], "#24204a"),
        )
        card.grid(
            row=index // 2,
            column=index % 2,
            sticky="nsew",
            padx=(4, 7) if index % 2 == 0 else (7, 4),
            pady=7,
        )
        self._animate_card_in(card, grid=True)
        self.service_cards_container.grid_columnconfigure(0, weight=1, uniform="service")
        self.service_cards_container.grid_columnconfigure(1, weight=1, uniform="service")

        heading = tk.Frame(card, bg=COLORS["surface_light"])
        heading.pack(fill="x", padx=14, pady=(13, 8))
        icon = tk.Label(
            heading,
            text="♡",
            bg="#282650",
            fg=COLORS["accent_light"],
            font=(FONT, 15, "bold"),
            width=2,
            height=1,
        )
        icon.pack(side="left", padx=(0, 10), ipady=3)
        title_area = tk.Frame(heading, bg=COLORS["surface_light"])
        title_area.pack(side="left", fill="x", expand=True)
        self._label(
            title_area,
            service["nombre"],
            size=10,
            weight="bold",
            bg=COLORS["surface_light"],
            wraplength=330,
            justify="left",
        ).pack(anchor="w")
        service_type = SERVICE_TYPES.get(
            service["tipo_servicio"],
            service["tipo_servicio"].replace("_", " ").title(),
        )
        district = self._format_district(service["ubicacion"]["distrito_id"])
        self._label(
            title_area,
            f"{service_type}  ·  {district}",
            size=8,
            color=COLORS["muted"],
            bg=COLORS["surface_light"],
        ).pack(anchor="w", pady=(3, 0))

        self._service_detail(
            card,
            "HORARIO",
            self._format_schedule(service["horario_atencion"]),
        )
        channels = service["canales_atencion"]
        channel_names = [
            SERVICE_CHANNELS.get(channel, channel.replace("_", " ").title())
            for channel in channels
        ]
        self._service_detail(card, "CANALES DE ATENCIÓN", "  ·  ".join(channel_names))
        self._service_detail(
            card,
            "ORIENTACIÓN",
            self._format_referral(service["informacion_requerida_derivacion"]),
        )
        self._label(
            card,
            "Servicio demostrativo · Datos ficticios",
            size=8,
            color=COLORS["muted"],
            bg=COLORS["surface_light"],
        ).pack(anchor="w", padx=14, pady=(4, 12))

    def _service_detail(self, parent, label, value):
        detail = tk.Frame(parent, bg=COLORS["surface_light"])
        detail.pack(fill="x", padx=14, pady=4)
        self._label(
            detail,
            label,
            size=7,
            color=COLORS["accent_light"],
            weight="bold",
            bg=COLORS["surface_light"],
        ).pack(anchor="w")
        self._label(
            detail,
            value,
            size=9,
            color=COLORS["text"],
            bg=COLORS["surface_light"],
            wraplength=360,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

    def _format_district(self, district_id):
        name = district_id.removeprefix("DIST_").title()
        return f"Distrito {name}"

    def _format_schedule(self, schedule):
        day_range, _, hours = schedule.partition(" ")
        readable_days = WEEKDAYS.get(day_range, day_range)
        if not hours:
            return readable_days
        start, separator, end = hours.partition("-")
        if separator:
            return f"{readable_days}  ·  {start}–{end} h"
        return f"{readable_days}  ·  {hours}"

    def _format_referral(self, information):
        labels = {
            "student_id": "identificador del estudiante",
            "preferred channel": "canal de atención preferido",
            "non-clinical reason code": "motivo de orientación (no clínico)",
        }
        parts = [item.strip() for item in information.split(",")]
        return " · ".join(
            labels.get(part.casefold(), part.replace("_", " ").capitalize())
            for part in parts
        )

    def _show_empty_services(self):
        empty = tk.Frame(self.service_cards_container, bg=COLORS["surface"])
        empty.pack(fill="x", padx=8, pady=24)
        tk.Label(
            empty,
            text="⌕",
            bg=COLORS["surface"],
            fg=COLORS["accent_light"],
            font=(FONT, 28),
        ).pack()
        self._label(
            empty,
            "No encontramos servicios con estos filtros",
            size=11,
            weight="bold",
        ).pack(pady=(3, 5))
        self._label(
            empty,
            "Prueba con otro distrito o una búsqueda más amplia.",
            size=9,
            color=COLORS["muted"],
        ).pack()
