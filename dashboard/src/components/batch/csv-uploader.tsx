"use client";

import { useCallback, useRef } from "react";
import Papa from "papaparse";

export function CsvUploader({
  onParsed,
}: {
  onParsed: (headers: string[], rows: Record<string, string>[]) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    (file: File) => {
      Papa.parse<Record<string, string>>(file, {
        header: true,
        skipEmptyLines: true,
        complete: (result) => {
          if (result.data.length > 0) {
            onParsed(result.meta.fields || [], result.data);
          }
        },
      });
    },
    [onParsed]
  );

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        e.currentTarget.classList.add("border-teal-500");
      }}
      onDragLeave={(e) => {
        e.currentTarget.classList.remove("border-teal-500");
      }}
      onDrop={(e) => {
        e.preventDefault();
        e.currentTarget.classList.remove("border-teal-500");
        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
      }}
      className="cursor-pointer rounded-xl border-2 border-dashed border-zinc-700 bg-zinc-900 p-12 text-center transition-colors hover:border-zinc-600"
    >
      <svg className="mx-auto h-10 w-10 text-zinc-600 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
      </svg>
      <p className="text-zinc-400 text-sm">
        Drop a CSV here or <span className="text-teal-400">click to upload</span>
      </p>
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
        }}
      />
    </div>
  );
}
