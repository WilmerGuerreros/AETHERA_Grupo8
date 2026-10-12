"""Sección chat de la interfaz de Aethera."""

from .components import (
    COLORS,
    datetime,
    EMOJI_CHAR,
    FONT,
    INLINE_MARKDOWN,
    Image,
    ImageDraw,
    ImageFont,
    ImageTk,
    Path,
    _is_markdown_table_separator,
    _markdown_table_cells,
    extraer_texto_pdf,
    filedialog,
    math,
    os,
    queue,
    re,
    threading,
    tk,
    ttk,
)

class ChatSection:
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
            "GuIA te acompaña a organizarte; tú decides cómo avanzar.",
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
                "¡Hola! Soy GuIA. ¿Qué te gustaría organizar o conversar hoy?",
            )

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

    def _choose_pdf(self):
        rutas = filedialog.askopenfilenames(
            parent=self.root,
            title="Seleccionar documentos PDF",
            filetypes=(("Documentos PDF", "*.pdf"),),
        )
        if not rutas:
            return
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

    @staticmethod
    def _user_message_preview(text):
        prompt, documents = ChatSection._split_user_message(text)
        if prompt:
            return prompt
        return ", ".join(document["name"] for document in documents)

    @staticmethod
    def _split_user_message(text):
        parts = re.split(r"(?:\A|\n\n|\n)document: ([^\r\n]*)\r?\n", text)
        if len(parts) == 1:
            return text, []
        prompt = parts[0]
        documents = [
            {"name": parts[index], "text": parts[index + 1]}
            for index in range(1, len(parts), 2)
        ]
        return prompt, documents

    @staticmethod
    def _compose_user_message(
        prompt, document_name=None, document_text="", documents=None
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

    def _append_message(self, role, text):
        is_user = role == "user"
        attachments = []
        if is_user:
            text, attachments = self._split_user_message(text)
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
            text="Tú" if is_user else "GuIA",
            bg=bubble_color,
            fg="white" if is_user else COLORS["accent_light"],
            font=(FONT, 10, "bold"),
        ).pack(anchor="w", padx=18, pady=(14, 4))
        if text:
            body = self._create_formatted_message(
                bubble,
                text,
                background=bubble_color,
                foreground="white" if is_user else COLORS["text"],
                width=max(50, (self.root.winfo_width() - 560) // 9),
            )
            body.pack(
                anchor="w",
                padx=18,
                pady=(0, 8 if attachments else 15),
            )
        if attachments:
            attachment_frame = tk.Frame(bubble, bg=bubble_color)
            attachment_frame.pack(fill="x", padx=18, pady=(0, 12))
            attachment_frame.bind(
                "<Configure>",
                lambda event: self._layout_attachment_chips(event.widget),
                add="+",
            )
            for document in attachments:
                self._create_pdf_chip(
                    attachment_frame,
                    document["name"],
                )
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
        body.tag_configure("bold_italic", font=(FONT, 12, "bold", "italic"))
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
        body.tag_configure(
            "table_header",
            font=(FONT, 11, "bold"),
            foreground=COLORS["accent_light"],
        )
        body.tag_configure("table_primary", font=(FONT, 12, "bold"))
        body.tag_configure("strike", overstrike=True)
        self._emoji_images[body] = {}
        body.bind(
            "<Destroy>",
            lambda event, widget=body: (
                self._emoji_images.pop(widget, None)
                if event.widget is widget
                else None
            ),
            add="+",
        )
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
        lines = text.splitlines()
        line_index = 0
        while line_index < len(lines):
            line = lines[line_index]
            if line_index:
                widget.insert("end", "\n")
            headers = _markdown_table_cells(line)
            if (
                headers
                and line_index + 1 < len(lines)
                and _is_markdown_table_separator(lines[line_index + 1])
            ):
                separator = _markdown_table_cells(lines[line_index + 1])
                if len(headers) == len(separator):
                    rows = []
                    next_line = line_index + 2
                    while next_line < len(lines):
                        row = _markdown_table_cells(lines[next_line])
                        if not row or len(row) != len(headers):
                            break
                        rows.append(row)
                        next_line += 1
                    if rows:
                        self._insert_markdown_table(widget, headers, rows)
                        line_index = next_line
                        continue
            heading_match = re.match(r"^\s{0,3}(#{1,3})\s+(.*)$", line)
            if heading_match:
                widget.insert("end", f"{heading_match.group(2)}\n", "heading")
            else:
                quote_match = re.match(r"^\s*>\s?(.*)$", line)
                if quote_match:
                    self._insert_inline_formatted_text(
                        widget,
                        quote_match.group(1),
                        base_tag="quote",
                    )
                else:
                    list_match = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", line)
                    if list_match:
                        marker = (
                            "•"
                            if list_match.group(2) in {"-", "*", "+"}
                            else f"{list_match.group(2)}"
                        )
                        widget.insert("end", f"{list_match.group(1)}{marker}  ")
                        self._insert_inline_formatted_text(widget, list_match.group(3))
                    else:
                        self._insert_inline_formatted_text(widget, line)
            line_index += 1

        if text.endswith("\n"):
            widget.insert("end", "\n")

    def _insert_markdown_table(self, widget, headers, rows):
        for row_index, row in enumerate(rows):
            if row_index:
                widget.insert("end", "\n\n")
            for column_index, (header, value) in enumerate(zip(headers, row)):
                if column_index:
                    widget.insert("end", "\n")
                self._insert_inline_formatted_text(
                    widget,
                    f"{header}: ",
                    base_tag="table_header",
                )
                self._insert_inline_formatted_text(
                    widget,
                    value,
                    base_tag="table_primary" if column_index == 0 else None,
                )

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
            if (
                part.startswith(("***", "___"))
                and part.endswith(part[:3])
            ):
                value = part[3:-3]
                tag = "bold_italic"
            elif part.startswith(("**", "__")) and part.endswith(part[:2]):
                value = part[2:-2]
                tag = "bold"
            elif part.startswith("~~") and part.endswith("~~"):
                value = part[2:-2]
                tag = "strike"
            elif part.startswith("`") and part.endswith("`"):
                value = part[1:-1]
                tag = "code"
            elif part.startswith(("*", "_")) and part.endswith(part[0]):
                value = part[1:-1]
                tag = "italic"

            segments = EMOJI_CHAR.split(value)
            emojis = EMOJI_CHAR.findall(value)
            for index, segment in enumerate(segments):
                if segment:
                    tags = tuple(item for item in (base_tag, tag) if item)
                    widget.insert("end", segment, tags)
                if index < len(emojis):
                    self._insert_color_emoji(widget, emojis[index])

    def _insert_color_emoji(self, widget, emoji):
        images = self._emoji_images[widget]
        image = images.get(emoji)
        if image is None:
            if self._emoji_font is None:
                windows_directory = os.environ.get("WINDIR", r"C:\Windows")
                font_path = Path(windows_directory) / "Fonts" / "seguiemj.ttf"
                if not font_path.is_file():
                    widget.insert("end", emoji, "emoji")
                    return
                self._emoji_font = ImageFont.truetype(str(font_path), 18)
            bounds = self._emoji_font.getbbox(emoji)
            left, top, right, bottom = bounds
            emoji_image = Image.new(
                "RGBA",
                (max(1, right - left), max(1, bottom - top)),
                (0, 0, 0, 0),
            )
            ImageDraw.Draw(emoji_image).text(
                (-left, -top),
                emoji,
                font=self._emoji_font,
                embedded_color=True,
            )
            image = ImageTk.PhotoImage(emoji_image, master=widget)
            images[emoji] = image
        widget.image_create("end", image=image, align="baseline", padx=1)

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
        self.send_button.configure(state="disabled")
        self.status_label = self._label(
            self.content,
            "✦  GuIA está pensando",
            size=10,
            color=COLORS["accent_light"],
            bg=COLORS["background"],
        )
        self.status_label.pack(anchor="w", pady=(5, 0))
        self.status_base = "✦  GuIA está pensando"
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
                elif event == "services":
                    self._display_services(*value)
                elif event == "pdf_loaded":
                    self._handle_pdf_loaded(*value)
                elif event == "pdf_error":
                    self._handle_pdf_error(*value)
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
                text="GuIA",
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
