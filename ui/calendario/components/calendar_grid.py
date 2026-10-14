"""Dibujo de la cuadrícula semanal y sus animaciones."""

import math
from datetime import date, datetime, time, timedelta

from ...tema import COLORS, FONT, WEEKDAY_NAMES, estilo_evento, humanizar_etiqueta
from ...widgets import mezclar_color


class CalendarGrid:
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
        all_day_events = [
            event
            for event in getattr(self, "calendar_events", [])
            if not event.get("hora_inicio")
        ]
        event_rows = max(1, len(all_day_events))
        event_row_height = 38
        event_area_height = max(66, event_rows * event_row_height + 12)
        grid_top = event_area_top + event_area_height + 8
        hour_height = 54
        timed_events = [
            event
            for event in getattr(self, "calendar_events", [])
            if event.get("hora_inicio") and event.get("hora_fin")
        ]
        first_hour, last_hour = 8, 20
        for event in timed_events:
            try:
                start_hour, _ = map(
                    int, event["hora_inicio"].split(":")
                )
                end_hour, end_minute = map(int, event["hora_fin"].split(":"))
                start_day = date.fromisoformat(event["fecha_inicio"])
                end_day = date.fromisoformat(event["fecha_fin"])
            except (KeyError, TypeError, ValueError):
                continue
            if start_day != end_day:
                first_hour, last_hour = 0, 24
                continue
            first_hour = min(first_hour, start_hour)
            last_hour = max(
                last_hour,
                end_hour + bool(end_minute),
            )
        self._calendar_first_hour = first_hour
        self._calendar_last_hour = last_hour
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
            text="Los eventos con hora ocupan su duración en la cuadrícula.",
            anchor="w",
            fill="#8490aa",
            font=(FONT, 9),
        )
        canvas.configure(scrollregion=(0, 0, width, total_height))
        self._draw_timed_events(
            canvas,
            days,
            left,
            column_width,
            grid_top,
            first_hour,
            last_hour,
            hour_height,
        )
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
        last_hour = getattr(self, "_calendar_last_hour", 20)
        if not grid_top <= y <= grid_top + (last_hour - first_hour) * hour_height:
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
                max(
                    1,
                    sum(
                        not event.get("hora_inicio")
                        for event in getattr(self, "calendar_events", [])
                    ),
                )
                * 38
                + 12,
            ) + 8
            self._draw_now_line(
                self.calendar_canvas,
                left,
                right,
                grid_top,
                getattr(self, "_calendar_first_hour", 8),
                54,
            )
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
        events = [
            event
            for event in getattr(self, "calendar_events", [])
            if not event.get("hora_inicio")
        ]
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
            fill, accent, border = estilo_evento(event.get("categoria"))
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
                    humanizar_etiqueta(event.get("origen", ""))
                    if event.get("editable")
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

    def _draw_timed_events(
        self,
        canvas,
        days,
        left,
        column_width,
        grid_top,
        first_hour,
        last_hour,
        hour_height,
    ):
        events = [
            event
            for event in getattr(self, "calendar_events", [])
            if event.get("hora_inicio") and event.get("hora_fin")
        ]
        visible_start = time(first_hour)
        for day_index, day in enumerate(days):
            day_start = datetime.combine(day, time.min)
            day_end = day_start + timedelta(days=1)
            segments = []
            for event_index, event in enumerate(events):
                try:
                    start = datetime.combine(
                        date.fromisoformat(event["fecha_inicio"]),
                        time.fromisoformat(event["hora_inicio"]),
                    )
                    end = datetime.combine(
                        date.fromisoformat(event["fecha_fin"]),
                        time.fromisoformat(event["hora_fin"]),
                    )
                except (KeyError, ValueError):
                    continue
                segment_start = max(start, day_start, datetime.combine(day, visible_start))
                segment_end = min(
                    end,
                    day_end,
                    datetime.combine(day, visible_start)
                    + timedelta(hours=last_hour - first_hour),
                )
                if segment_end > segment_start:
                    segments.append((segment_start, segment_end, event_index, event))

            segments.sort(key=lambda segment: segment[0])
            lane_ends = []
            assigned_segments = []
            for segment_start, segment_end, event_index, event in segments:
                lane = next(
                    (
                        index
                        for index, lane_end in enumerate(lane_ends)
                        if lane_end <= segment_start
                    ),
                    len(lane_ends),
                )
                if lane == len(lane_ends):
                    lane_ends.append(segment_end)
                else:
                    lane_ends[lane] = segment_end
                assigned_segments.append(
                    (segment_start, segment_end, event_index, event, lane)
                )

            lane_count = max(1, len(lane_ends))
            for segment_start, segment_end, event_index, event, lane in assigned_segments:
                day_x = left + day_index * column_width
                lane_width = (column_width - 8) / lane_count
                x0 = day_x + 4 + lane * lane_width
                x1 = x0 + lane_width - 3
                y0 = grid_top + (
                    (segment_start.hour + segment_start.minute / 60) - first_hour
                ) * hour_height
                y1 = grid_top + (
                    (segment_end.hour + segment_end.minute / 60) - first_hour
                ) * hour_height
                if segment_end.date() > day:
                    y1 = grid_top + (last_hour - first_hour) * hour_height
                if y1 <= y0:
                    continue

                fill, accent, border = estilo_evento(event.get("categoria"))
                tag = f"calendar_timed_event_{day_index}_{event_index}"
                self._canvas_round_rect(
                    canvas,
                    x0,
                    y0 + 1,
                    x1,
                    y1 - 1,
                    7,
                    fill,
                    border,
                    tags=(tag, "calendar_event", f"{tag}_bg"),
                )
                canvas.create_rectangle(
                    x0 + 1,
                    y0 + 5,
                    x0 + 4,
                    max(y0 + 6, y1 - 5),
                    fill=accent,
                    outline="",
                    tags=(tag, "calendar_event"),
                )
                if y1 - y0 >= 25:
                    duration_minutes = int((segment_end - segment_start).total_seconds() // 60)
                    duration_hours, remainder = divmod(duration_minutes, 60)
                    duration_label = (
                        f"{duration_hours} h {remainder} min"
                        if remainder
                        else f"{duration_hours} h"
                    )
                    canvas.create_text(
                        x0 + 8,
                        y0 + 4,
                        text=(
                            f"{event.get('resumen', 'Evento')} "
                            f"({segment_start:%H:%M}–{segment_end:%H:%M}, "
                            f"{duration_label})"
                        ),
                        anchor="nw",
                        fill="#f5efff",
                        font=(FONT, 8, "bold"),
                        width=max(1, x1 - x0 - 12),
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
                    lambda _event: canvas.configure(cursor="hand2"),
                )
                canvas.tag_bind(
                    tag,
                    "<Leave>",
                    lambda _event: canvas.configure(cursor="arrow"),
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
        return humanizar_etiqueta(category)

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
        initial_fill = mezclar_color(fill, COLORS["surface"], 0.76)
        initial_outline = mezclar_color(fill, COLORS["surface"], 0.55)
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
                fill=mezclar_color(initial_fill, fill, eased),
                outline=mezclar_color(initial_outline, fill, eased),
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
