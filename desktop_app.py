"""Interfaz de escritorio para Aethera, construida con Tkinter."""

import queue
import math
import re
import threading
import time
import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import ttk

from ChatSession import ChatSession
from tools.calendario_academico import calendario_academico
from tools.evaluar_carga_academica import evaluar_riesgo_sobrecarga
from tools.servicios_ayuda import buscar_servicios_ayuda


COLORS = {
    "background": "#080b18",
    "sidebar": "#0c1224",
    "surface": "#11182b",
    "surface_light": "#18223b",
    "border": "#293551",
    "text": "#f5f7ff",
    "muted": "#aab5cf",
    "accent": "#6558f5",
    "accent_light": "#8b83ff",
    "green": "#35d5a0",
    "yellow": "#f6c85f",
    "red": "#ff7885",
    "teal": "#34cbb3",
    "purple_deep": "#37256f",
}

FONT = "Segoe UI"
SERVICE_CATEGORIES = {
    "Presión académica": "academic_pressure",
    "Apoyo social": "social_support",
    "Orientación vocacional": "career_concern",
    "Sueño y rutinas": "sleep_and_routine",
    "Orientación sobre servicios": "service_navigation",
}
SERVICE_TYPES = {
    "counseling": "Orientación",
    "peer_support": "Acompañamiento entre pares",
    "career_guidance": "Orientación vocacional",
}
SERVICE_DISTRICTS = {
    "Todos los distritos": None,
    "Distrito Gaia": "DIST_GAIA",
    "Distrito Horizon": "DIST_HORIZON",
    "Distrito Nebula": "DIST_NEBULA",
    "Distrito Quantum": "DIST_QUANTUM",
    "Distrito Vector": "DIST_VECTOR",
}
SERVICE_CHANNELS = {
    "in_person": "Presencial",
    "digital": "En línea",
    "phone": "Teléfono",
}
INLINE_MARKDOWN = re.compile(
    r"(\*\*.+?\*\*|__.+?__|(?<!\*)\*(?!\*).+?(?<!\*)\*(?!\*)|`[^`\n]+`|~~.+?~~)"
)
EMOJI_CHAR = re.compile(r"[\U0001F000-\U0001FAFF\u2600-\u27BF]")
WEEKDAYS = {
    "Mon-Fri": "Lunes a viernes",
    "Mon-Sat": "Lunes a sábado",
    "Mon-Sun": "Todos los días",
}
WEEKDAY_NAMES = ("LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM")
MONTH_NAMES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
EVENT_STYLES = {
    "evaluation_week": ("#593039", "#ff94a1", "#42252e"),
    "wellbeing_activity": ("#185347", "#71e2c5", "#123e39"),
    "period_start": ("#283f69", "#9dc3ff", "#1e3151"),
    "period_end": ("#56426c", "#d0a7ff", "#382a4a"),
    "university_activity": ("#4b476d", "#b9adff", "#302b4a"),
}


def _mix_color(start, end, amount):
    start_rgb = tuple(int(start[index:index + 2], 16) for index in (1, 3, 5))
    end_rgb = tuple(int(end[index:index + 2], 16) for index in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(
        round(first + (last - first) * amount)
        for first, last in zip(start_rgb, end_rgb)
    )


def _rounded_scanline(width, height, radius, y):
    inset = 0
    if y < radius:
        inset = radius - math.sqrt(max(0, radius * radius - (radius - y) ** 2))
    elif y > height - radius:
        distance = y - (height - radius)
        inset = radius - math.sqrt(max(0, radius * radius - distance ** 2))
    return inset, width - inset


class RoundedFrame(tk.Frame):
    """Marco con fondo redondeado dibujado en un canvas de Tk."""

    def __init__(self, parent, bg, border, radius=20, gradient=None, **kwargs):
        parent_bg = parent.cget("bg")
        super().__init__(parent, bg=parent_bg, **kwargs)
        self.fill = bg
        self.border = border
        self.radius = radius
        self.gradient = gradient
        self.canvas = tk.Canvas(self, bg=parent_bg, highlightthickness=0, bd=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.bind("<Configure>", self._draw)

    def _draw(self, _event=None):
        width = self.winfo_width()
        height = self.winfo_height()
        if width < 2 or height < 2:
            return
        radius = min(self.radius, width // 2, height // 2)
        self.canvas.delete("rounded")
        points = []
        for center_x, center_y, start in (
            (width - radius, radius, -90),
            (width - radius, height - radius, 0),
            (radius, height - radius, 90),
            (radius, radius, 180),
        ):
            for step in range(13):
                angle = (start + step * 90 / 12) * math.pi / 180
                points.extend(
                    (
                        center_x + radius * math.cos(angle),
                        center_y + radius * math.sin(angle),
                    )
                )
        if self.gradient:
            stops = self.gradient
            rows = min(height, 120)
            for row in range(rows):
                y = row * height / rows
                position = row / max(1, rows - 1)
                color = _gradient_color(stops, position)
                left, right = _rounded_scanline(width, height, radius, y)
                self.canvas.create_line(
                    left,
                    y,
                    right,
                    y,
                    fill=color,
                    width=height / rows + 1,
                    tags="rounded",
                )
            self.canvas.create_polygon(
                *points,
                smooth=True,
                splinesteps=24,
                fill="",
                outline=self.border,
                width=1,
                tags="rounded",
            )
            return
        self.canvas.create_polygon(
            *points,
            smooth=True,
            splinesteps=24,
            fill=self.fill,
            outline=self.border,
            width=1,
            tags="rounded",
        )


def _gradient_color(stops, position):
    if len(stops) == 1:
        return stops[0]
    segment = position * (len(stops) - 1)
    index = min(int(segment), len(stops) - 2)
    return _mix_color(stops[index], stops[index + 1], segment - index)


class RoundedButton(tk.Canvas):
    """Botón de estilo minimalista con estados hover y presionado."""

    def __init__(self, parent, text, command, primary=False):
        self.primary = primary
        self.command = command
        self.text = text
        self.disabled = False
        self.hovered = False
        self.pressed = False
        self.focused = False
        self.bg_normal = COLORS["accent"] if primary else COLORS["surface_light"]
        self.bg_hover = COLORS["accent_light"] if primary else "#253252"
        self.gradient = (
            ("#7666ff", "#634ff0", "#3d82ed")
            if primary
            else None
        )
        width = max(116, len(text) * 8 + 40)
        super().__init__(
            parent,
            width=width,
            height=46,
            bg=getattr(parent, "fill", parent.cget("bg")),
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            takefocus=True,
        )
        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<FocusIn>", self._on_focus)
        self.bind("<FocusOut>", self._on_blur)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Return>", self._invoke)
        self.bind("<space>", self._invoke)

    def _draw(self, _event=None):
        self.delete("button")
        width = self.winfo_width()
        height = self.winfo_height()
        if width < 2 or height < 2:
            return
        radius = min(12, height // 2)
        points = []
        for center_x, center_y, start in (
            (width - radius, radius, -90),
            (width - radius, height - radius, 0),
            (radius, height - radius, 90),
            (radius, radius, 180),
        ):
            for step in range(13):
                angle = math.radians(start + step * 7.5)
                points.extend(
                    (
                        center_x + radius * math.cos(angle),
                        center_y + radius * math.sin(angle),
                    )
                )
        fill = self.bg_normal
        if self.disabled:
            fill = COLORS["border"]
        elif self.pressed:
            fill = COLORS["accent"]
        elif self.hovered:
            fill = self.bg_hover
        if self.gradient and not (self.disabled or self.pressed or self.hovered):
            for row in range(height):
                left, right = _rounded_scanline(width, height, radius, row)
                self.create_line(
                    left,
                    row,
                    right,
                    row,
                    fill=_gradient_color(self.gradient, row / max(1, height - 1)),
                    tags="button",
                )
        else:
            self.create_polygon(
                *points,
                smooth=True,
                splinesteps=20,
                fill=fill,
                outline=COLORS["accent_light"] if self.focused else fill,
                width=2 if self.focused else 1,
                tags="button",
            )
        if self.focused:
            self.create_polygon(
                *points,
                smooth=True,
                splinesteps=20,
                fill="",
                outline=COLORS["accent_light"],
                width=2,
                tags="button",
            )
        self.create_text(
            width / 2,
            height / 2,
            text=self.text,
            fill="#8792ad" if self.disabled else "white",
            font=(FONT, 10, "bold"),
            tags="button",
        )

    def _on_enter(self, _event):
        self.hovered = True
        self._draw()

    def _on_leave(self, _event):
        self.hovered = False
        self.pressed = False
        self._draw()

    def _on_focus(self, _event):
        self.focused = True
        self._draw()

    def _on_blur(self, _event):
        self.focused = False
        self._draw()

    def _on_press(self, _event):
        if not self.disabled:
            self.pressed = True
            self._draw()

    def _on_release(self, event):
        was_pressed = self.pressed
        self.pressed = False
        self._draw()
        inside = 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height()
        if was_pressed and inside and not self.disabled:
            self.command()

    def _invoke(self, _event=None):
        if not self.disabled:
            self.command()
        return "break"

    def configure(self, cnf=None, **kwargs):
        state = kwargs.pop("state", None)
        if state is not None:
            self.disabled = state == "disabled"
            super().configure(cursor="arrow" if self.disabled else "hand2")
            self._draw()
        if kwargs or cnf:
            super().configure(cnf, **kwargs)


class AnimatedDropdown(tk.Frame):
    """Selector desplegable propio para evitar el menú nativo del sistema."""

    def __init__(self, parent, textvariable, values, width=280, on_select=None):
        super().__init__(parent, bg=parent.cget("bg"), width=width, height=48)
        self.pack_propagate(False)
        self.textvariable = textvariable
        self.values = tuple(values)
        self.on_select = on_select
        self.is_open = False
        self.popup = None
        self.animation_id = None
        self._outside_binding = None
        self._selection_animation_id = None
        self._hover_animations = {}
        self._hover_starts = {}
        self.selection_color = self._option_color(textvariable.get())
        self.canvas = tk.Canvas(
            self,
            width=width,
            height=48,
            bg=parent.cget("bg"),
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._draw)
        self.canvas.bind("<Button-1>", self.toggle)
        self.canvas.bind("<Enter>", self._on_hover)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<Return>", self.toggle)
        self.canvas.bind("<space>", self.toggle)
        self.canvas.configure(takefocus=True)
        self.textvariable.trace_add("write", self._draw)

    def _draw(self, *_args):
        if not self.winfo_exists():
            return
        self.canvas.delete("selector")
        width = max(2, self.canvas.winfo_width())
        height = max(2, self.canvas.winfo_height())
        radius = min(15, height // 2)
        colors = ("#222b45", "#1b2238", "#252044") if not self.is_open else (
            "#312b60",
            "#24294b",
            "#27354e",
        )
        for y in range(height):
            left, right = _rounded_scanline(width, height, radius, y)
            self.canvas.create_line(
                left,
                y,
                right,
                y,
                fill=_gradient_color(colors, y / max(1, height - 1)),
                tags="selector",
            )
        self.canvas.create_arc(
            1,
            1,
            height - 1,
            height - 1,
            start=90,
            extent=180,
            style="arc",
            outline="#544d8a" if self.is_open else COLORS["border"],
            width=1,
            tags="selector",
        )
        self.canvas.create_arc(
            width - height + 1,
            1,
            width - 1,
            height - 1,
            start=270,
            extent=180,
            style="arc",
            outline="#544d8a" if self.is_open else COLORS["border"],
            width=1,
            tags="selector",
        )
        self.canvas.create_line(
            radius,
            1,
            width - radius,
            1,
            fill="#544d8a" if self.is_open else COLORS["border"],
            tags="selector",
        )
        self.canvas.create_line(
            radius,
            height - 1,
            width - radius,
            height - 1,
            fill="#544d8a" if self.is_open else COLORS["border"],
            tags="selector",
        )
        selected = self.textvariable.get()
        accent = self._option_color(selected)
        accent = self.selection_color or accent
        glow = 4 if self.is_open else 0
        self.canvas.create_oval(
            11 - glow,
            height / 2 - 9 - glow,
            29 + glow,
            height / 2 + 9 + glow,
            outline="#4b427e" if self.is_open else "",
            width=1 if self.is_open else 0,
            tags="selector",
        )
        self.canvas.create_oval(
            15,
            height / 2 - 5,
            25,
            height / 2 + 5,
            fill=accent,
            outline="",
            tags="selector",
        )
        self.canvas.create_text(
            36,
            height / 2,
            text=selected,
            anchor="w",
            fill=COLORS["text"],
            font=(FONT, 10, "bold"),
            tags="selector",
        )
        center_x = width - 20
        center_y = height / 2
        direction = -1 if self.is_open else 1
        self.canvas.create_line(
            center_x - 4,
            center_y - direction * 2,
            center_x,
            center_y + direction * 2,
            fill=COLORS["accent_light"],
            width=2,
            capstyle="round",
            tags="selector",
        )
        self.canvas.create_line(
            center_x,
            center_y + direction * 2,
            center_x + 4,
            center_y - direction * 2,
            fill=COLORS["accent_light"],
            width=2,
            capstyle="round",
            tags="selector",
        )

    def _option_color(self, value):
        label = value.casefold()
        if "evalu" in label:
            return "#ff8799"
        if "bienestar" in label:
            return "#54d9bb"
        if "período" in label or "periodo" in label:
            return "#83aaff"
        if "activ" in label:
            return "#c196ff"
        if "gaia" in label:
            return "#48d3b7"
        if "horizon" in label:
            return "#61b9ff"
        if "nebula" in label:
            return "#b493ff"
        if "quantum" in label:
            return "#ff94bf"
        if "vector" in label:
            return "#ffbd71"
        if "apoyo" in label:
            return "#56d7be"
        if "sueño" in label or "rutinas" in label:
            return "#82b5ff"
        if "vocacional" in label:
            return "#ffc26c"
        return COLORS["accent_light"]

    def _on_hover(self, _event=None):
        if not self.is_open:
            self.canvas.configure(cursor="hand2")
        self._draw()

    def _on_leave(self, _event=None):
        self.canvas.configure(cursor="hand2")
        self._draw()

    def toggle(self, _event=None):
        if self.is_open:
            self.close()
        else:
            self.open()
        return "break"

    def open(self):
        if self.is_open or not self.values:
            return
        self.is_open = True
        self._draw()
        self.popup = tk.Toplevel(self)
        self.popup.withdraw()
        self.popup.overrideredirect(True)
        self.popup.configure(bg="#403a65")
        self.popup.attributes("-topmost", True)
        self.popup.bind("<Escape>", lambda _event: self.close())
        self.popup.bind("<Up>", lambda _event: self._move_active_option(-1))
        self.popup.bind("<Down>", lambda _event: self._move_active_option(1))
        self.popup.bind("<Return>", lambda _event: self._select_active_option())
        body = tk.Frame(
            self.popup,
            bg="#131a2d",
            highlightbackground="#484572",
            highlightthickness=1,
            bd=0,
        )
        body.pack(fill="both", expand=True, padx=1, pady=1)
        header = tk.Frame(body, bg="#131a2d")
        header.pack(fill="x", padx=9, pady=(8, 5))
        tk.Label(
            header,
            text="ELIGE UNA OPCIÓN",
            bg="#131a2d",
            fg="#8996b4",
            font=(FONT, 8, "bold"),
        ).pack(side="left")
        tk.Label(
            header,
            text=f"{len(self.values):02d}",
            bg="#282447",
            fg=COLORS["accent_light"],
            font=(FONT, 8, "bold"),
            padx=6,
            pady=2,
        ).pack(side="right")
        self.option_rows = []
        self._hover_animations = {}
        for index, value in enumerate(self.values):
            self._create_option(body, value, index)
        self.popup.update_idletasks()
        self.popup_width = max(self.winfo_width(), 270)
        self.popup_height = min(
            self.popup.winfo_reqheight(),
            self.winfo_screenheight() - 100,
        )
        self.popup_x = self.winfo_rootx()
        self.popup_y = self.winfo_rooty() + self.winfo_height() + 7
        if self.popup_y + self.popup_height > self.winfo_screenheight() - 12:
            self.popup_y = max(8, self.winfo_rooty() - self.popup_height - 7)
        if self.popup_x + self.popup_width > self.winfo_screenwidth() - 12:
            self.popup_x = self.winfo_screenwidth() - self.popup_width - 12
        self.popup.geometry(
            f"{self.popup_width}x1+{self.popup_x}+{self.popup_y}"
        )
        self.popup.deiconify()
        self.popup.lift()
        self.active_option_index = next(
            (
                index
                for index, value in enumerate(self.values)
                if value == self.textvariable.get()
            ),
            0,
        )
        self.popup.focus_force()
        self._animate_open(1)
        self._outside_binding = self.winfo_toplevel().bind_all(
            "<Button-1>",
            self._close_if_outside,
            add="+",
        )

    def _create_option(self, parent, value, index):
        accent = self._option_color(value)
        selected = value == self.textvariable.get()
        row = tk.Frame(
            parent,
            bg="#27264a" if selected else "#131a2d",
            height=42,
            cursor="hand2",
        )
        row.pack(fill="x", padx=7, pady=2)
        row.pack_propagate(False)
        stripe = tk.Frame(row, bg=accent, width=3)
        stripe.pack(side="left", fill="y", padx=(5, 10), pady=8)
        dot = tk.Canvas(
            row,
            width=17,
            height=17,
            bg=row.cget("bg"),
            highlightthickness=0,
            bd=0,
        )
        dot.pack(side="left", padx=(0, 8))
        dot.create_oval(2, 2, 15, 15, fill=accent, outline="")
        label = tk.Label(
            row,
            text=value,
            bg=row.cget("bg"),
            fg=COLORS["text"] if selected else "#c6cee2",
            font=(FONT, 10, "bold" if selected else "normal"),
            anchor="w",
        )
        label.pack(side="left", fill="x", expand=True)
        marker = tk.Label(
            row,
            text="✓" if selected else f"{index + 1:02d}",
            bg=row.cget("bg"),
            fg=accent if selected else "#727d98",
            font=(FONT, 9, "bold"),
            padx=10,
        )
        marker.pack(side="right")
        for widget in (row, stripe, dot, label, marker):
            widget.bind("<Enter>", lambda _event, item=row, color=accent: self._hover_option(item, color))
            widget.bind("<Leave>", lambda _event, item=row, chosen=selected: self._unhover_option(item, chosen))
            widget.bind("<Button-1>", lambda _event, selected_value=value: self.select(selected_value))
        self.option_rows.append(row)

    def _hover_option(self, row, accent):
        self._animate_option_color(row, "#353363", accent, 1)

    def _unhover_option(self, row, selected):
        base = "#27264a" if selected else "#131a2d"
        self._animate_option_color(row, base, COLORS["accent_light"], 1, restore=True)

    def _animate_option_color(self, row, target, accent, step, restore=False):
        if not row.winfo_exists():
            return
        old_job = self._hover_animations.get(str(row))
        if old_job:
            self.after_cancel(old_job)
        current = row.cget("bg")
        start = current if step == 1 else self._hover_starts.get(str(row), current)
        if step == 1:
            self._hover_starts[str(row)] = start
        progress = min(1.0, step / 9)
        eased = progress * progress * (3 - 2 * progress)
        color = _mix_color(start, target, eased)
        row.configure(
            bg=color,
            highlightbackground=accent,
            highlightthickness=0 if restore and step == 9 else 1,
        )
        for child in row.winfo_children():
            if isinstance(child, (tk.Label, tk.Canvas)):
                child.configure(bg=color)
        if step < 9:
            self._hover_animations[str(row)] = self.after(
                16,
                lambda: self._animate_option_color(
                    row,
                    target,
                    accent,
                    step + 1,
                    restore,
                ),
            )
        else:
            self._hover_animations.pop(str(row), None)
            self._hover_starts.pop(str(row), None)

    def _animate_open(self, step):
        if not self.popup or not self.popup.winfo_exists():
            return
        progress = min(1.0, step / 18)
        eased = 1 - (1 - progress) ** 4
        height = max(1, round(self.popup_height * eased))
        self.popup.geometry(
            f"{self.popup_width}x{height}+{self.popup_x}+{self.popup_y}"
        )
        if step < 18:
            self.animation_id = self.after(16, lambda: self._animate_open(step + 1))

    def select(self, value):
        old_color = self._option_color(self.textvariable.get())
        new_color = self._option_color(value)
        self.textvariable.set(value)
        self.selection_color = old_color
        self._draw()
        self._animate_selection(old_color, new_color, 1)
        callback = self.on_select
        self.close()
        if callback:
            self.after(30, lambda: callback(value))

    def _animate_selection(self, old_color, new_color, step):
        if not self.winfo_exists():
            return
        progress = min(1.0, step / 18)
        eased = 1 - (1 - progress) ** 3
        self.selection_color = _mix_color(old_color, new_color, eased)
        self._draw()
        if step < 18:
            self._selection_animation_id = self.after(
                22,
                lambda: self._animate_selection(old_color, new_color, step + 1),
            )

    def _move_active_option(self, offset):
        self.active_option_index = (
            self.active_option_index + offset
        ) % len(self.values)
        for index, row in enumerate(self.option_rows):
            self._unhover_option(row, index == self.active_option_index)
        self._hover_option(
            self.option_rows[self.active_option_index],
            self._option_color(self.values[self.active_option_index]),
        )
        return "break"

    def _select_active_option(self):
        self.select(self.values[self.active_option_index])
        return "break"

    def _close_if_outside(self, event):
        if not self.is_open or not self.popup:
            return
        clicked = str(event.widget)
        popup_path = str(self.popup)
        if clicked == str(self.canvas) or clicked.startswith(popup_path):
            return
        self.close()

    def close(self):
        if not self.is_open:
            return
        self.is_open = False
        if self.animation_id:
            self.after_cancel(self.animation_id)
            self.animation_id = None
        if self._outside_binding:
            self.winfo_toplevel()._unbind(
                ("bind", "all", "<Button-1>"),
                self._outside_binding,
            )
            self._outside_binding = None
        popup = self.popup
        self.popup = None
        self._draw()
        if popup and popup.winfo_exists():
            self._animate_close(popup, 1)

    def _animate_close(self, popup, step):
        if not popup.winfo_exists():
            return
        progress = min(1.0, step / 14)
        eased = progress * progress * (3 - 2 * progress)
        height = max(1, round(self.popup_height * (1 - eased)))
        popup.geometry(
            f"{self.popup_width}x{height}+{self.popup_x}+{self.popup_y}"
        )
        if step < 14:
            self.animation_id = self.after(
                16,
                lambda: self._animate_close(popup, step + 1),
            )
        else:
            popup.destroy()
            self.animation_id = None


class AetheraDesktopApp:
    def __init__(self, motor, historial, herramientas, guardar_historial):
        self.root = tk.Tk()
        self.root.title("Aethera | Acompañamiento académico")
        self.root.geometry("1560x980")
        self.root.minsize(1200, 780)
        self.root.configure(bg=COLORS["background"])
        self.event_queue = queue.Queue()
        self._scroll_animations = {}
        self._search_after_id = None
        self._scroll_targets = []
        self.calendar_week_start = date.today() - timedelta(days=date.today().weekday())
        self.calendar_category_var = None
        self._calendar_animation_ids = []
        self._calendar_pulse_after_id = None
        self._calendar_pulse_phase = 0
        self.root.bind_all("<MouseWheel>", self._handle_mousewheel)
        self.current_page = "Inicio"
        self.busy = False

        self.chat = ChatSession(
            motor,
            historial,
            herramientas,
            al_completar_turno=lambda usuario, respuesta: guardar_historial(
                usuario,
                respuesta,
                motor.modelo,
            ),
        )

        self._configure_styles()
        self._build_shell()
        self.show_page("Inicio")
        self.root.after(80, self._process_queue)

    def _configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "Aethera.TCombobox",
            fieldbackground=COLORS["surface_light"],
            background=COLORS["surface_light"],
            foreground=COLORS["text"],
            arrowcolor=COLORS["text"],
            bordercolor=COLORS["border"],
            lightcolor=COLORS["border"],
            darkcolor=COLORS["border"],
            padding=12,
        )
        style.map(
            "Aethera.TCombobox",
            fieldbackground=[("readonly", COLORS["surface_light"])],
            foreground=[("readonly", COLORS["text"])],
        )

    def _build_shell(self):
        self.sidebar = tk.Frame(self.root, bg=COLORS["sidebar"], width=276)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand = tk.Frame(self.sidebar, bg=COLORS["sidebar"])
        brand.pack(fill="x", padx=22, pady=(25, 30))
        tk.Label(
            brand,
            text="✦",
            bg=COLORS["accent"],
            fg="white",
            font=(FONT, 21, "bold"),
            width=2,
            height=1,
        ).pack(side="left", padx=(0, 11), ipady=5)
        title = tk.Frame(brand, bg=COLORS["sidebar"])
        title.pack(side="left")
        tk.Label(
            title,
            text="AETHERA",
            bg=COLORS["sidebar"],
            fg=COLORS["text"],
            font=(FONT, 16, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title,
            text="Tu espacio académico",
            bg=COLORS["sidebar"],
            fg=COLORS["muted"],
            font=(FONT, 10),
        ).pack(anchor="w", pady=(2, 0))

        tk.Label(
            self.sidebar,
            text="MENÚ PRINCIPAL",
            bg=COLORS["sidebar"],
            fg="#7381a4",
            font=(FONT, 9, "bold"),
        ).pack(anchor="w", padx=24, pady=(0, 10))

        self.nav_buttons = {}
        for page, icon in (
            ("Inicio", "⌂"),
            ("Asistente IA", "✧"),
            ("Calendario", "▦"),
            ("Carga académica", "▤"),
            ("Servicios de apoyo", "♡"),
        ):
            button = tk.Button(
                self.sidebar,
                text=f"  {icon}    {page}",
                anchor="w",
                command=lambda selected=page: self.show_page(selected),
                relief="flat",
                bd=0,
                padx=14,
                pady=12,
                bg=COLORS["sidebar"],
                fg=COLORS["muted"],
                activebackground=COLORS["surface_light"],
                activeforeground=COLORS["text"],
                font=(FONT, 11),
                cursor="hand2",
            )
            button.pack(fill="x", padx=12, pady=2)
            button.bind(
                "<Enter>",
                lambda _event, item=button, selected_page=page: (
                    item.configure(
                        bg=COLORS["accent"] if self.current_page == selected_page else COLORS["surface_light"],
                        fg=COLORS["text"],
                    )
                ),
            )
            button.bind(
                "<Leave>",
                lambda _event, item=button, selected_page=page: (
                    item.configure(
                        bg=COLORS["accent"] if self.current_page == selected_page else COLORS["sidebar"],
                        fg="white" if self.current_page == selected_page else COLORS["muted"],
                    )
                ),
            )
            self.nav_buttons[page] = button

        spacer = tk.Frame(self.sidebar, bg=COLORS["sidebar"])
        spacer.pack(fill="both", expand=True)
        wellbeing = self._card(
            self.sidebar,
            bg=COLORS["surface"],
            radius=22,
        )
        wellbeing.pack(fill="x", padx=16, pady=(0, 18))
        self._label(
            wellbeing,
            text="Un paso a la vez",
            size=11,
            weight="bold",
        ).pack(anchor="w", padx=16, pady=(14, 5))
        self._label(
            wellbeing,
            text="Organizarte también es cuidarte.",
            size=9,
            color=COLORS["muted"],
            wraplength=185,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 15))

        self.main = tk.Frame(self.root, bg=COLORS["background"])
        self.main.pack(side="left", fill="both", expand=True)
        self.header = tk.Frame(
            self.main,
            bg=COLORS["background"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        self.header.pack(fill="x")
        self.page_title = tk.Label(
            self.header,
            text="Inicio",
            bg=COLORS["background"],
            fg=COLORS["text"],
            font=(FONT, 19, "bold"),
        )
        self.page_title.pack(side="left", padx=30, pady=20)
        tk.Label(
            self.header,
            text="Acompañamiento académico personalizado",
            bg=COLORS["background"],
            fg=COLORS["muted"],
            font=(FONT, 10),
        ).pack(side="left", padx=(4, 0), pady=20)
        tk.Label(
            self.header,
            text="●  AETHERA",
            bg=COLORS["background"],
            fg=COLORS["green"],
            font=(FONT, 10, "bold"),
        ).pack(side="right", padx=30, pady=20)

        self.content = tk.Frame(self.main, bg=COLORS["background"])
        self.content.pack(fill="both", expand=True, padx=30, pady=24)

    def _card(self, parent, **kwargs):
        return RoundedFrame(
            parent,
            bg=kwargs.pop("bg", COLORS["surface"]),
            border=kwargs.pop("border", COLORS["border"]),
            radius=kwargs.pop("radius", 20),
            gradient=kwargs.pop("gradient", None),
            **kwargs,
        )

    def _label(self, parent, text, size=10, color=None, weight="normal", **kwargs):
        return tk.Label(
            parent,
            text=text,
            bg=kwargs.pop("bg", COLORS["surface"]),
            fg=color or COLORS["text"],
            font=(FONT, max(8, round(size * 1.16)), weight),
            **kwargs,
        )

    def _button(self, parent, text, command, primary=False):
        return RoundedButton(parent, text, command, primary=primary)

    def _animate_scroll_to_bottom(self, canvas):
        self._animate_scroll(canvas, 1.0, duration=340)

    def _animate_scroll(self, canvas, target, duration=340):
        key = str(canvas)
        animation = self._scroll_animations.get(key)
        if animation and abs(animation["target"] - target) < 0.001:
            return
        if animation and animation.get("after_id"):
            self.root.after_cancel(animation["after_id"])
        start = canvas.yview()[0] if animation is None else animation["current"]
        self._scroll_animations[key] = {
            "start": start,
            "target": target,
            "started": time.monotonic(),
            "duration": duration / 1000,
            "current": start,
            "after_id": None,
        }
        self._step_scroll(canvas, key)

    def _step_scroll(self, canvas, key):
        animation = self._scroll_animations.get(key)
        if animation is None or not canvas.winfo_exists():
            self._scroll_animations.pop(key, None)
            return
        elapsed = time.monotonic() - animation["started"]
        progress = min(1.0, elapsed / animation["duration"])
        eased = (1 - math.cos(math.pi * progress)) / 2
        current = animation["start"] + (
            animation["target"] - animation["start"]
        ) * eased
        animation["current"] = current
        canvas.yview_moveto(current)
        if progress < 1:
            animation["after_id"] = self.root.after(
                12,
                lambda: self._step_scroll(canvas, key),
            )
        else:
            self._scroll_animations.pop(key, None)

    def _on_mousewheel(self, canvas, event):
        delta = -1 if event.delta > 0 else 1
        current = canvas.yview()[0]
        target = min(1.0, max(0.0, current + delta * 0.12))
        self._animate_scroll(canvas, target, duration=280)
        return "break"

    def _handle_mousewheel(self, event):
        widget = event.widget
        for canvas, scrollable in reversed(self._scroll_targets):
            current = widget
            while current is not None:
                if current == scrollable or current == canvas:
                    return self._on_mousewheel(canvas, event)
                current = getattr(current, "master", None)

    def show_page(self, page):
        if self.current_page == "Asistente IA" and page != "Asistente IA":
            for attribute in ("stream_bubble", "stream_text", "stream_content"):
                if hasattr(self, attribute):
                    delattr(self, attribute)
        self.current_page = page
        self.page_title.configure(text=page)
        for name, button in self.nav_buttons.items():
            selected = name == page
            button.configure(
                bg=COLORS["accent"] if selected else COLORS["sidebar"],
                fg="white" if selected else COLORS["muted"],
                font=(FONT, 12, "bold" if selected else "normal"),
            )
        for child in self.content.winfo_children():
            child.destroy()

        if page == "Inicio":
            self._show_dashboard()
        elif page == "Asistente IA":
            self._show_chat()
        elif page == "Calendario":
            self._show_calendar()
        elif page == "Carga académica":
            self._show_workload()
        elif page == "Servicios de apoyo":
            self._show_services()

    def _show_dashboard(self):
        self._label(
            self.content,
            f"Hola, estudiante  {self._greeting()}",
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
            "Cuéntale a Aethera qué tienes pendiente y construyan juntos un siguiente paso.",
            color="#c4c7e7",
            bg="#171a3a",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(7, 15))
        self._button(
            left,
            "Conversar con Aethera  →",
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
        events = calendario_academico("any", fecha_inicio=today)
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

    def _show_calendar(self):
        heading = tk.Frame(self.content, bg=COLORS["background"])
        heading.pack(fill="x", pady=(0, 14))
        title_area = tk.Frame(heading, bg=COLORS["background"])
        title_area.pack(side="left")
        self._label(
            title_area,
            "Tu calendario académico",
            size=24,
            weight="bold",
            bg=COLORS["background"],
        ).pack(anchor="w")
        self._label(
            title_area,
            "Una vista clara de tus fechas importantes. Organiza tu semana con calma.",
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
            width=270,
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
            events = calendario_academico(
                "any",
                fecha_inicio=start.isoformat(),
                fecha_fin=end.isoformat(),
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
            text="Los eventos académicos se registran por fecha; no incluyen horario.",
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
            label = event.get("resumen") or "Evento académico"
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
                text=self._format_calendar_category(event.get("categoria", "")),
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
            progress = min(1.0, index / 20)
            eased = (1 - math.cos(math.pi * progress)) / 2
            previous = (1 - math.cos(math.pi * max(0, progress - 1 / 20))) / 2
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
            if index < 20:
                self._schedule_calendar_animation(
                    lambda: step(index + 1),
                    22,
                )

        self._schedule_calendar_animation(lambda: step(1), 22)

    def _animate_calendar_header(self, canvas, direction, left, top, right):
        del left, top, right
        canvas.move("calendar_event", -direction * 32, 0)

        def settle(index, previous=0.0):
            if not canvas.winfo_exists():
                return
            progress = min(1.0, index / 18)
            eased = (1 - math.cos(math.pi * progress)) / 2
            canvas.move("calendar_event", direction * 32 * (eased - previous), 0)
            if index < 18:
                self._schedule_calendar_animation(
                    lambda: settle(index + 1, eased),
                    18,
                )

        self._schedule_calendar_animation(lambda: settle(1), 18)

    def _show_calendar_event(self, event):
        dialog = tk.Toplevel(self.root)
        dialog.title(event.get("resumen", "Evento académico"))
        dialog.configure(bg=COLORS["background"])
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("560x340")
        dialog.resizable(False, False)
        panel = self._card(
            dialog,
            radius=28,
            bg=COLORS["surface"],
            gradient=("#17213b", "#17213b", "#25204c"),
        )
        panel.pack(fill="both", expand=True, padx=14, pady=14)
        category = event.get("categoria", "")
        _, accent, _ = EVENT_STYLES.get(category, (COLORS["surface_light"], COLORS["accent_light"], COLORS["border"]))
        self._label(
            panel,
            self._format_calendar_category(category).upper(),
            size=9,
            color=accent,
            weight="bold",
            bg="#17213b",
        ).pack(anchor="w", padx=24, pady=(23, 7))
        self._label(
            panel,
            event.get("resumen", "Evento académico"),
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
        district = event.get("distrito_id", "ALL")
        self._label(
            panel,
            f"Ubicación: {district.replace('DIST_', 'Distrito ').title()}",
            size=10,
            color=COLORS["muted"],
            bg="#17213b",
        ).pack(anchor="w", padx=24)
        self._label(
            panel,
            "Las fechas provienen del calendario académico institucional.",
            size=9,
            color=COLORS["muted"],
            bg="#17213b",
        ).pack(anchor="w", padx=24, pady=(14, 14))
        self._button(panel, "Entendido", dialog.destroy, primary=True).pack(
            anchor="e",
            padx=24,
            pady=(0, 20),
        )

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
            self._search_after_id = self.root.after(140, self._load_services)

    def _load_services(self):
        self._search_after_id = None
        for child in self.service_cards_container.winfo_children():
            child.destroy()
        self.service_count.configure(text="Cargando…")
        category = SERVICE_CATEGORIES[self.category_var.get()]
        try:
            result = buscar_servicios_ayuda(category)
            if "error" in result:
                raise ValueError(result["error"])
            selected_district = SERVICE_DISTRICTS[self.district_var.get()]
            query = self.service_search_var.get().strip().casefold()
            services = [
                service
                for service in result["servicios"]
                if (
                    selected_district is None
                    or service["ubicacion"]["distrito_id"] == selected_district
                )
                and (
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
            self.service_count.configure(
                text=f"{len(services)} {'opciones' if len(services) != 1 else 'opción'}"
            )
            if not services:
                self._show_empty_services()
                return
            for index, service in enumerate(services):
                self._service_card(service, index)
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.service_count.configure(text="Error")
            self._notice(
                self.service_cards_container,
                f"No se pudieron cargar los servicios de apoyo: {error}",
                COLORS["red"],
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

    def _show_chat(self):
        intro = self._card(self.content)
        intro.pack(fill="x", pady=(0, 12))
        self._label(
            intro,
            "Un espacio para pensar tu siguiente paso",
            size=14,
            weight="bold",
        ).pack(anchor="w", padx=16, pady=(13, 3))
        self._label(
            intro,
            "Aethera te acompaña a organizarte; tú decides cómo avanzar.",
            color=COLORS["muted"],
        ).pack(anchor="w", padx=16, pady=(0, 13))

        transcript = self._card(self.content)
        transcript.pack(fill="both", expand=True)
        canvas = tk.Canvas(transcript, bg=COLORS["background"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(transcript, orient="vertical", command=canvas.yview)
        self.message_list = tk.Frame(canvas, bg=COLORS["background"])
        self.message_list.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas_window = canvas.create_window((0, 0), window=self.message_list, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(canvas_window, width=event.width),
        )
        canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=8)
        self.canvas = canvas
        self._bind_smooth_scroll(canvas, self.message_list)

        for message in self.chat.historial:
            if message.get("role") in {"assistant", "user"} and message.get("content"):
                self._append_message(message["role"], message["content"])
        if not self.message_list.winfo_children():
            self._append_message(
                "assistant",
                "¡Hola! Soy Aethera. ¿Qué te gustaría organizar o conversar hoy?",
            )

        composer = self._card(self.content)
        composer.pack(fill="x", pady=(12, 0))
        self.message_input = tk.Text(
            composer,
            height=3,
            wrap="word",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            font=(FONT, 12),
            padx=12,
            pady=10,
        )
        self.message_input.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        self.message_input.bind("<Control-Return>", self._send_from_shortcut)
        send_button = self._button(composer, "Enviar  ↑", self._send_message, primary=True)
        send_button.pack(side="right", padx=10, pady=10)
        self.send_button = send_button
        if self.busy:
            self.send_button.configure(state="disabled")

    def _append_message(self, role, text):
        is_user = role == "user"
        outer = tk.Frame(self.message_list, bg=COLORS["background"])
        outer.pack(fill="x", padx=15, pady=8)
        bubble_color = "#30245f" if is_user else COLORS["surface"]
        bubble_center = "#5b52e8" if is_user else COLORS["surface"]
        if is_user:
            bubble_color = bubble_center
        bubble = self._card(
            outer,
            bg=bubble_color,
            border=COLORS["accent_light"] if is_user else COLORS["border"],
            radius=24,
            gradient=("#7666ff", bubble_center, "#3c73cb") if is_user else None,
        )
        bubble.pack(side="right" if is_user else "left", padx=(80, 0) if is_user else (0, 80))
        tk.Label(
            bubble,
            text="Tú" if is_user else "Aethera",
            bg=bubble_color,
            fg="white" if is_user else COLORS["accent_light"],
            font=(FONT, 10, "bold"),
        ).pack(anchor="w", padx=18, pady=(14, 4))
        body = self._create_formatted_message(
            bubble,
            text,
            background=bubble_color,
            foreground="white" if is_user else COLORS["text"],
            width=max(50, (self.root.winfo_width() - 560) // 9),
        )
        body.pack(anchor="w", padx=18, pady=(0, 15))
        self._animate_card_in(outer)
        self.root.after_idle(lambda: self._animate_scroll_to_bottom(self.canvas))

    def _create_formatted_message(self, parent, text, background, foreground, width):
        line_count = self._estimate_message_lines(text, width)
        body = tk.Text(
            parent,
            width=width,
            height=line_count,
            wrap="word",
            bg=background,
            fg=foreground,
            insertwidth=0,
            borderwidth=0,
            highlightthickness=0,
            relief="flat",
            padx=0,
            pady=0,
            font=(FONT, 12),
            cursor="arrow",
            takefocus=False,
            spacing1=2,
            spacing3=2,
        )
        body.tag_configure("bold", font=(FONT, 12, "bold"))
        body.tag_configure("italic", font=(FONT, 12, "italic"))
        body.tag_configure("code", font=("Consolas", 11), foreground="#b6c8ff")
        body.tag_configure(
            "heading",
            font=(FONT, 14, "bold"),
            foreground=COLORS["accent_light"],
            spacing1=7,
            spacing3=4,
        )
        body.tag_configure(
            "quote",
            foreground="#c1cce2",
            lmargin1=14,
            lmargin2=14,
        )
        body.tag_configure("emoji", font=("Segoe UI Emoji", 12))
        body.tag_configure("strike", overstrike=True)
        self._insert_formatted_text(body, text)
        body.configure(state="disabled")
        return body

    def _estimate_message_lines(self, text, width):
        available = max(20, width)
        lines = 0
        for line in text.splitlines() or [""]:
            lines += max(1, math.ceil(len(line) / available))
        return min(28, max(1, lines))

    def _insert_formatted_text(self, widget, text):
        for line_index, line in enumerate(text.splitlines()):
            if line_index:
                widget.insert("end", "\n")
            heading_match = re.match(r"^\s{0,3}(#{1,3})\s+(.*)$", line)
            if heading_match:
                widget.insert("end", f"{heading_match.group(2)}\n", "heading")
                continue
            quote_match = re.match(r"^\s*>\s?(.*)$", line)
            if quote_match:
                self._insert_inline_formatted_text(
                    widget,
                    quote_match.group(1),
                    base_tag="quote",
                )
                continue
            list_match = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", line)
            if list_match:
                marker = "•" if list_match.group(2) in {"-", "*", "+"} else f"{list_match.group(2)}"
                widget.insert("end", f"{list_match.group(1)}{marker}  ")
                self._insert_inline_formatted_text(widget, list_match.group(3))
                continue
            self._insert_inline_formatted_text(widget, line)
        if text.endswith("\n"):
            widget.insert("end", "\n")

    def _set_formatted_text(self, widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        self._insert_formatted_text(widget, text)
        widget.configure(
            height=self._estimate_message_lines(
                text,
                max(50, (self.root.winfo_width() - 560) // 9),
            ),
            state="disabled",
        )

    def _insert_inline_formatted_text(self, widget, text, base_tag=None):
        for part in INLINE_MARKDOWN.split(text):
            if not part:
                continue
            tag = base_tag
            value = part
            if part.startswith(("**", "__")) and part.endswith(part[:2]):
                value = part[2:-2]
                tag = "bold"
            elif part.startswith("~~") and part.endswith("~~"):
                value = part[2:-2]
                tag = "strike"
            elif part.startswith("`") and part.endswith("`"):
                value = part[1:-1]
                tag = "code"
            elif part.startswith("*") and part.endswith("*"):
                value = part[1:-1]
                tag = "italic"

            segments = EMOJI_CHAR.split(value)
            emojis = EMOJI_CHAR.findall(value)
            for index, segment in enumerate(segments):
                if segment:
                    tags = tuple(item for item in (base_tag, tag) if item)
                    widget.insert("end", segment, tags)
                if index < len(emojis):
                    tags = tuple(item for item in (base_tag, tag, "emoji") if item)
                    widget.insert("end", emojis[index], tags)

    def _send_from_shortcut(self, _event):
        self._send_message()
        return "break"

    def _send_message(self):
        if self.busy:
            return
        text = self.message_input.get("1.0", "end").strip()
        if not text:
            return
        self.message_input.delete("1.0", "end")
        self._append_message("user", text)
        self.busy = True
        self.send_button.configure(state="disabled")
        self.status_label = self._label(
            self.content,
            "✦  Aethera está pensando",
            size=10,
            color=COLORS["accent_light"],
            bg=COLORS["background"],
        )
        self.status_label.pack(anchor="w", pady=(5, 0))
        self.status_base = "✦  Aethera está pensando"
        self._typing_phase = 0
        self._pulse_typing_indicator()
        worker = threading.Thread(
            target=self._run_chat_turn,
            args=(text,),
            daemon=True,
        )
        worker.start()

    def _run_chat_turn(self, text):
        try:
            self.chat.procesar_turno(
                text,
                al_emitir_texto=lambda chunk: self.event_queue.put(("token", chunk)),
                al_actualizar_estado=lambda status: self.event_queue.put(("status", status)),
            )
            self.event_queue.put(("complete", None))
        except Exception as error:
            self.event_queue.put(("error", str(error)))

    def _process_queue(self):
        try:
            while True:
                event, value = self.event_queue.get_nowait()
                if event == "token":
                    if self.current_page == "Asistente IA":
                        self._append_stream_chunk(value)
                elif event == "status":
                    self._set_status(value)
                elif event == "complete":
                    self._finish_chat_turn()
                elif event == "error":
                    self._append_message(
                        "assistant",
                        f"No pude completar la respuesta. Inténtalo de nuevo.\n\nDetalle: {value}",
                    )
                    self._finish_chat_turn()
        except queue.Empty:
            pass
        self.root.after(80, self._process_queue)

    def _pulse_typing_indicator(self):
        if not self.busy or not hasattr(self, "status_label"):
            return
        if not self.status_label.winfo_exists():
            return
        self._typing_phase = (self._typing_phase + 1) % 4
        dots = "·" * self._typing_phase
        color = COLORS["accent_light"] if self._typing_phase % 2 else COLORS["teal"]
        self.status_label.configure(
            text=f"{self.status_base}  {dots}",
            fg=color,
        )
        self._typing_after_id = self.root.after(500, self._pulse_typing_indicator)

    def _append_stream_chunk(self, chunk):
        if not hasattr(self, "stream_bubble"):
            outer = tk.Frame(self.message_list, bg=COLORS["background"])
            outer.pack(fill="x", padx=15, pady=8)
            stream_background = "#14283b"
            self.stream_bubble = self._card(
                outer,
                bg=stream_background,
                border="#405176",
                radius=24,
                gradient=("#17223d", stream_background, "#20214b"),
            )
            self.stream_bubble.pack(side="left", padx=(0, 80))
            tk.Label(
                self.stream_bubble,
                text="Aethera",
                bg=stream_background,
                fg=COLORS["accent_light"],
                font=(FONT, 10, "bold"),
            ).pack(anchor="w", padx=18, pady=(14, 4))
            self.stream_text = self._create_formatted_message(
                self.stream_bubble,
                "",
                background=stream_background,
                foreground=COLORS["text"],
                width=max(50, (self.root.winfo_width() - 560) // 9),
            )
            self.stream_text.pack(anchor="w", padx=18, pady=(0, 15))
            self.stream_content = ""
            self._animate_card_in(outer)
        self.stream_content += chunk
        self._set_formatted_text(self.stream_text, self.stream_content)
        self.root.after_idle(lambda: self._animate_scroll_to_bottom(self.canvas))

    def _set_status(self, status):
        if hasattr(self, "status_label") and self.status_label.winfo_exists():
            self.status_base = f"✦  {status}"
            self.status_label.configure(text=self.status_base)

    def _finish_chat_turn(self):
        typing_after_id = getattr(self, "_typing_after_id", None)
        if typing_after_id:
            self.root.after_cancel(typing_after_id)
        if hasattr(self, "status_label") and self.status_label.winfo_exists():
            self.status_label.destroy()
        self.busy = False
        if hasattr(self, "send_button") and self.send_button.winfo_exists():
            self.send_button.configure(state="normal")
        if hasattr(self, "stream_bubble"):
            del self.stream_bubble
            del self.stream_text
            del self.stream_content
        if self.current_page == "Asistente IA" and hasattr(self, "canvas"):
            self.root.after_idle(lambda: self._animate_scroll_to_bottom(self.canvas))

    def _bind_smooth_scroll(self, canvas, child):
        self._scroll_targets.append((canvas, child))

    def _animate_card_in(self, widget, grid=False):
        try:
            info = widget.grid_info() if grid else widget.pack_info()
        except tk.TclError:
            return
        padding = info.get("pady", 0)
        if isinstance(padding, tuple):
            final_top, final_bottom = (int(value) for value in padding)
        else:
            final_top = final_bottom = int(padding)
        steps = 18
        widget.configure(highlightthickness=0)
        rounded = next(
            (
                child
                for child in widget.winfo_children()
                if isinstance(child, RoundedFrame)
            ),
            widget if isinstance(widget, RoundedFrame) else None,
        )
        original_border = rounded.border if rounded else None
        parent_bg = widget.master.cget("bg")

        def step(index):
            if not widget.winfo_exists():
                return
            progress = min(1.0, index / steps)
            eased = (1 - math.cos(math.pi * progress)) / 2
            top = round(final_top * eased)
            bottom = round(final_bottom * eased)
            if grid:
                widget.grid_configure(pady=(top, bottom))
            else:
                widget.pack_configure(pady=(top, bottom))
            if rounded:
                rounded.border = _mix_color(
                    parent_bg,
                    original_border,
                    eased,
                )
                rounded._draw()
            if index < steps:
                self.root.after(20, lambda: step(index + 1))

        self.root.after(0, lambda: step(1))

    def _notice(self, parent, text, color):
        tk.Label(
            parent,
            text=text,
            bg=COLORS["surface"],
            fg=color,
            font=(FONT, 9),
            wraplength=900,
            justify="left",
        ).pack(anchor="w", padx=18, pady=16)

    def run(self):
        self.root.mainloop()


def iniciar_app_escritorio(motor, historial, herramientas, guardar_historial):
    AetheraDesktopApp(motor, historial, herramientas, guardar_historial).run()
