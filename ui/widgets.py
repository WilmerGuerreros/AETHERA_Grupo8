"""Widgets reutilizables con esquinas redondeadas y animaciones."""

import math

import tkinter as tk
from tkinter import font as tkfont

from .tema import COLORS, FONT


def mezclar_color(start, end, amount):
    """Mezcla dos colores hexadecimales; ``amount`` va de 0 (inicio) a 1 (fin)."""
    start_rgb = tuple(int(start[index:index + 2], 16) for index in (1, 3, 5))
    end_rgb = tuple(int(end[index:index + 2], 16) for index in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(
        round(first + (last - first) * amount)
        for first, last in zip(start_rgb, end_rgb)
    )


def texto_con_elipsis(texto, fuente, ancho):
    """Recorta texto al ancho disponible sin partir palabras visualmente."""
    if ancho <= 0:
        return ""
    medida = fuente if isinstance(fuente, tkfont.Font) else tkfont.Font(font=fuente)
    if medida.measure(texto) <= ancho:
        return texto
    elipsis = "…"
    if medida.measure(elipsis) > ancho:
        return ""
    texto = texto.rstrip()
    while texto and medida.measure(texto + elipsis) > ancho:
        texto = texto[:-1].rstrip()
    return texto + elipsis


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
            inset = min(5, radius)
            inner_radius = max(0, radius - inset)
            inner_points = []
            for center_x, center_y, start in (
                (width - inset - inner_radius, inset + inner_radius, -90),
                (
                    width - inset - inner_radius,
                    height - inset - inner_radius,
                    0,
                ),
                (inset + inner_radius, height - inset - inner_radius, 90),
                (inset + inner_radius, inset + inner_radius, 180),
            ):
                for step in range(13):
                    angle = (start + step * 90 / 12) * math.pi / 180
                    inner_points.extend(
                        (
                            center_x + inner_radius * math.cos(angle),
                            center_y + inner_radius * math.sin(angle),
                        )
                    )
            if width - inset * 2 > 0 and height - inset * 2 > 0:
                self.canvas.create_polygon(
                    *inner_points,
                    smooth=True,
                    splinesteps=24,
                    fill=self.fill,
                    outline="",
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
    return mezclar_color(stops[index], stops[index + 1], segment - index)


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
        self.gradient = (
            ("#7666ff", "#634ff0", "#3d82ed")
            if primary
            else ("#18223b", "#1d2943", "#18223b")
        )
        self.selected = False
        self.font = (FONT, 10, "bold")
        self._display_gradient = self.gradient
        self._gradient_animation_id = None
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
        for row in range(height):
            left, right = _rounded_scanline(width, height, radius, row)
            self.create_line(
                left,
                row,
                right,
                row,
                fill=_gradient_color(
                    self._display_gradient,
                    row / max(1, height - 1),
                ),
                tags="button",
            )
        outline = (
            COLORS["accent_light"]
            if self.focused or self.selected
            else self._display_gradient[1]
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
        elif self.selected:
            self.create_polygon(
                *points,
                smooth=True,
                splinesteps=20,
                fill="",
                outline=outline,
                width=1,
                tags="button",
            )
        self.create_text(
            width / 2,
            height / 2,
            text=texto_con_elipsis(
                self.text,
                self.font,
                max(0, width - 28),
            ),
            fill=(
                "#8792ad"
                if self.disabled
                else COLORS["text"]
                if self.selected or self.hovered
                else COLORS["muted"]
                if not self.primary
                else "white"
            ),
            font=self.font,
            tags="button",
        )

    def _gradient_for_state(self):
        if self.disabled:
            color = COLORS["border"]
            return color, mezclar_color(color, COLORS["surface_light"], 0.4), color
        if self.pressed:
            return ("#4439bd", "#5144cf", "#315fae")
        if self.selected:
            return ("#5145d7", "#5f53e8", "#326fc6")
        if self.hovered:
            return ("#302b62", "#383774", "#264b76")
        if self.focused and not self.primary:
            return ("#24234b", "#292952", "#203a5d")
        return self.gradient

    def _animate_gradient(self):
        if self._gradient_animation_id:
            self.after_cancel(self._gradient_animation_id)
            self._gradient_animation_id = None
        start = self._display_gradient
        target = self._gradient_for_state()
        if start == target:
            self._draw()
            return

        def step(index):
            if not self.winfo_exists():
                return
            progress = min(1.0, index / 9)
            eased = 1 - (1 - progress) ** 3
            self._display_gradient = tuple(
                mezclar_color(first, last, eased)
                for first, last in zip(start, target)
            )
            self._draw()
            if progress < 1:
                self._gradient_animation_id = self.after(
                    14,
                    lambda next_step=index + 1: step(next_step),
                )
            else:
                self._gradient_animation_id = None

        step(1)

    def set_selected(self, selected):
        self.selected = selected
        self.font = (FONT, 10, "bold" if selected else "normal")
        self._animate_gradient()

    def _on_enter(self, _event):
        self.hovered = True
        self._animate_gradient()

    def _on_leave(self, _event):
        self.hovered = False
        self.pressed = False
        self._animate_gradient()

    def _on_focus(self, _event):
        self.focused = True
        self._animate_gradient()

    def _on_blur(self, _event):
        self.focused = False
        self._animate_gradient()

    def _on_press(self, _event):
        if not self.disabled:
            self.pressed = True
            self._animate_gradient()

    def _on_release(self, event):
        was_pressed = self.pressed
        self.pressed = False
        self._animate_gradient()
        inside = 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height()
        if was_pressed and inside and not self.disabled:
            self.command()

    def _invoke(self, _event=None):
        if not self.disabled:
            self.pressed = True
            self._animate_gradient()
            self.after(100, self._release_keyboard_activation)
            self.command()
        return "break"

    def _release_keyboard_activation(self):
        if self.winfo_exists():
            self.pressed = False
            self._animate_gradient()

    def configure(self, cnf=None, **kwargs):
        state = kwargs.pop("state", None)
        if state is not None:
            self.disabled = state == "disabled"
            super().configure(cursor="arrow" if self.disabled else "hand2")
            self._animate_gradient()
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
        self._gradient_animation_id = None
        self._hover_animations = {}
        self._hover_starts = {}
        self.hovered = False
        self.pressed = False
        self._display_gradient = ("#222b45", "#1b2238", "#252044")
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
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Enter>", self._on_hover)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<Return>", self.toggle)
        self.canvas.bind("<space>", self.toggle)
        self.canvas.configure(takefocus=True)
        self.textvariable.trace_add("write", self._draw)
        self.bind("<Configure>", self._resize)

    def _resize(self, event):
        self.canvas.configure(width=event.width)
        self._draw()

    def set_width(self, width):
        """Ajusta el selector a su celda sin desbordar el área disponible."""
        width = max(110, int(width))
        self.configure(width=width)
        self.canvas.configure(width=width)
        self._draw()

    def _draw(self, *_args):
        if not self.winfo_exists():
            return
        self.canvas.delete("selector")
        width = max(2, self.canvas.winfo_width())
        height = max(2, self.canvas.winfo_height())
        radius = min(15, height // 2)
        colors = self._display_gradient
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
            text=texto_con_elipsis(
                selected,
                (FONT, 10, "bold"),
                max(0, width - 72),
            ),
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
        self.hovered = True
        if not self.is_open:
            self.canvas.configure(cursor="hand2")
        self._animate_gradient()
        self._draw()

    def _on_leave(self, _event=None):
        self.hovered = False
        self.pressed = False
        self._animate_gradient()
        self.canvas.configure(cursor="hand2")
        self._draw()

    def _on_press(self, _event=None):
        self.pressed = True
        self._animate_gradient()
        return "break"

    def _on_release(self, _event=None):
        was_pressed = self.pressed
        self.pressed = False
        self._animate_gradient()
        if was_pressed:
            self.toggle()
        return "break"

    def _gradient_for_state(self):
        if self.pressed:
            return ("#403782", "#39366f", "#294c73")
        if self.is_open:
            return ("#393274", "#2e355e", "#2c4d70")
        if self.hovered:
            return ("#302b62", "#2a3155", "#264968")
        return ("#222b45", "#1b2238", "#252044")

    def _animate_gradient(self):
        if self._gradient_animation_id:
            self.after_cancel(self._gradient_animation_id)
            self._gradient_animation_id = None
        start = self._display_gradient
        target = self._gradient_for_state()
        if start == target:
            self._draw()
            return

        def step(index):
            if not self.winfo_exists():
                return
            progress = min(1.0, index / 8)
            eased = 1 - (1 - progress) ** 3
            self._display_gradient = tuple(
                mezclar_color(first, last, eased)
                for first, last in zip(start, target)
            )
            self._draw()
            if progress < 1:
                self._gradient_animation_id = self.after(
                    14,
                    lambda next_step=index + 1: step(next_step),
                )
            else:
                self._gradient_animation_id = None

        step(1)

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
        self._animate_gradient()
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
        progress = min(1.0, step / 7)
        eased = progress * progress * (3 - 2 * progress)
        color = mezclar_color(start, target, eased)
        row.configure(
            bg=color,
            highlightbackground=accent,
            highlightthickness=0 if restore and step == 7 else 1,
        )
        for child in row.winfo_children():
            if isinstance(child, (tk.Label, tk.Canvas)):
                child.configure(bg=color)
        if step < 7:
            self._hover_animations[str(row)] = self.after(
                14,
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
        progress = min(1.0, step / 14)
        eased = 1 - (1 - progress) ** 4
        height = max(1, round(self.popup_height * eased))
        self.popup.geometry(
            f"{self.popup_width}x{height}+{self.popup_x}+{self.popup_y}"
        )
        if step < 14:
            self.animation_id = self.after(14, lambda: self._animate_open(step + 1))

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
        progress = min(1.0, step / 14)
        eased = 1 - (1 - progress) ** 3
        self.selection_color = mezclar_color(old_color, new_color, eased)
        self._draw()
        if step < 14:
            self._selection_animation_id = self.after(
                16,
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
        self._animate_gradient()
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
        progress = min(1.0, step / 11)
        eased = progress * progress * (3 - 2 * progress)
        height = max(1, round(self.popup_height * (1 - eased)))
        popup.geometry(
            f"{self.popup_width}x{height}+{self.popup_x}+{self.popup_y}"
        )
        if step < 11:
            self.animation_id = self.after(
                14,
                lambda: self._animate_close(popup, step + 1),
            )
        else:
            popup.destroy()
            self.animation_id = None
