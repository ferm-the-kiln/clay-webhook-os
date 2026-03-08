"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { LayoutDashboard, FlaskConical, TestTubes, Rocket, Library, Settings, Activity, FolderTree } from "lucide-react";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";

const NAV = [
  {
    href: "/",
    label: "Dashboard",
    icon: LayoutDashboard,
    shortcut: "1",
  },
  {
    href: "/run",
    label: "Run",
    icon: FlaskConical,
    shortcut: "2",
  },
  {
    href: "/campaigns",
    label: "Campaigns",
    icon: Rocket,
    shortcut: "3",
  },
  {
    href: "/plays",
    label: "Plays",
    icon: Library,
    shortcut: "4",
  },
  {
    href: "/skills",
    label: "Skills",
    icon: TestTubes,
    shortcut: "5",
  },
  {
    href: "/status",
    label: "Status",
    icon: Activity,
    shortcut: "6",
  },
  {
    href: "/context",
    label: "Context",
    icon: FolderTree,
    shortcut: "7",
  },
  {
    href: "/settings",
    label: "Settings",
    icon: Settings,
    shortcut: "8",
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  // Listen for custom event from header hamburger button
  useEffect(() => {
    const handleToggle = () => setMobileOpen((prev) => !prev);
    document.addEventListener("toggle-mobile-sidebar", handleToggle);
    return () =>
      document.removeEventListener("toggle-mobile-sidebar", handleToggle);
  }, []);

  // Keyboard shortcuts for navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && ["1", "2", "3", "4", "5", "6", "7", "8"].includes(e.key)) {
        e.preventDefault();
        const idx = parseInt(e.key) - 1;
        const nav = NAV[idx];
        if (nav) window.location.href = nav.href;
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  const navContent = (compact: boolean, onNavigate?: () => void) => (
    <nav className="flex flex-col gap-1">
      {NAV.map((item) => {
        const active = pathname === item.href;
        const btn = (
          <Button
            key={item.href}
            variant="ghost"
            asChild
            className={cn(
              "h-10 transition-all duration-200",
              compact ? "justify-center px-2" : "justify-start gap-3 px-3",
              active
                ? "bg-kiln-teal/10 text-kiln-teal hover:bg-kiln-teal/15 hover:text-kiln-teal"
                : "text-clay-400 hover:bg-clay-800 hover:text-clay-200"
            )}
          >
            <Link href={item.href} onClick={onNavigate}>
              <item.icon className="h-5 w-5 shrink-0" />
              {!compact && (
                <>
                  <span className="flex-1">{item.label}</span>
                  <kbd className="hidden lg:inline-block text-[10px] text-clay-600 font-mono border border-clay-800 rounded px-1 py-0.5">
                    {"\u2318"}{item.shortcut}
                  </kbd>
                </>
              )}
            </Link>
          </Button>
        );

        if (compact) {
          return (
            <Tooltip key={item.href}>
              <TooltipTrigger asChild>{btn}</TooltipTrigger>
              <TooltipContent
                side="right"
                className="bg-clay-900 border-clay-700 text-clay-200 text-xs"
              >
                <span className="flex items-center gap-2">
                  {item.label}
                  <kbd className="rounded border border-clay-700 bg-clay-800 px-1 py-0.5 font-mono text-[10px] text-clay-400">
                    {"\u2318"}{item.shortcut}
                  </kbd>
                </span>
              </TooltipContent>
            </Tooltip>
          );
        }

        return btn;
      })}
    </nav>
  );

  return (
    <>
      {/* Desktop sidebar: full width on lg, icon-only on md */}
      <aside className="relative z-10 hidden md:flex shrink-0 border-r border-clay-800 bg-white p-4 flex-col gap-1 lg:w-56 w-16">
        {/* Logo */}
        <div className="mb-6 px-3 flex items-center gap-3">
          <Image
            src="/brand-assets/the-kiln-logo.avif"
            alt="The Kiln"
            width={32}
            height={32}
            className="rounded-md"
          />
          <div className="hidden lg:block">
            <h1 className="text-lg font-bold text-clay-100 font-[family-name:var(--font-sans)]">
              Clay OS
            </h1>
            <p className="text-[10px] text-clay-500 tracking-wider uppercase">
              Webhook Dashboard
            </p>
          </div>
        </div>

        {/* Nav - compact on md, full on lg */}
        <div className="hidden lg:block">{navContent(false)}</div>
        <div className="lg:hidden">{navContent(true)}</div>
      </aside>

      {/* Mobile drawer */}
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-64 bg-white border-clay-800 p-4">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <SheetDescription className="sr-only">Main navigation menu</SheetDescription>
          <div className="mb-6 px-3 flex items-center gap-3">
            <Image
              src="/brand-assets/the-kiln-logo.avif"
              alt="The Kiln"
              width={32}
              height={32}
              className="rounded-md"
            />
            <div>
              <h1 className="text-lg font-bold text-clay-100 font-[family-name:var(--font-sans)]">
                Clay OS
              </h1>
              <p className="text-[10px] text-clay-500 tracking-wider uppercase">
                Webhook Dashboard
              </p>
            </div>
          </div>
          {navContent(false, () => setMobileOpen(false))}
        </SheetContent>
      </Sheet>

      {/* Mobile bottom nav */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 z-50 border-t border-clay-800 bg-white/95 backdrop-blur-sm">
        <nav className="flex items-center justify-around py-2">
          {NAV.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex flex-col items-center gap-0.5 px-3 py-1 transition-colors",
                  active ? "text-kiln-teal" : "text-clay-500"
                )}
              >
                <item.icon className="h-5 w-5" />
                {active && <span className="h-1 w-1 rounded-full bg-kiln-teal" />}
              </Link>
            );
          })}
        </nav>
      </div>
    </>
  );
}

export { NAV };
