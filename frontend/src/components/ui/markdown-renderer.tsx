"use client";

import { useMemo } from "react";
import { cn } from "@/lib/utils";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

/**
 * Simple markdown renderer for common markdown syntax
 * Handles: headings, bold, italic, code, links, lists, and line breaks
 */
export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  const rendered = useMemo(() => {
    if (!content) return null;

    // Split by double newlines for paragraphs, single newlines for lines
    const blocks = content.split(/\n\n+/);

    return blocks.map((block, blockIdx) => {
      const trimmedBlock = block.trim();
      if (!trimmedBlock) return null;

      // Check for headers
      if (trimmedBlock.startsWith("### ")) {
        return (
          <h3 key={blockIdx} className="text-lg font-semibold mt-4 mb-2">
            {parseInline(trimmedBlock.slice(4))}
          </h3>
        );
      }
      if (trimmedBlock.startsWith("## ")) {
        return (
          <h2 key={blockIdx} className="text-xl font-bold mt-5 mb-3">
            {parseInline(trimmedBlock.slice(3))}
          </h2>
        );
      }
      if (trimmedBlock.startsWith("# ")) {
        return (
          <h1 key={blockIdx} className="text-2xl font-bold mt-6 mb-4">
            {parseInline(trimmedBlock.slice(2))}
          </h1>
        );
      }

      // Check for unordered list
      const lines = trimmedBlock.split("\n");
      const isUnorderedList = lines.every(
        (line) => line.trim().startsWith("- ") || line.trim().startsWith("* ") || line.trim() === ""
      );
      if (isUnorderedList && lines.some((line) => line.trim().startsWith("-") || line.trim().startsWith("*"))) {
        return (
          <ul key={blockIdx} className="list-disc pl-6 space-y-1 my-2">
            {lines
              .filter((line) => line.trim().startsWith("-") || line.trim().startsWith("*"))
              .map((line, lineIdx) => (
                <li key={lineIdx} className="text-sm">
                  {parseInline(line.replace(/^[\s]*[-*]\s*/, ""))}
                </li>
              ))}
          </ul>
        );
      }

      // Check for ordered list
      const isOrderedList = lines.every(
        (line) => /^\d+\.\s/.test(line.trim()) || line.trim() === ""
      );
      if (isOrderedList && lines.some((line) => /^\d+\.\s/.test(line.trim()))) {
        return (
          <ol key={blockIdx} className="list-decimal pl-6 space-y-1 my-2">
            {lines
              .filter((line) => /^\d+\.\s/.test(line.trim()))
              .map((line, lineIdx) => (
                <li key={lineIdx} className="text-sm">
                  {parseInline(line.replace(/^\d+\.\s*/, ""))}
                </li>
              ))}
          </ol>
        );
      }

      // Check for code block
      if (trimmedBlock.startsWith("```") && trimmedBlock.endsWith("```")) {
        const codeContent = trimmedBlock.slice(3, -3).replace(/^[a-z]*\n/, "");
        return (
          <pre
            key={blockIdx}
            className="bg-muted p-4 rounded-lg overflow-x-auto my-3 text-sm font-mono"
          >
            <code>{codeContent}</code>
          </pre>
        );
      }

      // Regular paragraph - handle line breaks within
      return (
        <p key={blockIdx} className="text-sm my-2 leading-relaxed">
          {lines.map((line, lineIdx) => (
            <span key={lineIdx}>
              {parseInline(line)}
              {lineIdx < lines.length - 1 && <br />}
            </span>
          ))}
        </p>
      );
    });
  }, [content]);

  return (
    <div className={cn("prose prose-sm max-w-none dark:prose-invert", className)}>
      {rendered}
    </div>
  );
}

/**
 * Parse inline markdown: bold, italic, code, links
 */
function parseInline(text: string): React.ReactNode {
  if (!text) return null;

  const elements: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    // Bold: **text** or __text__
    const boldMatch = remaining.match(/^([\s\S]*?)(\*\*|__)(.+?)\2([\s\S]*)$/);
    if (boldMatch) {
      if (boldMatch[1]) elements.push(<span key={key++}>{boldMatch[1]}</span>);
      elements.push(<strong key={key++} className="font-semibold">{boldMatch[3]}</strong>);
      remaining = boldMatch[4];
      continue;
    }

    // Italic: *text* or _text_ (but not inside words for underscores)
    const italicMatch = remaining.match(/^([\s\S]*?)(\*|_)(.+?)\2([\s\S]*)$/);
    if (italicMatch && italicMatch[2] === "*") {
      if (italicMatch[1]) elements.push(<span key={key++}>{italicMatch[1]}</span>);
      elements.push(<em key={key++} className="italic">{italicMatch[3]}</em>);
      remaining = italicMatch[4];
      continue;
    }

    // Inline code: `code`
    const codeMatch = remaining.match(/^([\s\S]*?)`([^`]+)`([\s\S]*)$/);
    if (codeMatch) {
      if (codeMatch[1]) elements.push(<span key={key++}>{codeMatch[1]}</span>);
      elements.push(
        <code key={key++} className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono">
          {codeMatch[2]}
        </code>
      );
      remaining = codeMatch[3];
      continue;
    }

    // Links: [text](url)
    const linkMatch = remaining.match(/^([\s\S]*?)\[([^\]]+)\]\(([^)]+)\)([\s\S]*)$/);
    if (linkMatch) {
      if (linkMatch[1]) elements.push(<span key={key++}>{linkMatch[1]}</span>);
      elements.push(
        <a
          key={key++}
          href={linkMatch[3]}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary underline hover:no-underline"
        >
          {linkMatch[2]}
        </a>
      );
      remaining = linkMatch[4];
      continue;
    }

    // No more patterns found, add remaining text
    elements.push(<span key={key++}>{remaining}</span>);
    break;
  }

  return elements.length === 1 ? elements[0] : <>{elements}</>;
}

export default MarkdownRenderer;
