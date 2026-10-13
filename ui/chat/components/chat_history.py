"""Renderizado del historial, formatos y scroll del chat."""

import math
import re
import tkinter as tk
from tkinter import ttk

from core.quizzes import (
    quiz_desde_mensaje,
    quiz_desde_resultado_herramienta,
)
from ...tema import COLORS, FONT
from ...utilidades import (
    EMOJI_CHAR,
    INLINE_MARKDOWN,
    _is_markdown_table_separator,
    _markdown_table_cells,
)


class ChatHistory:
    def _append_message(self, role, text):
        is_user = role == "user"
        quiz = None if is_user else quiz_desde_mensaje(text)
        attachments = []
        if is_user:
            text = re.sub(
                r"\AFecha: \d{2}/\d{2}/\d{4} Hora: \d{2}:\d{2}\n",
                "",
                text,
                count=1,
            )
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
        if text and quiz is None:
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
        if quiz is not None:
            self._render_chat_quiz(bubble, quiz)
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
        widget.insert("end", emoji, "emoji")

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

    def _attach_stream_quiz(self):
        if not hasattr(self, "stream_content"):
            return False
        quiz = quiz_desde_mensaje(self.stream_content)
        if quiz is None:
            return False
        self.stream_text.destroy()
        self._render_chat_quiz(self.stream_bubble, quiz)
        return True

    def _append_generated_quiz(self, quiz):
        outer = tk.Frame(self.message_list, bg=COLORS["background"])
        outer.pack(fill="x", padx=15, pady=8)
        bubble = self._card(
            outer,
            bg=COLORS["surface"],
            border=COLORS["border"],
            radius=24,
        )
        bubble.pack(side="left", padx=(0, 80))
        tk.Label(
            bubble,
            text="GuIA",
            bg=COLORS["surface"],
            fg=COLORS["accent_light"],
            font=(FONT, 10, "bold"),
        ).pack(anchor="w", padx=18, pady=(14, 4))
        self._render_chat_quiz(bubble, quiz)
        self._animate_card_in(outer)
        self.root.after_idle(lambda: self._animate_scroll_to_bottom(self.canvas))

    def _render_chat_history(self):
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

        assistant_quiz_ids = {
            quiz["quiz_id"]
            for message in self.chat.historial
            if message.get("role") == "assistant"
            and message.get("content")
            and (quiz := quiz_desde_mensaje(message["content"])) is not None
        }
        for message in self.chat.historial:
            if message.get("role") in {"assistant", "user"} and message.get("content"):
                self._append_message(message["role"], message["content"])
            elif (
                message.get("role") == "tool"
                and message.get("name") == "crear_quiz"
            ):
                quiz = quiz_desde_resultado_herramienta(message.get("content", ""))
                if quiz is not None and quiz["quiz_id"] not in assistant_quiz_ids:
                    self._append_generated_quiz(quiz)
        if not self.message_list.winfo_children():
            self._append_message(
                "assistant",
                "¡Hola! Soy GuIA. ¿Qué te gustaría organizar o conversar hoy?",
            )
