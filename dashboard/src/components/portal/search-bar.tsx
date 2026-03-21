"use client";

import { useRef, useEffect, useState } from "react";
import { Search, X } from "lucide-react";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  resultCount: number;
  totalCount: number;
}

export function SearchBar({ value, onChange, resultCount, totalCount }: SearchBarProps) {
  const [local, setLocal] = useState(value);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setLocal(value);
  }, [value]);

  function handleChange(v: string) {
    setLocal(v);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => onChange(v), 300);
  }

  function handleClear() {
    setLocal("");
    onChange("");
  }

  return (
    <div className="relative">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-clay-500" />
      <input
        type="text"
        value={local}
        onChange={(e) => handleChange(e.target.value)}
        placeholder="Search posts..."
        className="w-full rounded-lg border border-clay-700 bg-clay-900 pl-9 pr-20 py-2 text-sm text-clay-100 placeholder:text-clay-500 focus:border-clay-500 focus:outline-none"
      />
      <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
        {value && (
          <>
            <span className="text-[10px] text-clay-500">
              {resultCount} of {totalCount}
            </span>
            <button onClick={handleClear} className="text-clay-500 hover:text-clay-300">
              <X className="h-3.5 w-3.5" />
            </button>
          </>
        )}
      </div>
    </div>
  );
}
