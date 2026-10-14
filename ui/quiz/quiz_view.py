"""Orquestador de la sección de quizzes."""

import threading
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Protocol

from ..tema import COLORS, FONT
from ..widgets import RoundedButton, RoundedFrame
from .components import QuizCard
from core.quizzes import (
    cargar_intento,
    guardar_progreso_quiz,
    listar_quices,
    seleccionar_respuesta_alternativa,
)


class _QuizDesktopHost(Protocol):
    root: Any
    content: Any
    chat: Any
    event_queue: Any
    current_page: str
    _label: Callable[..., tk.Label]
    _card: Callable[..., RoundedFrame]
    _button: Callable[..., RoundedButton]
    _bind_smooth_scroll: Callable[..., None]
    show_page: Callable[[str], None]


class QuizSection(_QuizDesktopHost):
    def _show_quiz(self):
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
            quizzes = listar_quices()
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
                intento = cargar_intento(quiz)
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
            attempt = cargar_intento(quiz)
        except ValueError as error:
            self._show_quiz_message(str(error))
            return
        self._open_quiz_window(quiz, attempt)

    def _open_quiz_window(self, quiz, attempt):
        window = tk.Toplevel(self.root)
        window.title(quiz["quiz_titulo"])
        window.configure(bg=COLORS["background"])
        window.transient(self.root)
        window.geometry("760x680")
        state = {
            "indice": attempt["indice"] if attempt else 0,
            "respuestas": attempt["respuestas"] if attempt else {},
            "evaluations": attempt.get("evaluaciones", {}) if attempt else {},
            "busy": False,
            "answer_pending": False,
            "answer_error": "",
            "progress_pending": False,
            "progress_target": None,
            "progress_after_id": None,
        }
        window.protocol(
            "WM_DELETE_WINDOW",
            lambda: self._close_quiz_window(window, quiz, state),
        )
        self._render_quiz_page(window, quiz, state)

    def _render_quiz_page(self, window, quiz, state):
        state.pop("response_widget", None)
        for child in window.winfo_children():
            child.destroy()
        indice = state["indice"]
        pagina = quiz["paginas"][indice]
        header = self._card(window)
        header.pack(fill="x", padx=20, pady=(20, 10))
        self._label(header, quiz["quiz_titulo"], size=14, weight="bold").pack(
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
            respuesta_seleccionada = state["respuestas"].get(pagina["id"])
            evaluacion = state["evaluations"].get(pagina["id"])
            for letra, texto in pagina["alternativas"].items():
                selected = respuesta_seleccionada == letra
                button_color = COLORS["surface_light"]
                if selected and evaluacion:
                    button_color = COLORS[
                        "green" if evaluacion["correcta"] else "red"
                    ]
                elif selected or state["answer_pending"]:
                    button_color = COLORS["accent"]
                button = tk.Button(
                    content,
                    text=f"{letra}    {texto}",
                    anchor="w",
                    command=lambda key=letra: self._select_quiz_answer(
                        window, quiz, state, key
                    ),
                    bg=button_color,
                    fg=COLORS["text"],
                    activebackground=COLORS["accent_light"],
                    activeforeground="white",
                    relief="flat",
                    padx=15,
                    pady=12,
                    font=(FONT, 10),
                    cursor="hand2",
                    state=(
                        "disabled"
                        if (
                            respuesta_seleccionada
                            or state["answer_pending"]
                            or state["progress_pending"]
                        )
                        else "normal"
                    ),
                )
                button.pack(fill="x", padx=22, pady=5)
            if respuesta_seleccionada:
                feedback = evaluacion
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
            if state["progress_pending"]:
                response.configure(state="disabled")
            response.bind(
                "<KeyRelease>",
                lambda _event: self._schedule_quiz_progress_save(
                    window, quiz, state
                ),
            )
            state["response_widget"] = response
        if feedback:
            self._label(
                content,
                feedback["retroalimentacion"],
                color=COLORS["green"] if feedback["correcta"] else COLORS["red"],
                wraplength=660,
                justify="left",
            ).pack(anchor="w", padx=22, pady=12)
        if state["answer_error"]:
            self._label(content, state["answer_error"], color=COLORS["red"]).pack(
                anchor="w", padx=22, pady=8
            )
        if state["progress_pending"]:
            self._label(content, "Guardando avance…", color=COLORS["accent_light"]).pack(
                anchor="w", padx=22, pady=8
            )
        footer = tk.Frame(window, bg=COLORS["background"])
        footer.pack(fill="x", padx=20, pady=(8, 20))
        progress_locked = state["answer_pending"] or state["progress_pending"]
        previous_button = self._button(
            footer,
            "Anterior",
            lambda: self._move_quiz(window, quiz, state, -1),
        )
        previous_button.pack(side="left")
        if indice == 0 or progress_locked:
            previous_button.disabled = True
            previous_button._draw()
        final = indice == len(quiz["paginas"]) - 1
        next_button = self._button(
            footer,
            "Finalizar" if final else "Siguiente",
            lambda: self._finish_quiz(window, quiz, state)
            if final
            else self._move_quiz(window, quiz, state, 1),
            primary=True,
        )
        next_button.pack(side="right")
        if progress_locked:
            next_button.disabled = True
            next_button._draw()

    def _select_quiz_answer(self, window, quiz, state, key):
        if state["answer_pending"] or state["progress_pending"]:
            return
        pagina = quiz["paginas"][state["indice"]]
        if pagina["id"] in state["respuestas"]:
            return
        indice = state["indice"]
        pregunta_id = pagina["id"]
        state["answer_pending"] = True
        state["answer_error"] = ""
        self._render_quiz_page(window, quiz, state)
        worker = threading.Thread(
            target=self._evaluate_quiz_answer_worker,
            args=(window, quiz, state, indice, pregunta_id, key),
            daemon=True,
        )
        worker.start()

    def _evaluate_quiz_answer_worker(
        self, window, quiz, state, indice, pregunta_id, key
    ):
        try:
            resultado = seleccionar_respuesta_alternativa(
                quiz,
                indice,
                dict(state["respuestas"]),
                pregunta_id,
                key,
            )
            self.event_queue.put(
                ("quiz_answer_evaluated", (window, quiz, state, resultado))
            )
        except Exception as error:
            self.event_queue.put(
                ("quiz_answer_error", (window, quiz, state, str(error)))
            )

    def _handle_quiz_answer_result(self, window, quiz, state, result):
        if not window.winfo_exists():
            return
        state["respuestas"] = result["respuestas"]
        state["evaluations"][quiz["paginas"][state["indice"]]["id"]] = result
        state["answer_pending"] = False
        self._render_quiz_page(window, quiz, state)

    def _handle_quiz_answer_error(self, window, quiz, state, message):
        if not window.winfo_exists():
            return
        state["answer_pending"] = False
        state["answer_error"] = f"No se pudo guardar la respuesta: {message}"
        self._render_quiz_page(window, quiz, state)

    def _move_quiz(self, window, quiz, state, step):
        if state["answer_pending"] or state["progress_pending"]:
            return
        self._capture_development_answer(quiz, state)
        target_index = state["indice"] + step
        self._persist_quiz_progress(window, quiz, state, target_index, "move")

    def _persist_quiz_progress(self, window, quiz, state, target_index, action):
        state["progress_pending"] = True
        state["progress_target"] = target_index
        self._render_quiz_page(window, quiz, state)
        worker = threading.Thread(
            target=self._save_quiz_progress_worker,
            args=(
                window,
                quiz,
                state,
                target_index,
                dict(state["respuestas"]),
                action,
            ),
            daemon=True,
        )
        worker.start()

    def _schedule_quiz_progress_save(self, window, quiz, state):
        if state["progress_pending"]:
            return
        previous_id = state.get("progress_after_id")
        if previous_id:
            window.after_cancel(previous_id)
        state["progress_after_id"] = window.after(
            600,
            lambda: self._autosave_quiz_progress(window, quiz, state),
        )

    def _autosave_quiz_progress(self, window, quiz, state):
        state["progress_after_id"] = None
        if state["progress_pending"] or not window.winfo_exists():
            return
        self._capture_development_answer(quiz, state)
        response_widget = state.get("response_widget")
        if response_widget and response_widget.winfo_exists():
            response_widget.configure(state="disabled")
        state["progress_pending"] = True
        worker = threading.Thread(
            target=self._save_quiz_progress_worker,
            args=(
                window,
                quiz,
                state,
                state["indice"],
                dict(state["respuestas"]),
                "autosave",
            ),
            daemon=True,
        )
        worker.start()

    def _save_quiz_progress_worker(
        self, window, quiz, state, target_index, respuestas, action
    ):
        try:
            respuestas_guardadas = guardar_progreso_quiz(
                quiz,
                target_index,
                respuestas,
            )
            self.event_queue.put(
                (
                    "quiz_progress_saved",
                    (
                        window,
                        quiz,
                        state,
                        target_index,
                        respuestas_guardadas,
                        action,
                    ),
                )
            )
        except Exception as error:
            self.event_queue.put(
                ("quiz_progress_error", (window, quiz, state, str(error)))
            )

    def _handle_quiz_progress_saved(
        self, window, quiz, state, target_index, respuestas, action
    ):
        if not window.winfo_exists():
            return
        state["progress_pending"] = False
        state["respuestas"] = respuestas
        if action == "autosave":
            response_widget = state.get("response_widget")
            if response_widget and response_widget.winfo_exists():
                response_widget.configure(state="normal")
            state["answer_error"] = ""
            return
        if action == "close":
            window.destroy()
            return
        state["indice"] = target_index
        self._render_quiz_page(window, quiz, state)

    def _handle_quiz_progress_error(self, window, quiz, state, message):
        if not window.winfo_exists():
            return
        state["progress_pending"] = False
        state["answer_error"] = f"No se pudo guardar el avance: {message}"
        response_widget = state.get("response_widget")
        if response_widget and response_widget.winfo_exists():
            response_widget.configure(state="normal")
        self._render_quiz_page(window, quiz, state)

    def _capture_development_answer(self, quiz, state):
        pagina = quiz["paginas"][state["indice"]]
        widget = state.get("response_widget")
        if pagina["tipo"] == "desarrollo" and widget and widget.winfo_exists():
            answer = widget.get("1.0", "end").strip()
            if answer:
                state["respuestas"][pagina["id"]] = answer
            else:
                state["respuestas"].pop(pagina["id"], None)

    def _close_quiz_window(self, window, quiz, state):
        if state["answer_pending"] or state["progress_pending"]:
            return
        self._cancel_quiz_progress_save(window, state)
        self._capture_development_answer(quiz, state)
        self._persist_quiz_progress(window, quiz, state, state["indice"], "close")

    def _finish_quiz(self, window, quiz, state):
        if state["answer_pending"] or state["progress_pending"]:
            return
        self._cancel_quiz_progress_save(window, state)
        self._capture_development_answer(quiz, state)
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

    def _cancel_quiz_progress_save(self, window, state):
        after_id = state.pop("progress_after_id", None)
        if after_id:
            window.after_cancel(after_id)

    def _evaluate_quiz_worker(self, quiz, respuestas, window):
        try:
            # Determinar origen: barra_lateral es el flujo actual
            resultado = self.chat.finalizar_quiz(
                quiz,
                respuestas,
                origen="barra_lateral",
            )
            # Adaptar a estructura esperada por UI
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
            text=f"Resultado general: {resultado['porcentaje_total']}%",
            bg=COLORS["background"],
            fg=COLORS["green"],
            font=(FONT, 20, "bold"),
        ).pack(anchor="w", padx=24, pady=(22, 12))
        if resultado.get("feedback_final"):
            tk.Label(
                window,
                text=resultado["feedback_final"],
                bg=COLORS["background"],
                fg=COLORS["text"],
                font=(FONT, 10),
                justify="left",
                wraplength=680,
            ).pack(anchor="w", padx=24, pady=(0, 12))
        if resultado.get("porcentaje_desarrollo") is not None:
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
        paginas = {pagina["id"]: pagina for pagina in quiz["paginas"]}
        for item in resultado["retroalimentacion"]:
            pagina = paginas.get(item["pregunta_id"])
            if pagina is None:
                continue
            if item["tipo"] == "alternativa":
                etiqueta = "Correcta" if item["correcta"] else "Incorrecta"
            else:
                etiqueta = f"{item['porcentaje']}% de acierto"
            tk.Label(
                frame,
                text=f"{pagina['pregunta']} {etiqueta} · {item['retroalimentacion']}",
                bg=COLORS["surface"],
                fg=COLORS["text"],
                font=(FONT, 9),
                justify="left",
                wraplength=680,
                padx=14,
                pady=10,
            ).pack(fill="x", pady=5)
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
