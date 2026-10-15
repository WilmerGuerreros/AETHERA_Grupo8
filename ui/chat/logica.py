"""Coordinación de turnos, archivos adjuntos y mensajes."""

import queue
import os
import re
import logging
from datetime import datetime

from core.chat_manager import title_from_message
from core.documents import extraer_texto_pdf
from core.quizzes import (
    listar_quices,
    quiz_desde_resultado_herramienta,
)
from ..tema import COLORS


class ChatLogic:
    @property
    def busy(self):
        """El turno vive en el modelo, no en los widgets de la sección."""
        return self.chat_store.ocupado

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
                "name": os.path.basename(ruta),
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
            self.tasks.lanzar(
                "extraer_pdf",
                lambda _tarea, doc=document: self._extract_pdf_in_background(
                    doc["id"], doc["path"]
                ),
                contexto={"pdf_id": document["id"], "nombre": document["name"]},
            )

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
        session = self.chat_manager.sessions[self._active_chat_id]
        if session.title == "Nuevo chat":
            self.chat_manager.rename_session(
                session.chat_id,
                title_from_message(text),
            )
            self._sync_chat_selector()
        self._remove_pdf()
        self.chat_store.iniciar_turno()
        self.send_button.configure(state="disabled")
        self.status_label = self.chat_status_label
        self.status_base = f"✦  {self.chat_store.estado}"
        self.status_label.configure(
            text=self.status_base,
            fg=COLORS["accent_light"],
        )
        self._typing_phase = 0
        self._pulse_typing_indicator()
        self.tasks.lanzar(
            "turno_chat",
            lambda _tarea, chat_id=session.chat_id, conversation=session.conversation:
                self._run_chat_turn(chat_id, conversation, text),
            contexto={"texto": text},
        )

    def _run_chat_turn(self, chat_id, conversation=None, text=None):
        if text is None:
            text = chat_id
            chat_id = getattr(self, "_active_chat_id", None)
            conversation = self.chat

        def emit(event, value=None):
            if chat_id is None:
                self.event_queue.put((event, value))
            else:
                self.event_queue.put(("chat", chat_id, event, value))

        try:
            history_start = len(conversation.historial)
            for event_type, value in conversation.procesar_turno(text):
                if event_type == "token":
                    emit("token", value)
                elif event_type == "status":
                    emit("status", value)
            quizzes_generados = {}
            for message in conversation.historial[history_start:]:
                if message.get("role") != "tool" or message.get("name") != "crear_quiz":
                    continue
                quiz = quiz_desde_resultado_herramienta(message.get("content", ""))
                if quiz is not None:
                    quizzes_generados[quiz["quiz_id"]] = quiz
            for quiz in quizzes_generados.values():
                emit("quiz_generated", quiz)
            if chat_id is not None:
                self.chat_manager.save_history(chat_id)
            emit("complete")
        except Exception as error:
            if chat_id is not None:
                try:
                    self.chat_manager.save_history(chat_id)
                except Exception as persistence_error:
                    error = RuntimeError(
                        f"{error}\nNo se pudo guardar el historial del chat: "
                        f"{persistence_error}"
                    )
            emit("error", str(error))

    def _listar_quices_seguro(self):
        """Lista los quizzes sin que un archivo dañado rompa el chat."""
        try:
            return listar_quices()
        except (OSError, ValueError):
            logging.exception("No se pudieron listar los quizzes guardados.")
            return []

    def _process_queue(self):
        try:
            while True:
                queued = self.event_queue.get_nowait()
                if len(queued) == 4 and queued[0] == "chat":
                    _, chat_id, event, value = queued
                    self._handle_chat_event(chat_id, event, value)
                    continue
                event, value = queued
                if event in {
                    "token",
                    "status",
                    "complete",
                    "error",
                    "quiz_generated",
                }:
                    self._handle_chat_event(
                        getattr(self, "_active_chat_id", None),
                        event,
                        value,
                    )
                    continue
                if event == "services":
                    self._display_services(*value)
                elif event == "pdf_loaded":
                    self._handle_pdf_loaded(*value)
                elif event == "pdf_error":
                    self._handle_pdf_error(*value)
                elif event == "chat_quiz_evaluated":
                    self._show_chat_quiz_results(*value)
                elif event == "chat_quiz_evaluation_error":
                    self._show_chat_quiz_error(*value)
                elif event == "chat_quiz_answer_evaluated":
                    self._handle_chat_quiz_answer_result(*value)
                elif event == "chat_quiz_answer_error":
                    self._handle_chat_quiz_answer_error(*value)
                elif event == "quiz_answer_evaluated":
                    self._handle_quiz_answer_result(*value)
                elif event == "quiz_answer_error":
                    self._handle_quiz_answer_error(*value)
                elif event == "quiz_progress_saved":
                    self._handle_quiz_progress_saved(*value)
                elif event == "quiz_progress_error":
                    self._handle_quiz_progress_error(*value)
                elif event == "chat_quiz_progress_saved":
                    self._handle_chat_quiz_progress_saved(*value)
                elif event == "chat_quiz_progress_error":
                    self._handle_chat_quiz_progress_error(*value)
                elif event == "quiz_evaluated":
                    self._show_quiz_results(*value)
                elif event == "quiz_evaluation_error":
                    self._show_quiz_evaluation_error(*value)
                elif event == "tarea_actualizada":
                    self._handle_tarea_actualizada(value)
        except queue.Empty:
            pass
        self._process_after_id = self.root.after(80, self._process_queue)

    def _handle_chat_event(self, chat_id, event, value):
        stores = getattr(self, "_chat_stores", {})
        store = stores.get(chat_id)
        if store is None and chat_id == getattr(self, "_active_chat_id", chat_id):
            store = getattr(self, "chat_store", None)
        if store is None:
            return
        is_active = chat_id == getattr(self, "_active_chat_id", chat_id)
        if event == "token":
            store.agregar_token(value)
            if is_active and self.current_page == "Asistente IA":
                self._refresh_stream_bubble()
        elif event == "status":
            store.actualizar_estado(value)
            if is_active:
                self._set_status(value)
        elif event == "quiz_generated":
            store.agregar_quiz(value)
        elif event == "complete":
            if is_active and self.current_page == "Asistente IA":
                self._attach_stream_quizzes()
            store.finalizar_turno()
            if is_active:
                self._finish_chat_turn()
            if hasattr(self, "_sync_chat_selector"):
                self._sync_chat_selector()
        elif event == "error":
            mensaje = (
                "No pude completar la respuesta. Inténtalo de nuevo."
                f"\n\nDetalle: {value}"
            )
            store.marcar_error(mensaje)
            if is_active and self.current_page == "Asistente IA":
                self._append_message("assistant", mensaje)
            if is_active:
                self._finish_chat_turn()
            if hasattr(self, "_sync_chat_selector"):
                self._sync_chat_selector()

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
        typing_after_id = getattr(self, "_typing_after_id", None)
        if typing_after_id:
            self.root.after_cancel(typing_after_id)
            self._typing_after_id = None
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
        if self.current_page == "Asistente IA" and hasattr(self, "canvas"):
            self.root.after_idle(lambda: self._animate_scroll_to_bottom(self.canvas))

    def _attach_stream_quizzes(self):
        """Incrusta en la respuesta los quizzes generados durante el turno."""
        quizzes = self.chat_store.quices_del_turno()
        if not quizzes:
            return
        if hasattr(self, "stream_bubble") and self.stream_bubble.winfo_exists():
            if self._attach_stream_quiz():
                return
            for quiz in quizzes:
                self._render_chat_quiz(self.stream_bubble, quiz)
        elif hasattr(self, "message_list"):
            for quiz in quizzes:
                self._append_generated_quiz(quiz)
