"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

const SHORTCUT_GROUPS = [
  {
    title: "Navigation",
    shortcuts: [
      { keys: ["\u2318", "1"], label: "Dashboard" },
      { keys: ["\u2318", "2"], label: "Run" },
      { keys: ["\u2318", "3"], label: "Campaigns" },
      { keys: ["\u2318", "4"], label: "Skills" },
      { keys: ["\u2318", "5"], label: "Settings" },
      { keys: ["\u2318", "6"], label: "Status" },
    ],
  },
  {
    title: "Actions",
    shortcuts: [
      { keys: ["\u2318", "K"], label: "Command palette" },
      { keys: ["\u2318", "\u21A9"], label: "Run skill (playground)" },
    ],
  },
  {
    title: "General",
    shortcuts: [
      { keys: ["?"], label: "Show shortcuts" },
      { keys: ["Esc"], label: "Close dialog / panel" },
    ],
  },
];

export function KeyboardShortcutsDialog() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.key === "?" &&
        !e.metaKey &&
        !e.ctrlKey &&
        !(e.target instanceof HTMLInputElement) &&
        !(e.target instanceof HTMLTextAreaElement) &&
        !(e.target as HTMLElement)?.isContentEditable
      ) {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="border-clay-700 bg-clay-900 max-w-md">
        <DialogHeader>
          <DialogTitle className="text-clay-100">Keyboard Shortcuts</DialogTitle>
          <DialogDescription className="text-clay-500">
            Quick access to common actions
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-5">
          {SHORTCUT_GROUPS.map((group) => (
            <div key={group.title}>
              <h3 className="text-xs font-medium text-clay-500 uppercase tracking-wider mb-2">
                {group.title}
              </h3>
              <div className="space-y-1.5">
                {group.shortcuts.map((shortcut) => (
                  <div
                    key={shortcut.label}
                    className="flex items-center justify-between py-1"
                  >
                    <span className="text-sm text-clay-300">{shortcut.label}</span>
                    <div className="flex items-center gap-1">
                      {shortcut.keys.map((key, i) => (
                        <kbd
                          key={i}
                          className="min-w-[24px] text-center rounded border border-clay-700 bg-clay-800 px-1.5 py-0.5 font-mono text-xs text-clay-400"
                        >
                          {key}
                        </kbd>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
