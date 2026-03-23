"use client";

import { useRef, useState, useCallback, useEffect } from "react";
import type { FunctionDefinition } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Blocks, Send, Paperclip, Mic, MicOff, X } from "lucide-react";
import Papa from "papaparse";

interface ChatInputProps {
  value: string;
  onChange: (v: string) => void;
  onSend: (csvData?: Record<string, unknown>[]) => void;
  disabled: boolean;
  selectedFunction: FunctionDefinition | null;
}

// Web Speech API types (not all browsers ship these)
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

type SpeechRecognitionCtor = new () => SpeechRecognition;
interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((e: SpeechRecognitionEvent) => void) | null;
  onerror: ((e: Event) => void) | null;
  onend: (() => void) | null;
}

function getSpeechRecognition(): SpeechRecognitionCtor | null {
  if (typeof window === "undefined") return null;
  return (
    (window as unknown as Record<string, SpeechRecognitionCtor>).SpeechRecognition ??
    (window as unknown as Record<string, SpeechRecognitionCtor>).webkitSpeechRecognition ??
    null
  );
}

export function ChatInput({
  value,
  onChange,
  onSend,
  disabled,
  selectedFunction,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const [csvFile, setCsvFile] = useState<{ name: string; rows: Record<string, unknown>[] } | null>(null);
  const [listening, setListening] = useState(false);
  const [speechSupported] = useState(() => getSpeechRecognition() !== null);

  // Cleanup recognition on unmount
  useEffect(() => {
    return () => {
      recognitionRef.current?.abort();
    };
  }, []);

  const toggleVoice = useCallback(() => {
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }

    const Ctor = getSpeechRecognition();
    if (!Ctor) return;

    const recognition = new Ctor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    // Track the text that existed before we started listening
    const baseText = value;

    recognition.onresult = (e: SpeechRecognitionEvent) => {
      let transcript = "";
      for (let i = 0; i < e.results.length; i++) {
        transcript += e.results[i][0].transcript;
      }
      // Append voice text after any existing typed text
      const separator = baseText && !baseText.endsWith(" ") ? " " : "";
      onChange(baseText + separator + transcript);
    };

    recognition.onerror = () => {
      setListening(false);
    };

    recognition.onend = () => {
      setListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  }, [listening, value, onChange]);

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (canSend) {
        handleSend();
        if (textareaRef.current) {
          textareaRef.current.style.height = "auto";
        }
      }
    }
  };

  const handleSend = () => {
    // Stop listening if active
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
    }
    if (csvFile) {
      onSend(csvFile.rows);
      setCsvFile(null);
    } else {
      onSend();
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        setCsvFile({
          name: file.name,
          rows: results.data as Record<string, unknown>[],
        });
      },
      error: () => {
        setCsvFile(null);
      },
    });

    e.target.value = "";
  };

  const canSend = !!value.trim() && !disabled;

  return (
    <div className="border-t border-clay-700/60 bg-clay-850 p-3">
      {/* Function context chip */}
      {selectedFunction && (
        <div className="flex items-center gap-1.5 mb-2">
          <Blocks className="h-3 w-3 text-clay-300" />
          <span className="text-xs text-clay-200">
            Using {selectedFunction.name}
          </span>
        </div>
      )}

      {/* CSV file preview chip */}
      {csvFile && (
        <div className="flex items-center gap-1.5 mb-2">
          <Paperclip className="h-3 w-3 text-kiln-teal" />
          <span className="text-xs text-kiln-teal font-medium">
            {csvFile.rows.length} rows from {csvFile.name}
          </span>
          <button
            onClick={() => setCsvFile(null)}
            className="text-clay-400 hover:text-clay-100 transition-colors"
          >
            <X className="h-3 w-3" />
          </button>
        </div>
      )}

      {/* Listening indicator */}
      {listening && (
        <div className="flex items-center gap-1.5 mb-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
          </span>
          <span className="text-xs text-red-400 font-medium">Listening...</span>
        </div>
      )}

      {/* Input row */}
      <div className="flex items-end gap-2">
        {/* CSV upload button — visible only when function is selected */}
        {selectedFunction && (
          <>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled}
              className="text-clay-400 hover:text-kiln-teal hover:bg-kiln-teal/10 shrink-0"
              title="Upload CSV"
            >
              <Paperclip className="h-5 w-5" />
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              className="hidden"
              onChange={handleFileSelect}
            />
          </>
        )}

        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onInput={handleInput}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={
            selectedFunction
              ? "Type or paste your data..."
              : "Ask anything..."
          }
          rows={1}
          className="bg-clay-900/80 border border-clay-600/80 rounded-xl px-4 py-3 text-sm text-clay-100 placeholder:text-clay-400 resize-none min-h-[44px] max-h-[160px] w-full focus:outline-none focus:border-kiln-teal disabled:opacity-50 disabled:cursor-not-allowed"
        />

        {/* Voice button */}
        {speechSupported && (
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleVoice}
            disabled={disabled}
            className={
              listening
                ? "text-red-400 hover:text-red-300 hover:bg-red-400/10 shrink-0"
                : "text-clay-400 hover:text-clay-100 hover:bg-clay-700 shrink-0"
            }
            title={listening ? "Stop listening" : "Voice input"}
          >
            {listening ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
          </Button>
        )}

        <Button
          variant="ghost"
          size="icon"
          onClick={handleSend}
          disabled={!canSend}
          className={
            canSend
              ? "text-kiln-teal hover:text-kiln-teal hover:bg-kiln-teal/10 shrink-0"
              : "text-clay-400 cursor-not-allowed shrink-0"
          }
        >
          <Send className="h-5 w-5" />
        </Button>
      </div>
    </div>
  );
}
