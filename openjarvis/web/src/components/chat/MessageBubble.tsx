import { useState } from "react";
import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";
import { cn } from "../../lib/utils";
import type { ChatMessage } from "../../stores/chatStore";
import { ToolCallCard } from "./ToolCallCard";
import { ThinkingBlock } from "./ThinkingBlock";
import { useAuthStore } from "../../stores/authStore";
import { 
  Info, ChevronDown, ChevronRight, CheckCircle2, XCircle, 
  FileText, FileCode, FileImage, File, Download 
} from "lucide-react";

interface MessageBubbleProps {
  message: ChatMessage;
}

function getFileIcon(filename: string) {
  const ext = filename.split(".").pop()?.toLowerCase() || "";
  if (["png", "jpg", "jpeg", "gif", "webp", "bmp"].includes(ext)) return <FileImage className="h-4 w-4" />;
  if (["py", "js", "ts", "tsx", "html", "css", "json", "sh"].includes(ext)) return <FileCode className="h-4 w-4" />;
  if (["md", "txt", "pdf", "docx", "csv"].includes(ext)) return <FileText className="h-4 w-4" />;
  return <File className="h-4 w-4" />;
}

function FileCard({ href, name }: { href: string; name: string }) {
  const filename = name || href.split("/").pop() || "file";
  
  return (
    <div className="my-2 flex max-w-sm items-center gap-3 rounded-xl border border-border/50 bg-muted/30 p-3 shadow-sm transition-all hover:bg-muted/50 dark:bg-muted/10">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-background shadow-inner">
        {getFileIcon(filename)}
      </div>
      <div className="flex min-w-0 flex-col gap-0.5">
        <span className="truncate text-sm font-medium text-foreground/90">{filename}</span>
        <div className="flex items-center gap-3">
          <a 
            href={`${href}?download=1`} 
            download={filename}
            className="flex items-center gap-1 text-[11px] text-muted-foreground transition-colors hover:text-primary"
          >
            <Download className="h-3 w-3" />
            <span>Download</span>
          </a>
        </div>
      </div>
    </div>
  );
}

function splitThinking(content: string): { type: "text" | "thinking"; content: string }[] {
  const parts: { type: "text" | "thinking"; content: string }[] = [];
  const regex = /<think>([\s\S]*?)<\/think>/g;
  let lastIndex = 0;
  let match;
  while ((match = regex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: "text", content: content.slice(lastIndex, match.index) });
    }
    parts.push({ type: "thinking", content: match[1] });
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < content.length) {
    parts.push({ type: "text", content: content.slice(lastIndex) });
  }
  return parts;
}

/** Tool execution result block — clean slate style, collapsible */
function ToolResultBlock({ message }: { message: ChatMessage }) {
  const isError = message.content.startsWith("Error:");
  const isLong = message.content.length > 300;
  const [open, setOpen] = useState(false);

  return (
    <div className={cn(
      "rounded-lg border text-xs overflow-hidden",
      isError
        ? "border-red-200/70 bg-red-50/40 dark:border-red-800/40 dark:bg-red-950/15"
        : "border-border/60 bg-muted/30 dark:bg-muted/20"
    )}>
      <button
        onClick={() => isLong && setOpen((v) => !v)}
        className={cn(
          "flex w-full items-center gap-2 px-3 py-1.5 text-left rounded-lg transition-colors",
          isLong && "hover:bg-muted/50 cursor-pointer",
          !isLong && "cursor-default"
        )}
      >
        {isError
          ? <XCircle className="h-3 w-3 shrink-0 text-red-500" />
          : <CheckCircle2 className="h-3 w-3 shrink-0 text-violet-500" />}
        <span className="font-mono font-medium text-foreground/70 truncate">
          {message.name || "tool"}
        </span>
        <span className="ml-auto mr-1 shrink-0 text-[10px] text-muted-foreground/40">
          {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </span>
        {isLong && (
          open
            ? <ChevronDown className="h-3 w-3 shrink-0 text-muted-foreground/50" />
            : <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground/50" />
        )}
      </button>
      {(open || !isLong) && (
        <div className="border-t border-border/40 px-3 py-2">
          <pre className={cn(
            "max-h-48 overflow-y-auto whitespace-pre-wrap break-all font-mono text-[11px] leading-relaxed",
            isError ? "text-red-700/80 dark:text-red-300/70" : "text-muted-foreground/80"
          )}>
            {message.content}
          </pre>
        </div>
      )}
    </div>
  );
}

/** System message block — gray, collapsed by default (usually the system prompt) */
function SystemMessageBlock({ message }: { message: ChatMessage }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded border border-dashed border-muted-foreground/20 bg-muted/20 text-xs">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-1.5 text-left hover:bg-muted/40 rounded transition-colors"
      >
        <Info className="h-3 w-3 shrink-0 text-muted-foreground/60" />
        <span className="font-medium text-muted-foreground/70">System</span>
        <span className="ml-auto mr-1 shrink-0 text-[10px] text-muted-foreground/40">
          {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </span>
        {open
          ? <ChevronDown className="h-3 w-3 shrink-0 text-muted-foreground/50" />
          : <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground/50" />}
      </button>
      {open && (
        <div className="border-t border-muted-foreground/10 px-3 py-2">
          <pre className="max-h-56 overflow-y-auto whitespace-pre-wrap break-all font-mono text-[11px] leading-relaxed text-muted-foreground/60">
            {message.content}
          </pre>
        </div>
      )}
    </div>
  );
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const user = useAuthStore((s: any) => s.user);

  // Don't render anything for empty/whitespace messages
  if (!message.content?.trim() && !message.toolCalls?.length && !message.isStreaming) {
    return null;
  }

  // Hide redundant message() tool result — the reply is already shown as an assistant bubble
  if (message.role === "tool" && message.name === "message") {
    return null;
  }

  // Tool result — compact collapsible block (no avatar)
  if (message.role === "tool") {
    return <ToolResultBlock message={message} />;
  }

  // System message — compact info strip, collapsed by default (no avatar)
  if (message.role === "system") {
    return <SystemMessageBlock message={message} />;
  }

  const isUser = message.role === "user";
  const parts = splitThinking(message.content ?? "");

  const MarkdownComponents: Components = {
    a: ({ href, children }: { href?: string; children?: any }) => {
      if (href?.startsWith("/api/files/")) {
        // Only turn into a card if it's NOT an image (images are handled by 'img' tag or explicit logic)
        const isImage = /\.(png|jpe?g|gif|webp|bmp)$/i.test(href);
        if (!isImage) {
          return <FileCard href={href} name={String(children)} />;
        }
      }
      return (
        <a href={href} target="_blank" rel="noopener noreferrer">
          {children}
        </a>
      );
    },
    img: ({ src, alt }: { src?: string; alt?: string }) => {
      if (!src) return null;
      return (
        <a href={src} target="_blank" rel="noopener noreferrer" className="block my-2">
          <img
            src={src}
            alt={alt || "image"}
            className="max-h-96 max-w-full rounded-xl border border-primary-foreground/10 object-contain shadow-md"
          />
        </a>
      );
    }
  };

  return (
    <div className={cn("group flex gap-3 px-4", isUser ? "flex-row-reverse" : "flex-row")}>
      {/* Avatar */}
      <div className={cn(
        "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold select-none",
        isUser
          ? "bg-primary text-primary-foreground shadow-sm"
          : "overflow-hidden p-0 shadow-sm"
      )}>
        {isUser
          ? (user?.username?.[0]?.toUpperCase() ?? "U")
          : <img src="/icon.svg" alt="InterClaw" className="h-8 w-8 object-cover mix-blend-multiply dark:mix-blend-screen dark:brightness-150" />}
      </div>

      {/* Content */}
      <div className={cn(
        "flex max-w-[78%] flex-col gap-1",
        isUser ? "items-end" : "items-start"
      )}>
        <div className={cn(
          "w-full rounded-2xl p-0.5 shadow-sm",
          isUser ? "rounded-tr-sm bg-primary" : "bg-transparent"
        )}>
          {isUser ? (
            <div className="px-4 py-2.5 text-sm leading-relaxed text-primary-foreground prose prose-invert prose-sm max-w-none [&_a]:text-inherit [&_a]:underline hover:[&_a]:text-inherit/80">
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]} 
                rehypePlugins={[rehypeHighlight]}
                components={MarkdownComponents}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          ) : (
            <div className="w-full space-y-2">
              {parts.map((part, i) =>
                part.type === "thinking" ? (
                  <ThinkingBlock key={i} content={part.content} />
                ) : part.content.trim() ? (
                  <div key={i} className={cn(
                    "prose prose-sm max-w-none dark:prose-invert",
                    "[&_p]:leading-relaxed [&_p]:my-1",
                    "[&_pre]:rounded-xl [&_pre]:bg-zinc-100 dark:[&_pre]:bg-zinc-900 [&_pre]:text-zinc-900 dark:[&_pre]:text-zinc-100 [&_pre]:p-4 [&_pre]:text-xs [&_pre]:shadow-lg",
                    "[&_code:not(pre_code)]:rounded [&_code:not(pre_code)]:bg-muted [&_code:not(pre_code)]:px-1.5 [&_code:not(pre_code)]:py-0.5 [&_code:not(pre_code)]:text-xs [&_code:not(pre_code)]:font-mono",
                    "[&_blockquote]:border-l-primary [&_blockquote]:text-muted-foreground",
                    "[&_table]:text-xs [&_th]:bg-muted",
                    "[&_a]:text-primary [&_a]:no-underline hover:[&_a]:underline",
                  )}>
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]} 
                      rehypePlugins={[rehypeHighlight]}
                      components={MarkdownComponents}
                    >
                      {part.content}
                    </ReactMarkdown>
                  </div>
                ) : null
              )}
              {message.toolCalls?.map((tool) => (
                <ToolCallCard key={tool.id} tool={tool} />
              ))}
              {message.isStreaming && (
                <span className="inline-block h-4 w-0.5 animate-pulse rounded-full bg-foreground/60 align-middle ml-0.5" />
              )}
            </div>
          )}
        </div>
        <span className="text-[11px] text-muted-foreground/60 px-1">
          {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </span>
      </div>
    </div>
  );
}
