"""Tarjeta para presentar un quiz disponible."""

import tkinter as tk

from ...tema import COLORS, FONT
from ...widgets import RoundedFrame
from core.quizzes import resumir_quiz


class QuizCard:
    def __init__(self, parent, quiz, on_start, continuar=False):
        self.frame = RoundedFrame(
            parent,
            bg=COLORS["surface_light"],
            border=COLORS["border"],
            radius=22,
        )
        self.frame.pack(fill="x", padx=4, pady=7)
        top = tk.Frame(self.frame, bg=COLORS["surface_light"])
        top.pack(fill="x", padx=18, pady=(16, 8))
        tk.Label(
            top,
            text="⚗",
            bg="#282650",
            fg=COLORS["accent_light"],
            font=(FONT, 17, "bold"),
            width=2,
        ).pack(side="left", padx=(0, 12), ipady=4)
        tk.Label(
            top,
            text=quiz["quiz_titulo"],
            bg=COLORS["surface_light"],
            fg=COLORS["text"],
            font=(FONT, 12, "bold"),
            wraplength=600,
            justify="left",
        ).pack(side="left", fill="x", expand=True, anchor="w")

        resumen = resumir_quiz(quiz)
        tk.Label(
            self.frame,
            text=(
                f"{resumen['alternativas']} Alternativa | "
                f"{resumen['desarrollo']} Respuesta"
            ),
            bg=COLORS["surface_light"],
            fg=COLORS["muted"],
            font=(FONT, 9),
        ).pack(anchor="w", padx=18, pady=(0, 12))
        button = tk.Button(
            self.frame,
            text="Continuar Quiz" if continuar else "Iniciar Quiz",
            command=lambda: on_start(quiz),
            bg=COLORS["accent"],
            fg="white",
            activebackground=COLORS["accent_light"],
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=15,
            pady=9,
            font=(FONT, 9, "bold"),
            cursor="hand2",
        )
        button.pack(anchor="e", padx=18, pady=(0, 16))
