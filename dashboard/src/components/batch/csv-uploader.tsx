"use client";

import { useCallback, useRef } from "react";
import Image from "next/image";
import Papa from "papaparse";
import { Card, CardContent } from "@/components/ui/card";
import { Upload } from "lucide-react";

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
    <Card
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        e.currentTarget.classList.add("border-kiln-teal");
      }}
      onDragLeave={(e) => {
        e.currentTarget.classList.remove("border-kiln-teal");
      }}
      onDrop={(e) => {
        e.preventDefault();
        e.currentTarget.classList.remove("border-kiln-teal");
        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
      }}
      className="cursor-pointer border-2 border-dashed border-clay-700 bg-clay-900/50 hover:border-kiln-teal/50 transition-all duration-200"
    >
      <CardContent className="flex flex-col items-center justify-center py-14 text-center">
        <Image
          src="/brand-assets/v2-batch.png"
          alt=""
          width={80}
          height={80}
          className="mb-4 animate-float opacity-70 rounded-lg"
        />
        <Upload className="h-8 w-8 text-clay-600 mb-3" />
        <p className="text-clay-300 text-sm font-[family-name:var(--font-sans)]">
          Drop a CSV here or{" "}
          <span className="text-kiln-teal font-medium">click to upload</span>
        </p>
        <p className="text-xs text-clay-600 mt-1">
          Supports .csv files with headers
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
      </CardContent>
    </Card>
  );
}
