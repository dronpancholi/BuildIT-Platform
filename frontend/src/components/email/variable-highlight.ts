import { Mark } from "@tiptap/core";

export interface VariableHighlightOptions {
  pattern: RegExp;
  className: string;
}

declare module "@tiptap/core" {
  interface Commands<ReturnType> {
    variableHighlight: {
      insertVariable: (name: string) => ReturnType;
    };
  }
}

export const VariableHighlight = Mark.create<VariableHighlightOptions>({
  name: "variableHighlight",

  addOptions() {
    return {
      pattern: /\{\{(\w+)\}\}/g,
      className: "merge-variable",
    };
  },

  parseHTML() {
    return [
      {
        tag: "span[data-merge-variable]",
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      "span",
      {
        "data-merge-variable": HTMLAttributes.id || "",
        class: this.options.className,
      },
      0,
    ];
  },

  addAttributes() {
    return {
      id: {
        default: null,
        parseHTML: (el) => el.getAttribute("data-merge-variable"),
        renderHTML: (attrs) => {
          if (!attrs.id) return {};
          return { "data-merge-variable": attrs.id };
        },
      },
    };
  },

  addCommands() {
    return {
      insertVariable:
        (name: string) =>
        ({ chain }) => {
          return chain()
            .insertContent(`{{${name}}}`)
            .run();
        },
    };
  },
});
