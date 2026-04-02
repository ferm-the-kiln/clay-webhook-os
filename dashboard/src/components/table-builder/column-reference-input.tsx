"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import type { TableColumn } from "@/lib/types";

interface ColumnReferenceInputProps {
  value: string;
  onChange: (value: string) => void;
  availableColumns: TableColumn[];
  placeholder?: string;
  multiline?: boolean;
}

const TYPE_COLORS: Record<string, string> = {
  input: "bg-zinc-700 text-zinc-200",
  enrichment: "bg-blue-500/20 text-blue-300",
  ai: "bg-purple-500/20 text-purple-300",
  formula: "bg-teal-500/20 text-teal-300",
  gate: "bg-amber-500/20 text-amber-300",
  static: "bg-zinc-700 text-zinc-300",
};

/**
 * Smart input that shows a dropdown when "/" is typed.
 * Selected columns render as visual pills in the display,
 * but the underlying value uses {{column_id}} for backend compatibility.
 */
export function ColumnReferenceInput({
  value,
  onChange,
  availableColumns,
  placeholder,
  multiline,
}: ColumnReferenceInputProps) {
  const [showDropdown, setShowDropdown] = useState(false);
  const [search, setSearch] = useState("");
  const [cursorPos, setCursorPos] = useState(0);
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Filter columns by search term
  const filtered = availableColumns.filter(
    (c) =>
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.id.toLowerCase().includes(search.toLowerCase()),
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "/" && !showDropdown) {
      e.preventDefault();
      setShowDropdown(true);
      setSearch("");
      return;
    }
    if (showDropdown) {
      if (e.key === "Escape") {
        setShowDropdown(false);
        return;
      }
      if (e.key === "Enter" && filtered.length > 0) {
        e.preventDefault();
        selectColumn(filtered[0]);
        return;
      }
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const newVal = e.target.value;
    onChange(newVal);

    // Check if user just typed "/"
    const pos = e.target.selectionStart || 0;
    setCursorPos(pos);
    if (newVal[pos - 1] === "/") {
      setShowDropdown(true);
      setSearch("");
    } else if (showDropdown) {
      // Extract search text after the last "/"
      const lastSlash = newVal.lastIndexOf("/", pos - 1);
      if (lastSlash >= 0) {
        setSearch(newVal.slice(lastSlash + 1, pos));
      } else {
        setShowDropdown(false);
      }
    }
  };

  const selectColumn = (col: TableColumn) => {
    // Replace the "/" and any search text with {{column_id}}
    const input = inputRef.current;
    if (!input) return;

    const pos = cursorPos;
    const text = value;
    const lastSlash = text.lastIndexOf("/", pos - 1);
    const before = text.slice(0, lastSlash >= 0 ? lastSlash : pos);
    const after = text.slice(pos);
    const newValue = `${before}{{${col.id}}}${after}`;
    onChange(newValue);
    setShowDropdown(false);

    // Restore focus
    setTimeout(() => {
      input.focus();
      const newPos = before.length + col.id.length + 4;
      input.setSelectionRange(newPos, newPos);
    }, 0);
  };

  // Close dropdown on outside click
  useEffect(() => {
    const handle = (e: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(e.target as Node)
      ) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, []);

  // Render the display with pills for {{column_id}} references
  const renderDisplay = () => {
    const colMap = new Map(availableColumns.map((c) => [c.id, c]));
    const parts = value.split(/(\{\{[^}]+\}\})/);
    return parts.map((part, i) => {
      const match = part.match(/^\{\{(.+)\}\}$/);
      if (match) {
        const col = colMap.get(match[1]);
        if (col) {
          const colorClass = TYPE_COLORS[col.column_type] || TYPE_COLORS.input;
          return (
            <span
              key={i}
              className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${colorClass} mx-0.5`}
            >
              {col.name}
            </span>
          );
        }
      }
      return part ? <span key={i}>{part}</span> : null;
    });
  };

  const InputComponent = multiline ? "textarea" : "input";

  return (
    <div className="relative">
      {/* Pill display overlay (shown above the actual input) */}
      {value && value.includes("{{") && (
        <div className="pointer-events-none absolute inset-0 flex items-center px-3 text-sm text-zinc-300 overflow-hidden">
          {renderDisplay()}
        </div>
      )}

      {/* Actual input */}
      <InputComponent
        ref={inputRef as never}
        value={value}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className={`w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-md text-sm text-white outline-none focus:border-kiln-teal transition-colors ${
          value.includes("{{") ? "text-transparent caret-white" : ""
        } ${multiline ? "min-h-[80px] resize-y" : ""}`}
      />

      {/* "/" Autocomplete dropdown */}
      {showDropdown && (
        <div
          ref={dropdownRef}
          className="absolute top-full left-0 mt-1 w-full bg-zinc-900 border border-zinc-700 rounded-md shadow-xl z-50 max-h-48 overflow-y-auto"
        >
          {filtered.length === 0 ? (
            <div className="px-3 py-2 text-xs text-zinc-500">No matching columns</div>
          ) : (
            filtered.map((col) => {
              const colorClass = TYPE_COLORS[col.column_type] || TYPE_COLORS.input;
              return (
                <button
                  key={col.id}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-zinc-300 hover:bg-zinc-800 text-left"
                  onClick={() => selectColumn(col)}
                >
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${colorClass}`}
                  >
                    {col.column_type}
                  </span>
                  <span className="truncate">{col.name}</span>
                </button>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
