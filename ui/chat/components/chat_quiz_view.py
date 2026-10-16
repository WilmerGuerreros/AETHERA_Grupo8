"""Quiz interactivo incrustado en una respuesta del asistente."""

import logging
import tkinter as tk
from typing import Any, Protocol

from ...tema import COLORS, FONT
from core.quizzes import (
    cargar_intento,
    guardar_progreso_quiz,
    seleccionar_respuesta_alternativa,
    validar_quiz,
)


class _ChatQuizHost(Protocol):
    chat: Any
    chat_manager: Any
    event_queue: Any
    tasks: Any
    _active_chat_id: str


class ChatQuizView(_ChatQuizHost):
    def _render_chat_quiz(self, parent, quiz):
        quiz = validar_quiz(quiz)
        chat_id = self._active_chat_id
        conversation = self.chat
        try:
            attempt = cargar_intento(quiz)
        except (OSError, ValueError) as error:
            tk.Label(
                parent,
                text=f"No se pudo cargar el avance del quiz: {error}",
                bg=COLORS["surface_light"],
                fg=COLORS["red"],
                font=(FONT, 9),
                wraplength=520,
                justify="left",
            ).pack(fill="x", padx=16, pady=(0, 16))
            return None
        state = {
            "chat_id": chat_id,
            "conversation": conversation,
            "index": attempt["indice"] if attempt else 0,
            "answers": attempt["respuestas"] if attempt else {},
            "evaluations": attempt.get("evaluaciones", {}) if attempt else {},
            "text": None,
            "answer_pending": False,
            "answer_error": "",
            "progress_pending": False,
            "progress_target": None,
            "progress_after_id": None,
            "progress_dirty": False,
        }
        shell = tk.Frame(
            parent,
            bg=COLORS["surface_light"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        sessions = getattr(self, "_active_chat_quiz_sessions", [])
        sessions.append((shell, quiz, state))
        self._active_chat_quiz_sessions = sessions
        shell.pack(fill="x", padx=16, pady=(0, 16))
        header = tk.Frame(shell, bg=COLORS["surface_light"])
        header.pack(fill="x", padx=14, pady=(12, 8))
        title = tk.Label(
            header,
            text=quiz["quiz_titulo"],
            bg=COLORS["surface_light"],
            fg=COLORS["text"],
            font=(FONT, 11, "bold"),
            wraplength=500,
            justify="left",
        )
        title.pack(anchor="w")
        progress = tk.Label(
            header,
            bg=COLORS["surface_light"],
            fg=COLORS["accent_light"],
            font=(FONT, 9, "bold"),
        )
        progress.pack(anchor="w", pady=(4, 0))
        content = tk.Frame(shell, bg=COLORS["surface_light"])
        content.pack(fill="x", padx=14)
        footer = tk.Frame(shell, bg=COLORS["surface_light"])
        footer.pack(fill="x", padx=14, pady=(10, 14))

        def save_development():
            page = quiz["paginas"][state["index"]]
            text_widget = state.get("text")
            if (
                page["tipo"] == "desarrollo"
                and text_widget
                and text_widget.winfo_exists()
            ):
                answer = text_widget.get("1.0", "end").strip()
                if answer:
                    state["answers"][page["id"]] = answer
                else:
                    state["answers"].pop(page["id"], None)
                state["progress_dirty"] = True

        def draw_page():
            state.pop("text", None)
            for child in content.winfo_children():
                child.destroy()
            for child in footer.winfo_children():
                child.destroy()
            index = state["index"]
            page = quiz["paginas"][index]
            progress.configure(text=f"Pregunta {index + 1} de {len(quiz['paginas'])}")
            tk.Label(
                content,
                text=page["pregunta"],
                bg=COLORS["surface_light"],
                fg=COLORS["text"],
                font=(FONT, 10, "bold"),
                wraplength=520,
                justify="left",
            ).pack(anchor="w", pady=(8, 12))
            if page["tipo"] == "alternativa":
                selected_letter = state["answers"].get(page["id"])
                evaluation = state["evaluations"].get(page["id"])
                for letter, option in page["alternativas"].items():
                    selected = selected_letter == letter
                    button_color = COLORS["background"]
                    if selected and evaluation:
                        button_color = COLORS[
                            "green" if evaluation["correcta"] else "red"
                        ]
                    elif selected or state["answer_pending"]:
                        button_color = COLORS["accent"]
                    button = tk.Button(
                        content,
                        text=f"{letter}    {option}",
                        anchor="w",
                        command=lambda key=letter: select_answer(key),
                        bg=button_color,
                        fg=COLORS["text"],
                        activebackground=COLORS["accent_light"],
                        activeforeground="white",
                        relief="flat",
                        padx=12,
                        pady=8,
                        font=(FONT, 9),
                        cursor="hand2",
                        state=(
                            "disabled"
                            if (
                                selected_letter
                                or state["answer_pending"]
                                or state["progress_pending"]
                            )
                            else "normal"
                        ),
                    )
                    button.pack(fill="x", pady=3)
                if selected_letter:
                    feedback_text = (
                        evaluation["retroalimentacion"] if evaluation else ""
                    )
                    feedback_color = COLORS[
                        "green" if evaluation and evaluation["correcta"] else "red"
                    ]
                    if feedback_text:
                        tk.Label(
                            content,
                            text=feedback_text,
                            bg=COLORS["surface_light"],
                            fg=feedback_color,
                            font=(FONT, 9),
                            wraplength=520,
                            justify="left",
                        ).pack(anchor="w", pady=(8, 2))
            else:
                text_widget = tk.Text(
                    content,
                    height=5,
                    wrap="word",
                    bg=COLORS["background"],
                    fg=COLORS["text"],
                    insertbackground=COLORS["text"],
                    relief="flat",
                    font=(FONT, 9),
                    padx=10,
                    pady=8,
                )
                text_widget.pack(fill="x")
                text_widget.insert("1.0", state["answers"].get(page["id"], ""))
                if state["progress_pending"]:
                    text_widget.configure(state="disabled")
                text_widget.bind(
                    "<KeyRelease>",
                    lambda _event: self._schedule_chat_quiz_progress_save(
                        shell, quiz, state
                    ),
                )
                state["text"] = text_widget
            if state["answer_error"]:
                tk.Label(
                    content,
                    text=state["answer_error"],
                    bg=COLORS["surface_light"],
                    fg=COLORS["red"],
                    font=(FONT, 9),
                    wraplength=520,
                    justify="left",
                ).pack(anchor="w", pady=(8, 2))
            if state["progress_pending"]:
                tk.Label(
                    content,
                    text="Guardando avance…",
                    bg=COLORS["surface_light"],
                    fg=COLORS["accent_light"],
                    font=(FONT, 9),
                ).pack(anchor="w", pady=(8, 2))
            progress_locked = (
                state["answer_pending"] or state["progress_pending"]
            )
            previous = tk.Button(
                footer,
                text="Anterior",
                command=lambda: move(-1),
                state=(
                    "normal"
                    if index and not progress_locked
                    else "disabled"
                ),
                bg=COLORS["background"],
                fg=COLORS["text"],
                relief="flat",
                padx=12,
                pady=7,
                font=(FONT, 9),
            )
            previous.pack(side="left")
            last = index == len(quiz["paginas"]) - 1
            tk.Button(
                footer,
                text="Finalizar" if last else "Siguiente",
                command=finish if last else lambda: move(1),
                state="disabled" if progress_locked else "normal",
                bg=COLORS["accent"],
                fg="white",
                activebackground=COLORS["accent_light"],
                relief="flat",
                padx=14,
                pady=7,
                font=(FONT, 9, "bold"),
            ).pack(side="right")

        def select_answer(letter):
            if state["answer_pending"] or state["progress_pending"]:
                return
            page = quiz["paginas"][state["index"]]
            if page["id"] in state["answers"]:
                return
            state["answer_pending"] = True
            state["answer_error"] = ""
            index = state["index"]
            draw_page()
            self.tasks.lanzar(
                "evaluar_respuesta_quiz_chat",
                lambda _tarea: self._evaluate_chat_quiz_answer(
                    shell, quiz, state, index, page["id"], letter
                ),
            )

        def move(offset):
            if state["answer_pending"] or state["progress_pending"]:
                return
            self._cancel_chat_quiz_progress_save(shell, state)
            save_development()
            target_index = state["index"] + offset
            state["progress_pending"] = True
            state["progress_target"] = target_index
            draw_page()
            self.tasks.lanzar(
                "guardar_avance_quiz_chat",
                lambda _tarea: self._save_chat_quiz_progress(
                    shell,
                    quiz,
                    state,
                    target_index,
                    dict(state["answers"]),
                    "move",
                ),
            )

        def finish():
            if state["answer_pending"] or state["progress_pending"]:
                return
            self._cancel_chat_quiz_progress_save(shell, state)
            save_development()
            for child in shell.winfo_children():
                child.destroy()
            loading = tk.Label(
                shell,
                text="revisando respuestas",
                bg=COLORS["surface_light"],
                fg=COLORS["accent_light"],
                font=(FONT, 10, "bold"),
                padx=14,
                pady=18,
            )
            loading.pack(anchor="w")
            self.tasks.lanzar("evaluar_quiz_chat", lambda _tarea: evaluate())

        def evaluate():
            try:
                result = conversation.finalizar_quiz(
                    quiz,
                    dict(state["answers"]),
                    origen="chat",
                )
            except Exception as error:
                self.event_queue.put(("chat_quiz_evaluation_error", (shell, str(error))))
                return

            archive_error = self._archive_chat_quiz_result(
                chat_id,
                quiz,
                dict(state["answers"]),
                result,
            )
            self.event_queue.put(
                ("chat_quiz_evaluated", (shell, quiz, result, archive_error))
            )

        state["draw_page"] = draw_page
        draw_page()
        return shell

    def _save_chat_quiz_progress(
        self, shell, quiz, state, target_index, answers, action
    ):
        try:
            saved_answers = guardar_progreso_quiz(
                quiz,
                target_index,
                answers,
            )
            self.event_queue.put(
                (
                    "chat_quiz_progress_saved",
                    (shell, state, target_index, saved_answers, action),
                )
            )
        except Exception as error:
            self.event_queue.put(
                ("chat_quiz_progress_error", (shell, state, str(error)))
            )

    def _handle_chat_quiz_progress_saved(
        self, shell, state, target_index, answers, action
    ):
        if not shell.winfo_exists():
            return
        state["progress_pending"] = False
        state["progress_target"] = None
        state["progress_dirty"] = False
        state["answers"] = answers
        if action == "autosave":
            text_widget = state.get("text")
            if text_widget and text_widget.winfo_exists():
                text_widget.configure(state="normal")
            state["answer_error"] = ""
            return
        state["index"] = target_index
        state["draw_page"]()

    def _handle_chat_quiz_progress_error(self, shell, state, message):
        if not shell.winfo_exists():
            return
        state["progress_pending"] = False
        state["answer_error"] = f"No se pudo guardar el avance: {message}"
        text_widget = state.get("text")
        if text_widget and text_widget.winfo_exists():
            text_widget.configure(state="normal")
        state["draw_page"]()

    def _schedule_chat_quiz_progress_save(self, shell, quiz, state):
        if state["progress_pending"]:
            return
        state["progress_dirty"] = True
        previous_id = state.get("progress_after_id")
        if previous_id:
            shell.after_cancel(previous_id)
        state["progress_after_id"] = shell.after(
            600,
            lambda: self._autosave_chat_quiz_progress(shell, quiz, state),
        )

    def _autosave_chat_quiz_progress(self, shell, quiz, state):
        state["progress_after_id"] = None
        if state["progress_pending"] or not shell.winfo_exists():
            return
        page = quiz["paginas"][state["index"]]
        text_widget = state.get("text")
        if page["tipo"] != "desarrollo" or not text_widget:
            return
        answer = text_widget.get("1.0", "end").strip()
        if answer:
            state["answers"][page["id"]] = answer
        else:
            state["answers"].pop(page["id"], None)
        text_widget.configure(state="disabled")
        state["progress_pending"] = True
        self.tasks.lanzar(
            "guardar_avance_quiz_chat",
            lambda _tarea: self._save_chat_quiz_progress(
                shell,
                quiz,
                state,
                state["index"],
                dict(state["answers"]),
                "autosave",
            ),
        )

    def _cancel_chat_quiz_progress_save(self, shell, state):
        after_id = state.pop("progress_after_id", None)
        if after_id:
            shell.after_cancel(after_id)

    def _flush_chat_quiz_progress_before_navigation(self):
        """Persists dirty chat quiz drafts before their widgets are destroyed."""
        sessions = getattr(self, "_active_chat_quiz_sessions", [])
        active_sessions = []
        for shell, quiz, state in sessions:
            if not shell.winfo_exists():
                continue
            active_sessions.append((shell, quiz, state))
            self._cancel_chat_quiz_progress_save(shell, state)
            if state["answer_pending"]:
                continue
            if not state["progress_dirty"] and not state["progress_pending"]:
                continue

            page = quiz["paginas"][state["index"]]
            text_widget = state.get("text")
            if (
                page["tipo"] == "desarrollo"
                and text_widget
                and text_widget.winfo_exists()
            ):
                answer = text_widget.get("1.0", "end").strip()
                if answer:
                    state["answers"][page["id"]] = answer
                else:
                    state["answers"].pop(page["id"], None)

            target_index = state["index"]
            if state["progress_pending"] and state["progress_target"] is not None:
                target_index = state["progress_target"]
            try:
                state["answers"] = guardar_progreso_quiz(
                    quiz,
                    target_index,
                    state["answers"],
                )
            except Exception as error:
                state["progress_pending"] = False
                state["progress_target"] = None
                state["answer_error"] = f"No se pudo guardar el avance: {error}"
                state["draw_page"]()
                self._active_chat_quiz_sessions = active_sessions
                return False

            state["progress_pending"] = False
            state["progress_target"] = None
            state["progress_dirty"] = False

        self._active_chat_quiz_sessions = active_sessions
        return True

    def _evaluate_chat_quiz_answer(
        self, shell, quiz, state, index, question_id, answer
    ):
        try:
            result = seleccionar_respuesta_alternativa(
                quiz,
                index,
                dict(state["answers"]),
                question_id,
                answer,
            )
            self.event_queue.put(
                ("chat_quiz_answer_evaluated", (shell, quiz, state, result))
            )
        except Exception as error:
            self.event_queue.put(
                ("chat_quiz_answer_error", (shell, state, str(error)))
            )

    def _handle_chat_quiz_answer_result(self, shell, quiz, state, result):
        if not shell.winfo_exists():
            return
        question_id = quiz["paginas"][state["index"]]["id"]
        state["answers"] = result["respuestas"]
        state["evaluations"][question_id] = result
        state["answer_pending"] = False
        state["draw_page"]()

    def _handle_chat_quiz_answer_error(self, shell, state, message):
        if not shell.winfo_exists():
            return
        state["answer_pending"] = False
        state["answer_error"] = f"No se pudo guardar la respuesta: {message}"
        state["draw_page"]()

    def _archive_chat_quiz_result(self, chat_id, quiz, answers, result):
        try:
            self.chat_manager.save_quiz_result(
                chat_id,
                quiz,
                answers,
                result,
            )
        except (KeyError, OSError, TypeError, ValueError) as error:
            logging.exception("No se pudo archivar el resultado del quiz del chat.")
            return (
                "No se pudo archivar el resultado en ARCHIVOS GENERADOS: "
                f"{error}"
            )
        return None

    def _show_chat_quiz_results(
        self,
        shell,
        quiz,
        result,
        archive_error=None,
    ):
        if not shell.winfo_exists():
            return
        for child in shell.winfo_children():
            child.destroy()
        tk.Label(
            shell,
            text=f"Resultado general: {result['porcentaje_total']}%",
            bg=COLORS["surface_light"],
            fg=COLORS["green"],
            font=(FONT, 11, "bold"),
        ).pack(anchor="w", padx=14, pady=(12, 8))
        if archive_error:
            tk.Label(
                shell,
                text=archive_error,
                bg=COLORS["surface_light"],
                fg=COLORS["red"],
                font=(FONT, 9, "bold"),
                wraplength=520,
                justify="left",
            ).pack(anchor="w", padx=14, pady=(0, 8))
        if result.get("feedback_final"):
            self._create_formatted_message(
                shell,
                result["feedback_final"],
                background=COLORS["surface_light"],
                foreground=COLORS["text"],
                width=52,
                max_lines=None,
            ).pack(fill="x", anchor="w", padx=14, pady=(0, 8))
        if result.get("porcentaje_desarrollo") is not None:
            tk.Label(
                shell,
                text=(
                    "Desarrollo · promedio de acierto "
                    f"{result['porcentaje_desarrollo']}%"
                ),
                bg=COLORS["surface_light"],
                fg=COLORS["accent_light"],
                font=(FONT, 9, "bold"),
            ).pack(anchor="w", padx=14, pady=(0, 8))
        pages = {page["id"]: page for page in quiz["paginas"]}
        for item in result["retroalimentacion"]:
            page = pages.get(item["pregunta_id"])
            if page is None:
                continue
            if item["tipo"] == "alternativa":
                label = "Correcta" if item["correcta"] else "Incorrecta"
            else:
                label = f"{item['porcentaje']}% de acierto"
            self._create_formatted_message(
                shell,
                f"**{page['pregunta']}**\n**{label}** · "
                f"{item['retroalimentacion']}",
                background=COLORS["surface_light"],
                foreground=COLORS["text"],
                width=52,
                max_lines=None,
            ).pack(fill="x", anchor="w", padx=14, pady=5)

    def _show_chat_quiz_error(self, shell, message):
        if not shell.winfo_exists():
            return
        for child in shell.winfo_children():
            child.destroy()
        tk.Label(
            shell,
            text=f"No se pudieron revisar las respuestas: {message}",
            bg=COLORS["surface_light"],
            fg=COLORS["red"],
            font=(FONT, 9),
            wraplength=520,
            justify="left",
            padx=14,
            pady=14,
        ).pack(anchor="w")
