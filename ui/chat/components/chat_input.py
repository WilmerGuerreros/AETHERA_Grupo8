"""Campo de entrada y controles de adjuntos del chat."""

import tkinter as tk
from tkinter import filedialog

from ...tema import COLORS, FONT


class ChatInput:
    def _choose_pdf(self):
        rutas = filedialog.askopenfilenames(
            parent=self.root,
            title="Seleccionar documentos PDF",
            filetypes=(("Documentos PDF", "*.pdf"),),
        )
        if not rutas:
            return
        self._attach_pdfs(rutas)

    def _sync_pdf_controls(self):
        if (
            not hasattr(self, "pdf_status_label")
            or not self.pdf_status_label.winfo_exists()
        ):
            return
        loading = [
            document
            for document in self._attached_pdfs
            if document["state"] == "loading"
        ]
        errors = [
            document
            for document in self._attached_pdfs
            if document["state"] == "error"
        ]
        ready_count = sum(
            document["state"] == "ready" for document in self._attached_pdfs
        )
        if loading:
            self._pdf_status_text = (
                f"Procesando {len(loading)} PDF"
                f"{'s' if len(loading) != 1 else ''}…"
            )
            self._pdf_status_color = COLORS["accent_light"]
        elif errors:
            failed_names = "; ".join(
                f"{document['name']}: {document['error']}"
                for document in errors
            )
            self._pdf_status_text = (
                f"No se pudo procesar {failed_names}. Quita esos archivos para continuar."
            )
            self._pdf_status_color = COLORS["red"]
        elif ready_count:
            self._pdf_status_text = (
                f"{ready_count} PDF listo"
                f"{'s' if ready_count != 1 else ''}"
            )
            self._pdf_status_color = COLORS["green"]
        else:
            self._pdf_status_text = "Sin documento adjunto"
            self._pdf_status_color = COLORS["muted"]
        self.pdf_status_label.configure(
            text=self._pdf_status_text,
            fg=self._pdf_status_color,
        )
        self.remove_pdf_button.configure(
            state="normal" if self._attached_pdfs else "disabled"
        )
        for child in self.pdf_attachments_frame.winfo_children():
            child.destroy()
        for document in self._attached_pdfs:
            self._create_pdf_chip(
                self.pdf_attachments_frame,
                document["name"],
                remove_command=lambda request_id=document["id"]: self._remove_pdf(
                    request_id
                ),
                error=document["state"] == "error",
            )

    def _create_pdf_chip(self, parent, name, remove_command=None, error=False):
        border = COLORS["red"] if error else COLORS["accent"]
        chip = self._card(
            parent,
            bg=COLORS["surface_light"],
            border=border,
            radius=17,
            gradient=("#222e4c", "#1b2440", "#2b2454"),
        )
        chip_name = name if len(name) <= 30 else f"{name[:13]}…{name[-13:]}"
        chip.configure(cursor="hand2" if remove_command else "arrow")
        badge = tk.Label(
            chip,
            text="PDF",
            bg=COLORS["accent"],
            fg="white",
            font=(FONT, 8, "bold"),
            padx=6,
            pady=3,
        )
        badge.pack(side="left", padx=(10, 6), pady=6)
        label = tk.Label(
            chip,
            text=chip_name,
            bg=COLORS["surface_light"],
            fg=COLORS["text"],
            font=(FONT, 9),
        )
        label.pack(side="left", pady=6)
        if remove_command:
            remove = tk.Label(
                chip,
                text="×",
                bg=COLORS["surface_light"],
                fg=COLORS["muted"],
                font=(FONT, 13, "bold"),
                cursor="hand2",
                padx=8,
            )
            remove.pack(side="left")
            remove.bind("<Button-1>", lambda _event: remove_command())
            remove.bind(
                "<Enter>",
                lambda _event: remove.configure(fg=COLORS["red"]),
            )
            remove.bind(
                "<Leave>",
                lambda _event: remove.configure(fg=COLORS["muted"]),
            )
        chip.grid(row=0, column=0, padx=(0, 8), pady=3, sticky="w")
        self._layout_attachment_chips(parent)
        self._animate_card_in(chip, grid=True)

    @staticmethod
    def _layout_attachment_chips(parent):
        available_width = max(1, parent.winfo_width())
        current_x = 0
        row = 0
        column = 0
        for chip in parent.winfo_children():
            chip_width = chip.winfo_reqwidth() + 8
            if current_x and current_x + chip_width > available_width:
                row += 1
                column = 0
                current_x = 0
            chip.grid_configure(row=row, column=column)
            current_x += chip_width
            column += 1

    def _render_chat_input(self):
        composer = self._card(self.content)
        composer.pack(fill="x", pady=(12, 0))
        attachment_bar = tk.Frame(composer, bg=COLORS["surface"])
        attachment_bar.pack(fill="x", padx=10, pady=(8, 0))
        self._button(
            attachment_bar,
            "Adjuntar PDF",
            self._choose_pdf,
        ).pack(side="left")
        self.pdf_status_label = self._label(
            attachment_bar,
            "Sin documento adjunto",
            size=9,
            color=COLORS["muted"],
            bg=COLORS["surface"],
            wraplength=520,
            justify="left",
        )
        self.pdf_status_label.pack(side="left", padx=12)
        self.remove_pdf_button = self._button(
            attachment_bar,
            "Quitar todos",
            self._remove_pdf,
        )
        self.remove_pdf_button.pack(side="right")
        self.pdf_attachments_frame = tk.Frame(composer, bg=COLORS["surface"])
        self.pdf_attachments_frame.pack(fill="x", padx=14, pady=(5, 0))
        self.pdf_attachments_frame.bind(
            "<Configure>",
            lambda event: self._layout_attachment_chips(event.widget),
            add="+",
        )
        self._sync_pdf_controls()
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
        self._bind_native_widget_animations(self.message_input)
        self.message_input.lift()
        self.message_input.bind(
            "<Button-1>",
            lambda _event: self.message_input.focus_set(),
            add="+",
        )
        self.message_input.bind("<Control-Return>", self._send_from_shortcut)
        send_button = self._button(composer, "Enviar  ↑", self._send_message, primary=True)
        send_button.pack(side="right", padx=10, pady=10)
        self.send_button = send_button
        if self.busy:
            self.send_button.configure(state="disabled")
