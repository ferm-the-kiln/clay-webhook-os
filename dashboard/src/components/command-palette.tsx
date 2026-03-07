"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Dialog as DialogPrimitive } from "radix-ui";
import { Command } from "cmdk";
import {
  LayoutDashboard,
  FlaskConical,
  BookOpen,
  Rocket,
  TestTubes,
  Settings,
  Zap,
  Search,
} from "lucide-react";
import { SKILL_SAMPLES } from "@/lib/constants";

const PAGES = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Run", href: "/run", icon: FlaskConical },
  { name: "Batch Processing", href: "/run?tab=batch", icon: FlaskConical },
  { name: "Campaigns", href: "/campaigns", icon: Rocket },
  { name: "Review Queue", href: "/campaigns?tab=review", icon: Rocket },
  { name: "Context Hub", href: "/context", icon: BookOpen },
  { name: "Skills", href: "/skills", icon: TestTubes },
  { name: "Pipelines", href: "/skills", icon: TestTubes },
  { name: "Skills Lab", href: "/skills?tab=lab", icon: TestTubes },
  { name: "Settings", href: "/settings", icon: Settings },
  { name: "Analytics", href: "/settings?tab=analytics", icon: Settings },
];

const SKILLS = Object.keys(SKILL_SAMPLES);

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  const navigate = (href: string) => {
    router.push(href);
    setOpen(false);
  };

  return (
    <DialogPrimitive.Root open={open} onOpenChange={setOpen}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=closed]:animate-out data-[state=closed]:fade-out-0" />
        <DialogPrimitive.Content className="fixed left-1/2 top-[20%] z-50 w-full max-w-lg -translate-x-1/2 data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95">
          <Command className="rounded-xl border border-clay-700 bg-clay-900 shadow-2xl overflow-hidden">
            <div className="flex items-center border-b border-clay-800 px-3">
              <Search className="h-4 w-4 text-clay-500 mr-2 shrink-0" />
              <Command.Input
                placeholder="Search pages, skills, actions..."
                className="h-12 w-full bg-transparent text-clay-100 placeholder:text-clay-600 text-sm outline-none"
              />
            </div>
            <Command.List className="max-h-72 overflow-y-auto p-2">
              <Command.Empty className="py-6 text-center text-sm text-clay-500">
                No results found.
              </Command.Empty>

              <Command.Group
                heading="Pages"
                className="[&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:text-clay-500 [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5"
              >
                {PAGES.map((page) => (
                  <Command.Item
                    key={page.href}
                    value={page.name}
                    onSelect={() => navigate(page.href)}
                    className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-clay-300 cursor-pointer data-[selected=true]:bg-kiln-teal/10 data-[selected=true]:text-kiln-teal"
                  >
                    <page.icon className="h-4 w-4" />
                    {page.name}
                  </Command.Item>
                ))}
              </Command.Group>

              <Command.Group
                heading="Skills"
                className="[&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:text-clay-500 [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5"
              >
                {SKILLS.map((skill) => (
                  <Command.Item
                    key={skill}
                    value={`skill ${skill}`}
                    onSelect={() => navigate(`/run?skill=${skill}`)}
                    className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-clay-300 cursor-pointer data-[selected=true]:bg-kiln-teal/10 data-[selected=true]:text-kiln-teal"
                  >
                    <Zap className="h-4 w-4" />
                    Run {skill}
                  </Command.Item>
                ))}
              </Command.Group>
            </Command.List>

            <div className="border-t border-clay-800 px-3 py-2 flex items-center gap-4 text-xs text-clay-600">
              <span>Navigate <kbd className="ml-1 rounded border border-clay-700 bg-clay-800 px-1.5 py-0.5 font-mono text-clay-400">Enter</kbd></span>
              <span>Close <kbd className="ml-1 rounded border border-clay-700 bg-clay-800 px-1.5 py-0.5 font-mono text-clay-400">Esc</kbd></span>
            </div>
          </Command>
          <DialogPrimitive.Title className="sr-only">Command Palette</DialogPrimitive.Title>
          <DialogPrimitive.Description className="sr-only">Search for pages, skills, and actions</DialogPrimitive.Description>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
