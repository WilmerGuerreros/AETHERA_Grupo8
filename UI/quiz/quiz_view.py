"""Orquestador de la sección de quizzes."""

import threading
from typing import Any, Callable, Protocol

from ..components import COLORS, FONT, RoundedButton, RoundedFrame, tk, ttk
from .components import QuizCard
from .logica import QuizLogic


class _QuizDesktopHost(Protocol):
    root: Any
    content: Any
    chat: Any
    event_queue: Any
    _label: Callable[..., tk.Label]
    _card: Callable[..., RoundedFrame]
    _button: Callable[..., RoundedButton]
    _bind_smooth_scroll: Callable[..., None]


class QuizSection(_QuizDesktopHost):
    def _show_quiz(self):
        self.quiz_logic = QuizLogic(self.chat.motor)
        self._label(
            self.content,
            "Tus quizzes",
            size=22,
            weight="bold",
            bg=COLORS["background"],
        ).pack(anchor="w")
        self._label(
            self.content,
            "Practica a tu ritmo y revisa tu progreso.",
            color=COLORS["muted"],
            bg=COLORS["background"],
        ).pack(anchor="w", pady=(5, 18))
        self.quiz_list_card = self._card(self.content)
        self.quiz_list_card.pack(fill="both", expand=True)
        self.quiz_canvas = tk.Canvas(
            self.quiz_list_card,
            bg=COLORS["surface"],
            highlightthickness=0,
        )
        scrollbar = ttk.Scrollbar(
            self.quiz_list_card,
            orient="vertical",
            command=self.quiz_canvas.yview,
        )
        self.quiz_cards = tk.Frame(self.quiz_canvas, bg=COLORS["surface"])
        self.quiz_cards.bind(
            "<Configure>",
            lambda _event: self.quiz_canvas.configure(
                scrollregion=self.quiz_canvas.bbox("all")
            ),
        )
        window = self.quiz_canvas.create_window(
            (0, 0), window=self.quiz_cards, anchor="nw"
        )
        self.quiz_canvas.configure(yscrollcommand=scrollbar.set)
        self.quiz_canvas.bind(
            "<Configure>",
            lambda event: self.quiz_canvas.itemconfigure(window, width=event.width),
        )
        self.quiz_canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=8)
        self._bind_smooth_scroll(self.quiz_canvas, self.quiz_cards)
        self._load_quiz_cards()

    def _load_quiz_cards(self):
        try:
            quizzes = self.quiz_logic.listar_quices()
        except (OSError, ValueError) as error:
            self._show_quiz_message(f"No se pudieron cargar los quizzes: {error}")
            return
        if not quizzes:
            self._show_quiz_message(
                "Todavía no hay quizzes guardados en los datos del usuario."
            )
            return
        for quiz in quizzes:
            try:
                intento = self.quiz_logic.cargar_intento(quiz)
            except ValueError as error:
                self._show_quiz_message(str(error))
                continue
            QuizCard(
                self.quiz_cards,
                quiz,
                self._start_quiz,
                continuar=intento is not None,
            )

    def _show_quiz_message(self, message):
        tk.Label(
            self.quiz_cards,
            text=message,
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=(FONT, 10),
            wraplength=720,
            justify="left",
        ).pack(anchor="w", padx=20, pady=22)

    def _start_quiz(self, quiz):
        try:
            attempt = self.quiz_logic.cargar_intento(quiz)
        except ValueError as error:
            self._show_quiz_message(str(error))
            return
        self._open_quiz_window(quiz, attempt)

    def _open_quiz_window(self, quiz, attempt):
        window = tk.Toplevel(self.root)
        window.title(quiz["test_titulo"])
        window.configure(bg=COLORS["background"])
        window.transient(self.root)
        window.geometry("760x680")
        state = {
            "indice": attempt["indice"] if attempt else 0,
            "respuestas": attempt["respuestas"] if attempt else {},
            "busy": False,
        }
        window.protocol(
            "WM_DELETE_WINDOW",
            lambda: self._close_quiz_window(window, quiz, state),
        )
        self._render_quiz_page(window, quiz, state)

    def _render_quiz_page(self, window, quiz, state):
        for child in window.winfo_children():
            child.destroy()
        indice = state["indice"]
        pagina = quiz["paginas"][indice]
        header = self._card(window)
        header.pack(fill="x", padx=20, pady=(20, 10))
        self._label(header, quiz["test_titulo"], size=14, weight="bold").pack(
            anchor="w", padx=18, pady=(15, 4)
        )
        self._label(
            header,
            f"Pregunta {indice + 1} de {len(quiz['paginas'])}",
            color=COLORS["accent_light"],
        ).pack(anchor="w", padx=18, pady=(0, 15))

        content = self._card(window)
        content.pack(fill="both", expand=True, padx=20, pady=10)
        self._label(content, pagina["pregunta"], size=14, weight="bold", wraplength=660).pack(
            anchor="w", padx=22, pady=(24, 18)
        )
        feedback = None
        if pagina["tipo"] == "alternativa":
            for letra, texto in pagina["alternativas"].items():
                selected = state["respuestas"].get(pagina["id"]) == letra
                button = tk.Button(
                    content,
                    text=f"{letra}    {texto}",
                    anchor="w",
                    command=lambda key=letra: self._select_quiz_answer(
                        window, quiz, state, key
                    ),
                    bg=COLORS["accent"] if selected else COLORS["surface_light"],
                    fg=COLORS["text"],
                    activebackground=COLORS["accent_light"],
                    activeforeground="white",
                    relief="flat",
                    padx=15,
                    pady=12,
                    font=(FONT, 10),
                    cursor="hand2",
                )
                button.pack(fill="x", padx=22, pady=5)
            if state["respuestas"].get(pagina["id"]):
                key = state["respuestas"][pagina["id"]]
                feedback = pagina["retroalimentacion"][key]
        else:
            response = tk.Text(
                content,
                height=8,
                wrap="word",
                bg=COLORS["surface_light"],
                fg=COLORS["text"],
                insertbackground=COLORS["text"],
                relief="flat",
                font=(FONT, 10),
                padx=12,
                pady=10,
            )
            response.pack(fill="x", padx=22, pady=(0, 12))
            response.insert("1.0", state["respuestas"].get(pagina["id"], ""))
            state["response_widget"] = response
        if feedback:
            self._label(
                content,
                feedback,
                color=COLORS["green"]
                if state["respuestas"][pagina["id"]] == pagina["respuesta_correcta"]
                else COLORS["yellow"],
                wraplength=660,
                justify="left",
            ).pack(anchor="w", padx=22, pady=12)
        footer = tk.Frame(window, bg=COLORS["background"])
        footer.pack(fill="x", padx=20, pady=(8, 20))
        previous_button = self._button(
            footer,
            "Anterior",
            lambda: self._move_quiz(window, quiz, state, -1),
        )
        previous_button.pack(side="left")
        final = indice == len(quiz["paginas"]) - 1
        self._button(
            footer,
            "Finalizar" if final else "Siguiente",
            lambda: self._finish_quiz(window, quiz, state)
            if final
            else self._move_quiz(window, quiz, state, 1),
            primary=True,
        ).pack(side="right")
        if indice == 0:
            previous_button.disabled = True
            previous_button._draw()

    def _select_quiz_answer(self, window, quiz, state, key):
        pagina = quiz["paginas"][state["indice"]]
        state["respuestas"][pagina["id"]] = key
        self._save_quiz_progress(quiz, state)
        self._render_quiz_page(window, quiz, state)

    def _move_quiz(self, window, quiz, state, step):
        self._capture_development_answer(quiz, state)
        state["indice"] += step
        self._save_quiz_progress(quiz, state)
        self._render_quiz_page(window, quiz, state)

    def _capture_development_answer(self, quiz, state):
        pagina = quiz["paginas"][state["indice"]]
        widget = state.pop("response_widget", None)
        if pagina["tipo"] == "desarrollo" and widget and widget.winfo_exists():
            answer = widget.get("1.0", "end").strip()
            if answer:
                state["respuestas"][pagina["id"]] = answer
            else:
                state["respuestas"].pop(pagina["id"], None)

    def _save_quiz_progress(self, quiz, state):
        if not state["respuestas"]:
            self.quiz_logic.eliminar_intento(quiz["test_id"])
            return
        self.quiz_logic.guardar_intento(
            quiz, state["indice"], state["respuestas"]
        )

    def _close_quiz_window(self, window, quiz, state):
        self._capture_development_answer(quiz, state)
        self._save_quiz_progress(quiz, state)
        window.destroy()

    def _finish_quiz(self, window, quiz, state):
        self._capture_development_answer(quiz, state)
        self._save_quiz_progress(quiz, state)
        for child in window.winfo_children():
            child.destroy()
        tk.Label(
            window,
            text="revisando respuestas",
            bg=COLORS["background"],
            fg=COLORS["accent_light"],
            font=(FONT, 15, "bold"),
        ).pack(expand=True)
        worker = threading.Thread(
            target=self._evaluate_quiz_worker,
            args=(quiz, state["respuestas"], window),
            daemon=True,
        )
        worker.start()

    def _evaluate_quiz_worker(self, quiz, respuestas, window):
        try:
            resultado = self.quiz_logic.evaluar(quiz, respuestas)
            self.event_queue.put(("quiz_evaluated", (window, quiz, resultado)))
        except Exception as error:
            self.event_queue.put(("quiz_evaluation_error", (window, str(error))))

    def _show_quiz_results(self, window, quiz, resultado):
        if not window.winfo_exists():
            return
        for child in window.winfo_children():
            child.destroy()
        tk.Label(
            window,
            text=(
                f"Puntaje alternativas: {resultado['puntaje']}%"
                if resultado["puntaje"] is not None
                else "Quiz sin preguntas de alternativa"
            ),
            bg=COLORS["background"],
            fg=COLORS["green"],
            font=(FONT, 20, "bold"),
        ).pack(anchor="w", padx=24, pady=(22, 12))
        if resultado["porcentaje_desarrollo"] is not None:
            tk.Label(
                window,
                text=(
                    "Desarrollo · promedio de acierto "
                    f"{resultado['porcentaje_desarrollo']}%"
                ),
                bg=COLORS["background"],
                fg=COLORS["accent_light"],
                font=(FONT, 11, "bold"),
            ).pack(anchor="w", padx=24, pady=(0, 10))
        frame = tk.Frame(window, bg=COLORS["background"])
        frame.pack(fill="both", expand=True, padx=24)
        for feedback in resultado["retroalimentacion"]:
            page = next(
                page for page in quiz["paginas"]
                if page["id"] == feedback["pregunta_id"]
            )
            line = (
                f"{page['pregunta']}\n"
                + (
                    f"{'Correcta' if feedback['correcta'] else 'Incorrecta'} · "
                    if "correcta" in feedback
                    else f"{feedback['porcentaje']}% de acierto · "
                )
                + feedback["retroalimentacion"]
            )
            tk.Label(
                frame,
                text=line,
                bg=COLORS["surface"],
                fg=COLORS["text"],
                font=(FONT, 9),
                justify="left",
                wraplength=680,
                padx=14,
                pady=10,
            ).pack(fill="x", pady=5)
        self.quiz_logic.eliminar_intento(quiz["test_id"])
        tk.Button(
            window,
            text="Cerrar",
            command=lambda: self._close_quiz_results(window),
            bg=COLORS["accent"],
            fg="white",
            relief="flat",
            padx=16,
            pady=9,
        ).pack(anchor="e", padx=24, pady=16)

    def _close_quiz_results(self, window):
        window.destroy()
        if self.current_page == "Quiz":
            self.show_page("Quiz")

    def _show_quiz_evaluation_error(self, window, message):
        if not window.winfo_exists():
            return
        for child in window.winfo_children():
            child.destroy()
        tk.Label(
            window,
            text=f"No se pudieron revisar las respuestas: {message}",
            bg=COLORS["background"],
            fg=COLORS["red"],
            font=(FONT, 11),
            wraplength=650,
        ).pack(expand=True, padx=24)
        tk.Button(
            window,
            text="Volver",
            command=window.destroy,
            bg=COLORS["surface_light"],
            fg=COLORS["text"],
            relief="flat",
            padx=16,
            pady=9,
        ).pack(anchor="e", padx=24, pady=16)
