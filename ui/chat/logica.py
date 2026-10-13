"""Coordinación de turnos, archivos adjuntos y mensajes."""

import queue
import os
import re
import threading
from ..quiz.logica import quiz_desde_resultado_herramienta
from datetime import datetime
from pathlib import Path

from ..tema import COLORS
from ..utilidades import extraer_texto_pdf
from ..quiz.logica import QuizLogic, quiz_desde_resultado_herramienta


class ChatLogic:
    def _attach_pdfs(self, rutas):
        existing_paths = {
            os.path.normcase(os.path.abspath(document["path"]))
            for document in self._attached_pdfs
        }
        selected = []
        for ruta in rutas:
            normalized_path = os.path.normcase(os.path.abspath(ruta))
            if normalized_path in existing_paths:
                continue
            existing_paths.add(normalized_path)
            self._pdf_request_id += 1
            document = {
                "id": self._pdf_request_id,
                "name": Path(ruta).name,
                "path": ruta,
                "text": "",
                "state": "loading",
                "error": "",
            }
            self._attached_pdfs.append(document)
            selected.append(document)
        if not selected:
            return
        self._sync_pdf_controls()
        for document in selected:
            worker = threading.Thread(
                target=self._extract_pdf_in_background,
                args=(document["id"], document["path"]),
                daemon=True,
            )
            worker.start()

    def _extract_pdf_in_background(self, request_id, ruta):
        try:
            texto = extraer_texto_pdf(ruta)
            self.event_queue.put(("pdf_loaded", (request_id, texto)))
        except Exception as error:
            self.event_queue.put(("pdf_error", (request_id, str(error))))

    def _find_attached_pdf(self, request_id):
        return next(
            (
                document
                for document in self._attached_pdfs
                if document["id"] == request_id
            ),
            None,
        )

    def _handle_pdf_loaded(self, request_id, texto):
        document = self._find_attached_pdf(request_id)
        if document is None:
            return
        document["state"] = "ready"
        document["text"] = texto
        self._sync_pdf_controls()

    def _handle_pdf_error(self, request_id, error):
        document = self._find_attached_pdf(request_id)
        if document is None:
            return
        document["state"] = "error"
        document["error"] = error
        self._sync_pdf_controls()

    def _remove_pdf(self, request_id=None):
        if request_id is None:
            self._attached_pdfs.clear()
        else:
            self._attached_pdfs = [
                document
                for document in self._attached_pdfs
                if document["id"] != request_id
            ]
        self._sync_pdf_controls()

    def _user_message_preview(self, text):
        prompt, documents = self._split_user_message(text)
        if prompt:
            return prompt
        return ", ".join(document["name"] for document in documents)

    def _split_user_message(self, text):
        parts = re.split(r"(?:\A|\n\n|\n)document: ([^\r\n]*)\r?\n", text)
        if len(parts) == 1:
            return text, []
        prompt = parts[0]
        documents = [
            {"name": parts[index], "text": parts[index + 1]}
            for index in range(1, len(parts), 2)
        ]
        return prompt, documents

    def _compose_user_message(
        self, prompt, document_name=None, document_text="", documents=None
    ):
        attachments = list(documents or ())
        if document_name and document_text:
            attachments.insert(
                0,
                {"name": document_name, "text": document_text},
            )
        sections = [prompt] if prompt else []
        sections.extend(
            f"document: {document['name']}\n{document['text']}"
            for document in attachments
            if document.get("text")
        )
        return "\n\n".join(sections)

    def _send_from_shortcut(self, _event):
        self._send_message()
        return "break"

    def _send_message(self):
        if self.busy:
            return
        prompt = self.message_input.get("1.0", "end").strip()
        if any(document["state"] == "loading" for document in self._attached_pdfs):
            self.pdf_status_label.configure(
                text="Espera a que termine el procesamiento de los PDF.",
                fg=COLORS["yellow"],
            )
            return
        if any(document["state"] == "error" for document in self._attached_pdfs):
            self.pdf_status_label.configure(
                text="Quita los PDF con error antes de enviar.",
                fg=COLORS["red"],
            )
            return
        ready_documents = [
            document
            for document in self._attached_pdfs
            if document["state"] == "ready"
        ]
        if not prompt and not ready_documents:
            return
        text = self._compose_user_message(
            prompt,
            documents=ready_documents,
        )
        ahora = datetime.now()
        text = f"Fecha: {ahora:%d/%m/%Y} Hora: {ahora:%H:%M}\n{text}"
        self.message_input.delete("1.0", "end")
        self._append_message("user", text)
        self._remove_pdf()
        self.busy = True
        self._pending_chat_quizzes = []
        self.send_button.configure(state="disabled")
        self.status_label = self.chat_status_label
        self.status_base = "✦  GuIA está pensando"
        self.status_label.configure(
            text=self.status_base,
            fg=COLORS["accent_light"],
        )
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
            history_start = len(self.chat.historial)
            quizzes_before = {
                quiz["test_id"] for quiz in QuizLogic(self.chat.motor).listar_quices()
            }
            self.chat.procesar_turno(
                text,
                al_emitir_texto=lambda chunk: self.event_queue.put(("token", chunk)),
                al_actualizar_estado=lambda status: self.event_queue.put(("status", status)),
            )
            quizzes_after = QuizLogic(self.chat.motor).listar_quices()
            for quiz in quizzes_after:
                if quiz["test_id"] not in quizzes_before:
                    self.event_queue.put(("quiz_generated", quiz))
            for message in self.chat.historial[history_start:]:
                if message.get("role") != "tool" or message.get("name") != "crear_test":
                    continue
                quiz = quiz_desde_resultado_herramienta(message.get("content", ""))
                if quiz is not None:
                    self.event_queue.put(("quiz_generated", quiz))
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
                elif event == "services":
                    self._display_services(*value)
                elif event == "pdf_loaded":
                    self._handle_pdf_loaded(*value)
                elif event == "pdf_error":
                    self._handle_pdf_error(*value)
                elif event == "chat_quiz_evaluated":
                    self._show_chat_quiz_results(*value)
                elif event == "chat_quiz_evaluation_error":
                    self._show_chat_quiz_error(*value)
                elif event == "quiz_generated":
                    self._pending_chat_quizzes.append(value)
                elif event == "quiz_evaluated":
                    self._show_quiz_results(*value)
                elif event == "quiz_evaluation_error":
                    self._show_quiz_evaluation_error(*value)
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

    def _set_status(self, status):
        if hasattr(self, "status_label") and self.status_label.winfo_exists():
            self.status_base = f"✦  {status}"
            self.status_label.configure(
                text=self.status_base,
                fg=COLORS["accent_light"],
            )

    def _finish_chat_turn(self):
        if self.current_page == "Asistente IA":
            has_stream_quiz = self._attach_stream_quiz()
            if not has_stream_quiz:
                pending_quizzes = getattr(self, "_pending_chat_quizzes", [])
                if hasattr(self, "stream_bubble"):
                    for quiz in pending_quizzes:
                        self._render_chat_quiz(self.stream_bubble, quiz)
                elif hasattr(self, "message_list"):
                    for quiz in pending_quizzes:
                        self._append_generated_quiz(quiz)
        self._pending_chat_quizzes = []
        typing_after_id = getattr(self, "_typing_after_id", None)
        if typing_after_id:
            self.root.after_cancel(typing_after_id)
        self.busy = False
        if hasattr(self, "status_label") and self.status_label.winfo_exists():
            self.status_base = "●  Disponible"
            self.status_label.configure(
                text=self.status_base,
                fg=COLORS["green"],
            )
        if hasattr(self, "send_button") and self.send_button.winfo_exists():
            self.send_button.configure(state="normal")
        if hasattr(self, "stream_bubble"):
            del self.stream_bubble
            del self.stream_text
            del self.stream_content
        if self.current_page == "Asistente IA" and hasattr(self, "canvas"):
            self.root.after_idle(lambda: self._animate_scroll_to_bottom(self.canvas))
