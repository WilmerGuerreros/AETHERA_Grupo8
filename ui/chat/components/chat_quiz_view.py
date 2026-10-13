"""Quiz interactivo incrustado en una respuesta del asistente."""

import threading
import tkinter as tk

from ...tema import COLORS, FONT
from ...quiz.logica import QuizLogic
from dominio.quices import QuizSession, validar_test


class ChatQuizView:
    def _render_chat_quiz(self, parent, quiz):
        quiz = validar_test(quiz)
        session = QuizSession(quiz)
        state = {"index": 0, "answers": {}, "text": None}
        shell = tk.Frame(
            parent,
            bg=COLORS["surface_light"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        shell.pack(fill="x", padx=16, pady=(0, 16))
        header = tk.Frame(shell, bg=COLORS["surface_light"])
        header.pack(fill="x", padx=14, pady=(12, 8))
        title = tk.Label(
            header,
            text=quiz["test_titulo"],
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
            text_widget = state.pop("text", None)
            if page["tipo"] == "desarrollo" and text_widget:
                answer = text_widget.get("1.0", "end").strip()
                if answer:
                    state["answers"][page["id"]] = answer
                    session.guardar_respuesta_desarrollo(page["id"], answer)
                else:
                    state["answers"].pop(page["id"], None)

        def draw_page():
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
                for letter, option in page["alternativas"].items():
                    selected = state["answers"].get(page["id"]) == letter
                    button = tk.Button(
                        content,
                        text=f"{letter}    {option}",
                        anchor="w",
                        command=lambda key=letter: select_answer(key),
                        bg=COLORS["accent"] if selected else COLORS["background"],
                        fg=COLORS["text"],
                        activebackground=COLORS["accent_light"],
                        activeforeground="white",
                        relief="flat",
                        padx=12,
                        pady=8,
                        font=(FONT, 9),
                        cursor="hand2",
                    )
                    button.pack(fill="x", pady=3)
                selected = state["answers"].get(page["id"])
                if selected:
                    feedback_text = page["retroalimentacion"][selected]
                    feedback_color = (
                        COLORS["green"]
                        if selected == page["respuesta_correcta"]
                        else COLORS["yellow"]
                    )
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
                state["text"] = text_widget
            previous = tk.Button(
                footer,
                text="Anterior",
                command=lambda: move(-1),
                state="normal" if index else "disabled",
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
                bg=COLORS["accent"],
                fg="white",
                activebackground=COLORS["accent_light"],
                relief="flat",
                padx=14,
                pady=7,
                font=(FONT, 9, "bold"),
            ).pack(side="right")

        def select_answer(letter):
            page = quiz["paginas"][state["index"]]
            state["answers"][page["id"]] = letter
            session.responder_alternativa(page["id"], letter)
            draw_page()

        def move(offset):
            save_development()
            state["index"] += offset
            draw_page()

        def finish():
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
            worker = threading.Thread(
                target=evaluate,
                daemon=True,
            )
            worker.start()

        def evaluate():
            try:
                result = QuizLogic(self.chat.motor).evaluar(quiz, state["answers"])
                self.event_queue.put(("chat_quiz_evaluated", (shell, quiz, result)))
            except Exception as error:
                self.event_queue.put(("chat_quiz_evaluation_error", (shell, str(error))))

        draw_page()
        return shell

    def _show_chat_quiz_results(self, shell, quiz, result):
        if not shell.winfo_exists():
            return
        for child in shell.winfo_children():
            child.destroy()
        tk.Label(
            shell,
            text=(
                f"Puntaje alternativas: {result['puntaje']}%"
                if result["puntaje"] is not None
                else "Quiz sin preguntas de alternativa"
            ),
            bg=COLORS["surface_light"],
            fg=COLORS["green"],
            font=(FONT, 11, "bold"),
        ).pack(anchor="w", padx=14, pady=(12, 8))
        if result["porcentaje_desarrollo"] is not None:
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
            label = (
                "Correcta" if item.get("correcta") else "Incorrecta"
            ) if "correcta" in item else f"{item['porcentaje']}% de acierto"
            tk.Label(
                shell,
                text=f"{pages[item['pregunta_id']]['pregunta']}\n{label} · "
                f"{item['retroalimentacion']}",
                bg=COLORS["surface_light"],
                fg=COLORS["text"],
                font=(FONT, 9),
                wraplength=520,
                justify="left",
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
