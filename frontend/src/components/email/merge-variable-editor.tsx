"use client";

import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Image from "@tiptap/extension-image";
import Link from "@tiptap/extension-link";
import { useEffect, forwardRef, useImperativeHandle } from "react";
import { cn } from "@/lib/utils";
import {
  Bold,
  Italic,
  List,
  ListOrdered,
  Quote,
  Code,
  Link as LinkIcon,
  Image as ImageIcon,
  Undo,
  Redo,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { VariableInsertMenu } from "./variable-insert-menu";

interface MergeVariableEditorProps {
  content: string;
  onChange: (html: string) => void;
  placeholder?: string;
  editable?: boolean;
  className?: string;
  onVariableInsert?: (name: string) => void;
}

export const MergeVariableEditor = forwardRef<any, MergeVariableEditorProps>(
  (
    {
      content,
      onChange,
      placeholder = "Write something...",
      editable = true,
      className,
      onVariableInsert,
    },
    ref
  ) => {
    const editor = useEditor({
      extensions: [
        StarterKit.configure({
          heading: {
            levels: [1, 2, 3],
          },
        }),
        Image.configure({
          inline: true,
          allowBase64: true,
        }),
        Link.configure({
          openOnClick: false,
        }),
      ],
      content,
      editable,
      onUpdate: ({ editor }) => {
        onChange(editor.getHTML());
      },
      editorProps: {
        attributes: {
          class: cn(
            "prose prose-sm max-w-none focus:outline-none min-h-[250px] p-4",
            "prose-headings:text-slate-100",
            "prose-p:text-slate-300",
            "prose-a:text-platform-400",
            "prose-strong:text-slate-100",
            "prose-code:text-slate-300",
            "prose-pre:bg-surface-darker",
            "prose-img:rounded-md",
            className
          ),
        },
      },
    });

    useImperativeHandle(ref, () => ({
      setContent: (newContent: string) => {
        editor?.commands.setContent(newContent);
      },
      getContent: () => editor?.getHTML() || "",
      editor,
    }));

    useEffect(() => {
      if (editor && content !== editor.getHTML()) {
        editor.commands.setContent(content);
      }
    }, [content, editor]);

    const handleInsertVariable = (name: string) => {
      if (!editor) return;
      editor.commands.insertContent(`{{${name}}}`);
      if (onVariableInsert) onVariableInsert(name);
    };

    if (!editor) {
      return null;
    }

    return (
      <div className="border border-slate-600 rounded-md bg-surface-darker">
        {editable && (
          <div className="flex items-center gap-1 p-2 border-b border-slate-600 flex-wrap">
            <Button
              size="sm"
              variant={editor.isActive("bold") ? "default" : "ghost"}
              onClick={() => editor.chain().focus().toggleBold().run()}
              className="h-8 w-8 p-0"
            >
              <Bold className="w-4 h-4" />
            </Button>
            <Button
              size="sm"
              variant={editor.isActive("italic") ? "default" : "ghost"}
              onClick={() => editor.chain().focus().toggleItalic().run()}
              className="h-8 w-8 p-0"
            >
              <Italic className="w-4 h-4" />
            </Button>
            <div className="w-px h-6 bg-slate-600 mx-1" />
            <Button
              size="sm"
              variant={editor.isActive("bulletList") ? "default" : "ghost"}
              onClick={() => editor.chain().focus().toggleBulletList().run()}
              className="h-8 w-8 p-0"
            >
              <List className="w-4 h-4" />
            </Button>
            <Button
              size="sm"
              variant={editor.isActive("orderedList") ? "default" : "ghost"}
              onClick={() => editor.chain().focus().toggleOrderedList().run()}
              className="h-8 w-8 p-0"
            >
              <ListOrdered className="w-4 h-4" />
            </Button>
            <div className="w-px h-6 bg-slate-600 mx-1" />
            <Button
              size="sm"
              variant={editor.isActive("blockquote") ? "default" : "ghost"}
              onClick={() => editor.chain().focus().toggleBlockquote().run()}
              className="h-8 w-8 p-0"
            >
              <Quote className="w-4 h-4" />
            </Button>
            <Button
              size="sm"
              variant={editor.isActive("codeBlock") ? "default" : "ghost"}
              onClick={() => editor.chain().focus().toggleCodeBlock().run()}
              className="h-8 w-8 p-0"
            >
              <Code className="w-4 h-4" />
            </Button>
            <div className="w-px h-6 bg-slate-600 mx-1" />
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                const url = prompt("Enter URL:");
                if (url) editor.chain().focus().setLink({ href: url }).run();
              }}
              className="h-8 w-8 p-0"
            >
              <LinkIcon className="w-4 h-4" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                const url = prompt("Enter image URL:");
                if (url) editor.chain().focus().setImage({ src: url }).run();
              }}
              className="h-8 w-8 p-0"
            >
              <ImageIcon className="w-4 h-4" />
            </Button>
            <div className="w-px h-6 bg-slate-600 mx-1" />
            <Button
              size="sm"
              variant="ghost"
              onClick={() => editor.chain().focus().undo().run()}
              className="h-8 w-8 p-0"
              disabled={!editor.can().undo()}
            >
              <Undo className="w-4 h-4" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => editor.chain().focus().redo().run()}
              className="h-8 w-8 p-0"
              disabled={!editor.can().redo()}
            >
              <Redo className="w-4 h-4" />
            </Button>
            <div className="ml-auto">
              <VariableInsertMenu onInsert={handleInsertVariable} />
            </div>
          </div>
        )}

        <EditorContent editor={editor} className="prose prose-invert max-w-none" />
      </div>
    );
  }
);

MergeVariableEditor.displayName = "MergeVariableEditor";
