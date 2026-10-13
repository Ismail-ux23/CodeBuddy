"use client";
import { useEffect, useRef } from "react";
import { EditorState } from "@codemirror/state";
import {
  EditorView,
  lineNumbers,
  highlightActiveLine,
  Decoration,
} from "@codemirror/view";
import { python } from "@codemirror/lang-python";
import { javascript } from "@codemirror/lang-javascript";
import { oneDark } from "@codemirror/theme-one-dark";
import { searchKeymap, highlightSelectionMatches } from "@codemirror/search";
import { keymap } from "@codemirror/view";
export default function CodeViewer({
  text,
  language,
  start,
  end,
  onSelection,
}: {
  text: string;
  language: string;
  start?: number;
  end?: number;
  onSelection?: (a: number, b: number) => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!host.current) return;
    const lang =
      language === "py"
        ? python()
        : ["js", "jsx", "ts", "tsx"].includes(language)
          ? javascript({
              typescript: language.startsWith("ts"),
              jsx: language.endsWith("x"),
            })
          : [];
    const initial = EditorState.create({ doc: text });
    const marks = [];
    if (start && end)
      for (let line = start; line <= Math.min(end, initial.doc.lines); line++)
        marks.push(
          Decoration.line({ class: "citation-highlight" }).range(
            initial.doc.line(line).from,
          ),
        );
    const editor = new EditorView({
      parent: host.current,
      state: EditorState.create({
        doc: text,
        extensions: [
          lineNumbers(),
          highlightActiveLine(),
          highlightSelectionMatches(),
          keymap.of(searchKeymap),
          lang,
          oneDark,
          EditorState.readOnly.of(true),
          EditorView.editable.of(false),
          EditorView.contentAttributes.of({
            "aria-label": "Read-only source code",
            tabindex: "0",
          }),
          EditorView.decorations.of(Decoration.set(marks)),
          EditorView.updateListener.of((v) => {
            if (v.selectionSet) {
              const selection = v.state.selection.main;
              onSelection?.(
                v.state.doc.lineAt(selection.from).number,
                v.state.doc.lineAt(selection.to).number,
              );
            }
          }),
          EditorView.theme({
            "&": {
              height: "100%",
              backgroundColor: "#080808",
              fontSize: "13px",
            },
            ".cm-scroller": {
              overflow: "auto",
              fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
            },
            ".cm-gutters": {
              backgroundColor: "#080808",
              color: "#737373",
              borderRight: "1px solid #1f1f1f",
            },
          }),
        ],
      }),
    });
    if (start && start <= editor.state.doc.lines)
      editor.dispatch({
        effects: EditorView.scrollIntoView(editor.state.doc.line(start).from, {
          y: "center",
        }),
      });
    return () => editor.destroy();
  }, [text, language, start, end, onSelection]);
  return <div ref={host} className="code-editor" />;
}
