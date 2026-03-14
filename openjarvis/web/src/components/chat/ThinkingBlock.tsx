import { useState } from "react";
import { ChevronDown, ChevronRight, Brain } from "lucide-react";

interface ThinkingBlockProps {
  content: string;
}

export function ThinkingBlock({ content }: ThinkingBlockProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="my-2 rounded-md border border-violet-200/60 bg-violet-50/40 dark:border-violet-800/40 dark:bg-violet-950/20 text-xs">
      <button
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-violet-700 dark:text-violet-400 hover:text-violet-900 dark:hover:text-violet-200"
        onClick={() => setOpen((v) => !v)}
      >
        <Brain className="h-3 w-3 shrink-0" />
        <span className="font-medium">Thinking</span>
        {open ? (
          <ChevronDown className="ml-auto h-3 w-3" />
        ) : (
          <ChevronRight className="ml-auto h-3 w-3" />
        )}
      </button>
      {open && (
        <div className="border-t border-violet-200/60 dark:border-violet-800/40 px-3 py-2">
          <pre className="whitespace-pre-wrap break-all font-mono text-xs text-violet-800 dark:text-violet-300">
            {content}
          </pre>
        </div>
      )}
    </div>
  );
}
