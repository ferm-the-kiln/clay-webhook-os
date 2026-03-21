"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownContentProps {
  content: string;
  className?: string;
}

export function MarkdownContent({ content, className }: MarkdownContentProps) {
  if (!content) return null;

  return (
    <div
      className={`prose prose-invert prose-sm max-w-none
        prose-headings:text-clay-100 prose-headings:font-semibold prose-headings:mt-4 prose-headings:mb-2
        prose-p:text-clay-300 prose-p:leading-relaxed prose-p:my-1.5
        prose-a:text-kiln-teal prose-a:no-underline hover:prose-a:underline
        prose-strong:text-clay-100 prose-em:text-clay-300
        prose-ul:text-clay-300 prose-ol:text-clay-300 prose-li:my-0.5
        prose-code:text-kiln-teal prose-code:bg-clay-700 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs
        prose-pre:bg-clay-900 prose-pre:border prose-pre:border-clay-700 prose-pre:rounded-lg
        prose-blockquote:border-clay-600 prose-blockquote:text-clay-400
        prose-table:text-clay-300 prose-th:text-clay-200 prose-th:border-clay-600 prose-td:border-clay-700
        prose-hr:border-clay-700
        ${className ?? ""}`}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
