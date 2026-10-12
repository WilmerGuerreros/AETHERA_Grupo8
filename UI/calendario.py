"""Sección calendario de la interfaz de Aethera."""

from .components import (
    AnimatedDropdown,
    COLORS,
    EVENT_STYLES,
    FONT,
    MONTH_NAMES,
    WEEKDAY_NAMES,
    _mix_color,
    buscar_eventos,
    date,
    datetime,
    math,
    timedelta,
    tk,
    ttk,
)

class CalendarSection:
    def _show_calendar(self):
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
            events = buscar_eventos(
                "any",
                fecha_inicio=start.isoformat(),
                fecha_fin=end.isoformat(),
                origen={
                    "Ambos": "ambos",
                    "Académico": "academico",
                    "Personal": "personal",
                }[self.calendar_source_var.get()],
            )
            if events and "error" in events[0]:
                raise ValueError(events[0]["error"])
            events = self._filter_calendar_events(events)
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

    def _filter_calendar_events(self, events):
        selection = self.calendar_category_var.get()
        category_groups = {
            "Evaluaciones": {"evaluation_week"},
            "Bienestar": {"wellbeing_activity"},
            "Períodos académicos": {"period_start", "period_end"},
            "Actividades": {"university_activity"},
        }
        allowed = category_groups.get(selection)
        if allowed is None:
            return events
        return [event for event in events if event.get("categoria") in allowed]

    def _draw_calendar(self, _event=None, direction=0):
        if not hasattr(self, "calendar_canvas"):
            return
        canvas = self.calendar_canvas
        if not canvas.winfo_exists():
            return
        for after_id in self._calendar_animation_ids:
            self.root.after_cancel(after_id)
        self._calendar_animation_ids.clear()
        width = max(canvas.winfo_width(), 900)
        start = self.calendar_week_start
        days = [start + timedelta(days=index) for index in range(7)]
        left = 78
        right = width - 14
        column_width = (right - left) / 7
        header_top = 18
        header_height = 68
        event_header_top = header_top + header_height
        event_area_top = event_header_top + 28
        event_rows = max(1, len(getattr(self, "calendar_events", [])))
        event_row_height = 38
        event_area_height = max(66, event_rows * event_row_height + 12)
        grid_top = event_area_top + event_area_height + 8
        hour_height = 54
        first_hour, last_hour = 8, 20
        total_height = grid_top + (last_hour - first_hour) * hour_height + 25
        canvas.delete("all")
        canvas.create_rectangle(
            0,
            0,
            width,
            total_height,
            fill=COLORS["surface"],
            outline="",
            tags="calendar_base",
        )

        for index, day in enumerate(days):
            x0 = left + index * column_width
            x1 = x0 + column_width
            is_weekend = index >= 5
            is_today = day == date.today()
            if is_weekend:
                canvas.create_rectangle(
                    x0,
                    header_top,
                    x1,
                    total_height,
                    fill="#141b2e",
                    outline="",
                )
            if is_today:
                canvas.create_rectangle(
                    x0 + 3,
                    header_top,
                    x1 - 3,
                    header_top + header_height - 3,
                    fill="#222044",
                    outline="#5145b9",
                    width=1,
                )
            canvas.create_text(
                (x0 + x1) / 2,
                header_top + 17,
                text=WEEKDAY_NAMES[index],
                fill=COLORS["muted"] if not is_today else COLORS["accent_light"],
                font=(FONT, 9, "bold"),
            )
            if is_today:
                self._draw_calendar_today_badge(
                    canvas,
                    (x0 + x1) / 2,
                    header_top + 46,
                    str(day.day),
                )
            else:
                canvas.create_text(
                    (x0 + x1) / 2,
                    header_top + 46,
                    text=str(day.day),
                    fill=COLORS["text"],
                    font=(FONT, 18, "bold"),
                )
            canvas.create_line(
                x1,
                header_top,
                x1,
                total_height,
                fill="#252d42",
                width=1,
            )

        canvas.create_text(
            19,
            event_header_top + 13,
            text="FECHAS",
            anchor="w",
            fill=COLORS["muted"],
            font=(FONT, 8, "bold"),
        )
        canvas.create_line(
            left,
            event_header_top,
            right,
            event_header_top,
            fill="#343b52",
            width=1,
        )
        canvas.create_line(
            left,
            grid_top - 8,
            right,
            grid_top - 8,
            fill="#343b52",
            width=1,
        )
        self._draw_week_event_chips(
            canvas,
            days,
            left,
            column_width,
            event_area_top,
            event_row_height,
        )

        for hour in range(first_hour, last_hour + 1):
            y = grid_top + (hour - first_hour) * hour_height
            canvas.create_text(
                19,
                y,
                text=f"{hour:02d}:00",
                anchor="w",
                fill="#8c98b3",
                font=(FONT, 9),
            )
            canvas.create_line(
                left,
                y,
                right,
                y,
                fill="#252d42" if hour != first_hour else "#343b52",
                width=1,
                dash=(2, 4) if hour % 2 else (),
            )
        canvas.create_text(
            left + 14,
            total_height - 17,
            text="Los eventos se muestran por fecha; no incluyen horario.",
            anchor="w",
            fill="#8490aa",
            font=(FONT, 9),
        )
        canvas.configure(scrollregion=(0, 0, width, total_height))
        self._draw_now_line(canvas, left, right, grid_top, first_hour, hour_height)
        self._schedule_calendar_pulse()
        if direction:
            self._animate_calendar_header(canvas, direction, left, header_top, right)

    def _draw_calendar_today_badge(self, canvas, x, y, label):
        radius = 17
        canvas.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            fill=COLORS["accent"],
            outline=COLORS["accent_light"],
            width=2,
            tags="today_badge",
        )
        canvas.create_text(
            x,
            y,
            text=label,
            fill="white",
            font=(FONT, 11, "bold"),
            tags="today_badge",
        )

    def _draw_now_line(self, canvas, left, right, grid_top, first_hour, hour_height):
        now = datetime.now()
        if now.date() not in (
            self.calendar_week_start + timedelta(days=index) for index in range(7)
        ):
            return
        minutes = now.hour * 60 + now.minute - first_hour * 60
        y = grid_top + minutes / 60 * hour_height
        if not grid_top <= y <= grid_top + (20 - first_hour) * hour_height:
            return
        day_offset = now.weekday()
        x = left + day_offset * (right - left) / 7
        pulse = getattr(self, "_calendar_pulse_phase", 0)
        radius = 5 + pulse % 3
        canvas.create_oval(
            x - radius - 4,
            y - radius - 4,
            x + radius + 4,
            y + radius + 4,
            fill="#3a263c",
            outline="",
            tags="now_indicator",
        )
        
        canvas.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            fill=("#ff8b9a", COLORS["red"], "#e65d86")[pulse % 3],
            outline="#ffd0d7",
            width=1,
            tags="now_indicator",
        )
        canvas.create_line(
            x,
            y,
            right,
            y,
            fill=COLORS["red"],
            width=2,
            tags="now_indicator",
        )

    def _schedule_calendar_pulse(self):
        if self._calendar_pulse_after_id:
            self.root.after_cancel(self._calendar_pulse_after_id)
            self._calendar_pulse_after_id = None
        today = date.today()
        if not self.calendar_week_start <= today < self.calendar_week_start + timedelta(days=7):
            return

        def pulse():
            if not hasattr(self, "calendar_canvas") or not self.calendar_canvas.winfo_exists():
                return
            self._calendar_pulse_phase = (self._calendar_pulse_phase + 1) % 6
            self.calendar_canvas.delete("now_indicator")
            width = max(self.calendar_canvas.winfo_width(), 900)
            left = 78
            right = width - 14
            grid_top = 18 + 68 + 28 + max(
                66,
                max(1, len(getattr(self, "calendar_events", []))) * 38 + 12,
            ) + 8
            self._draw_now_line(self.calendar_canvas, left, right, grid_top, 8, 54)
            self._calendar_pulse_after_id = self.root.after(520, pulse)

        self._calendar_pulse_after_id = self.root.after(520, pulse)

    def _draw_week_event_chips(
        self,
        canvas,
        days,
        left,
        column_width,
        top,
        row_height,
    ):
        events = getattr(self, "calendar_events", [])
        if not events:
            canvas.create_text(
                left + 14,
                top + 23,
                text="Una semana despejada. Un buen momento para planificar con calma.",
                anchor="w",
                fill="#9aa6bf",
                font=(FONT, 10),
                tags="calendar_empty",
            )
            return
        for index, event in enumerate(events):
            try:
                start = date.fromisoformat(event["fecha_inicio"])
                end = date.fromisoformat(event["fecha_fin"])
            except (KeyError, ValueError):
                continue
            first_index = max(0, (start - days[0]).days)
            last_index = min(6, (end - days[0]).days)
            if first_index > 6 or last_index < 0:
                continue
            x0 = left + first_index * column_width + 5
            x1 = left + (last_index + 1) * column_width - 5
            y0 = top + index * row_height + 4
            y1 = y0 + row_height - 6
            fill, accent, border = EVENT_STYLES.get(
                event.get("categoria"),
                (COLORS["surface_light"], COLORS["accent_light"], COLORS["border"]),
            )
            tag = f"calendar_event_{index}"
            self._canvas_round_rect(
                canvas,
                x0,
                y0,
                x1,
                y1,
                12,
                fill,
                border,
                tags=(tag, "calendar_event", f"{tag}_bg"),
            )
            canvas.create_rectangle(
                x0 + 1,
                y0 + 7,
                x0 + 4,
                y1 - 7,
                fill=accent,
                outline="",
                tags=(tag, "calendar_event"),
            )
            label = event.get("resumen") or "Evento"
            font = (FONT, 9, "bold")
            available = max(80, x1 - x0 - 22)
            max_chars = max(12, int(available / 7))
            if len(label) > max_chars:
                label = label[: max_chars - 1].rstrip() + "…"
            canvas.create_text(
                x0 + 12,
                y0 + 7,
                text=label,
                anchor="nw",
                fill="#f5efff",
                font=font,
                tags=(tag, "calendar_event"),
            )
            canvas.create_text(
                x0 + 12,
                y0 + 22,
                text=(
                    "Personal"
                    if event.get("origen") == "personal"
                    else self._format_calendar_category(event.get("categoria", ""))
                ),
                anchor="nw",
                fill="#d0c8e8",
                font=(FONT, 8),
                tags=(tag, "calendar_event"),
            )
            canvas.tag_bind(
                tag,
                "<Button-1>",
                lambda _event, selected=event: self._show_calendar_event(selected),
            )
            canvas.tag_bind(
                tag,
                "<Enter>",
                lambda _event, selected_tag=tag, hover=accent: self._highlight_calendar_event(
                    selected_tag,
                    hover,
                ),
            )
            canvas.tag_bind(
                tag,
                "<Leave>",
                lambda _event, selected_tag=tag, base=fill, edge=border: self._restore_calendar_event(
                    selected_tag,
                    base,
                    edge,
                ),
            )
            self._animate_calendar_event(
                canvas,
                tag,
                y0,
                y1,
                fill,
                direction=getattr(self, "_calendar_transition_direction", -1),
            )

    def _schedule_calendar_animation(self, callback, delay):
        after_id = None

        def run():
            if after_id in self._calendar_animation_ids:
                self._calendar_animation_ids.remove(after_id)
            callback()

        after_id = self.root.after(delay, run)
        self._calendar_animation_ids.append(after_id)
        return after_id

    def _canvas_round_rect(self, canvas, x0, y0, x1, y1, radius, fill, outline, tags=()):
        radius = min(radius, (x1 - x0) / 2, (y1 - y0) / 2)
        points = []
        for cx, cy, start_angle in (
            (x1 - radius, y0 + radius, -90),
            (x1 - radius, y1 - radius, 0),
            (x0 + radius, y1 - radius, 90),
            (x0 + radius, y0 + radius, 180),
        ):
            for step in range(13):
                angle = math.radians(start_angle + step * 7.5)
                points.extend(
                    (
                        cx + radius * math.cos(angle),
                        cy + radius * math.sin(angle),
                    )
                )
        return canvas.create_polygon(
            *points,
            smooth=True,
            splinesteps=20,
            fill=fill,
            outline=outline,
            width=1,
            tags=tags,
        )

    def _format_calendar_category(self, category):
        names = {
            "evaluation_week": "Semana de evaluaciones",
            "wellbeing_activity": "Bienestar y pausa",
            "period_start": "Inicio de período",
            "period_end": "Cierre de período",
            "university_activity": "Actividad universitaria",
        }
        return names.get(category, category.replace("_", " ").title())

    def _highlight_calendar_event(self, tag, accent):
        self.calendar_canvas.itemconfigure(f"{tag}_bg", outline=accent, width=2)
        self.calendar_canvas.configure(cursor="hand2")

    def _restore_calendar_event(self, tag, _fill, border):
        self.calendar_canvas.itemconfigure(f"{tag}_bg", outline=border, width=1)
        self.calendar_canvas.configure(cursor="arrow")

    def _animate_calendar_event(self, canvas, tag, y0, y1, fill, direction):
        start_y = y0 + 34
        start_x = -direction * 22
        canvas.move(tag, start_x, start_y - y0)
        background_tag = f"{tag}_bg"
        initial_fill = _mix_color(fill, COLORS["surface"], 0.76)
        initial_outline = _mix_color(fill, COLORS["surface"], 0.55)
        canvas.itemconfigure(
            background_tag,
            fill=initial_fill,
            outline=initial_outline,
        )

        def step(index):
            if not canvas.winfo_exists():
                return
            progress = min(1.0, index / 16)
            eased = (1 - math.cos(math.pi * progress)) / 2
            previous = (1 - math.cos(math.pi * max(0, progress - 1 / 16))) / 2
            canvas.move(
                tag,
                -start_x * (eased - previous),
                -(start_y - y0) * (eased - previous),
            )
            canvas.itemconfigure(
                background_tag,
                fill=_mix_color(initial_fill, fill, eased),
                outline=_mix_color(initial_outline, fill, eased),
            )
            if index < 16:
                self._schedule_calendar_animation(
                    lambda: step(index + 1),
                    18,
                )

        self._schedule_calendar_animation(lambda: step(1), 18)

    def _animate_calendar_header(self, canvas, direction, left, top, right):
        del left, top, right
        canvas.move("calendar_event", -direction * 32, 0)

        def settle(index, previous=0.0):
            if not canvas.winfo_exists():
                return
            progress = min(1.0, index / 14)
            eased = (1 - math.cos(math.pi * progress)) / 2
            canvas.move("calendar_event", direction * 32 * (eased - previous), 0)
            if index < 14:
                self._schedule_calendar_animation(
                    lambda: settle(index + 1, eased),
                    16,
                )

        self._schedule_calendar_animation(lambda: settle(1), 16)

    def _show_calendar_event(self, event):
        dialog = tk.Toplevel(self.root)
        origen = event.get("origen", "academico")
        nombre_calendario = "Personal" if origen == "personal" else "Académico"
        dialog.title(event.get("resumen", "Evento"))
        dialog.configure(bg=COLORS["background"])
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("560x340")
        dialog.resizable(False, False)
        panel = self._card(
            dialog,
            radius=28,
            bg="#17213b",
            gradient=("#17213b", "#17213b", "#25204c"),
        )
        panel.pack(fill="both", expand=True, padx=14, pady=14)
        category = event.get("categoria", "")
        _, accent, _ = EVENT_STYLES.get(
            category,
            (COLORS["surface_light"], COLORS["accent_light"], COLORS["border"]),
        )
        self._label(
            panel,
            (
                "PERSONAL"
                if origen == "personal"
                else self._format_calendar_category(category).upper()
            ),
            size=9,
            color=accent,
            weight="bold",
            bg="#17213b",
        ).pack(anchor="w", padx=24, pady=(23, 7))
        self._label(
            panel,
            event.get("resumen", "Evento"),
            size=20,
            weight="bold",
            bg="#17213b",
            wraplength=470,
            justify="left",
        ).pack(anchor="w", padx=24)
        start = date.fromisoformat(event["fecha_inicio"])
        end = date.fromisoformat(event["fecha_fin"])
        dates = start.strftime("%d/%m/%Y")
        if end != start:
            dates += f"  —  {end.strftime('%d/%m/%Y')}"
        self._label(
            panel,
            f"◷   {dates}",
            size=12,
            color=COLORS["muted"],
            bg="#17213b",
        ).pack(anchor="w", padx=24, pady=(17, 4))
        if origen == "personal":
            descripcion = event.get("descripcion")
            detalle = f"Descripción: {descripcion}" if descripcion else "Evento personal"
        else:
            district = event.get("distrito_id") or "ALL"
            detalle = f"Ubicación: {district.replace('DIST_', 'Distrito ').title()}"
        self._label(
            panel,
            detalle,
            size=9,
            color=COLORS["muted"],
            bg="#17213b",
            wraplength=470,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(14, 14))
        self._label(
            panel,
            f"Calendario: {nombre_calendario}",
            size=9,
            color=COLORS["muted"],
            bg="#17213b",
        ).pack(anchor="w", padx=24, pady=(0, 14))
        self._button(panel, "Entendido", dialog.destroy, primary=True).pack(
            anchor="e",
            padx=24,
            pady=(0, 20),
        )
