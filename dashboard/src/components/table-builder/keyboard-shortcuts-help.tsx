"use client";

import { useState } from "react";
import { HelpCircle, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const SHORTCUTS = [
  { keys: ["Cmd", "Enter"], desc: "Run enrichments" },
  { keys: ["Escape"], desc: "Stop execution / Close" },
  { keys: ["Cmd", "F"], desc: "Search in table" },
  { keys: ["Cmd", "Z"], desc: "Undo" },
  { keys: ["Cmd", "Shift", "Z"], desc: "Redo" },
  { keys: ["Tab"], desc: "Next cell" },
  { keys: ["Enter"], desc: "Edit cell / Confirm" },
  { keys: ["Double-click"], desc: "Edit input cell" },
  { keys: ["Cmd", "V"], desc: "Paste from clipboard" },
  { keys: ["Delete"], desc: "Delete selected rows" },
];

function KeyBadge({ children }: { children: string }) {
  return (
    <kbd className="px-1.5 py-0.5 rounded bg-clay-700 border border-clay-500 text-[10px] font-mono text-clay-100">
      {children}
    </kbd>
  );
}

export function KeyboardShortcutsHelp() {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* Trigger button */}
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-4 right-4 z-40 w-7 h-7 rounded-full bg-clay-700 border border-clay-500 flex items-center justify-center text-clay-300 hover:text-clay-100 hover:bg-clay-500 transition-colors shadow-lg"
        title="Keyboard shortcuts"
      >
        <HelpCircle className="w-3.5 h-3.5" />
      </button>

      {/* Modal */}
      <AnimatePresence>
        {open && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/40 z-50"
              onClick={() => setOpen(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-80 bg-clay-900 border border-clay-500 rounded-lg shadow-2xl p-4"
            >
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-white">
                  Keyboard Shortcuts
                </h3>
                <button
                  onClick={() => setOpen(false)}
                  className="p-1 rounded hover:bg-clay-700 text-clay-300"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="space-y-2">
                {SHORTCUTS.map((s, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between gap-2"
                  >
                    <span className="text-xs text-clay-200">{s.desc}</span>
                    <div className="flex items-center gap-1">
                      {s.keys.map((k, j) => (
                        <KeyBadge key={j}>{k === "Cmd" ? "⌘" : k}</KeyBadge>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
