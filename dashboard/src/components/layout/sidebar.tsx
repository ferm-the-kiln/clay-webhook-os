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
import {
  LayoutDashboard,
  FlaskConical,
  TestTubes,
  Library,
  Settings,
  Activity,
  FolderTree,
  PenLine,
  Radar,
  Brain,
  Search,
  Target,
  MoreHorizontal,
  Mail,
  ListOrdered,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  shortcut?: string;
}

interface NavSection {
  id: string;
  label: string;
  icon?: LucideIcon;
  accentColor: string;
  items: NavItem[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    id: "overview",
    label: "Overview",
    accentColor: "clay-500",
    items: [
      { href: "/", label: "Dashboard", icon: LayoutDashboard, shortcut: "1" },
      { href: "/run", label: "Run", icon: FlaskConical, shortcut: "2" },
    ],
  },
  {
    id: "outbound",
    label: "Outbound",
    icon: PenLine,
    accentColor: "kiln-teal",
    items: [
      { href: "/outbound", label: "Outbound", icon: PenLine, shortcut: "3" },
      { href: "/email-lab", label: "Email Lab", icon: Mail, shortcut: "8" },
      { href: "/sequence-lab", label: "Sequence Lab", icon: ListOrdered },
    ],
  },
  {
    id: "analyze",
    label: "Analyze",
    icon: Radar,
    accentColor: "kiln-indigo",
    items: [
      { href: "/analyze", label: "Analyze Home", icon: Brain },
      { href: "/analyze/research", label: "Research", icon: Search, shortcut: "4" },
      { href: "/analyze/scoring", label: "Scoring", icon: Target, shortcut: "5" },
      { href: "/analyze/plays", label: "Plays", icon: Library, shortcut: "6" },
    ],
  },
  {
    id: "platform",
    label: "Platform",
    accentColor: "clay-500",
    items: [
      { href: "/context", label: "Context", icon: FolderTree, shortcut: "7" },
      { href: "/lab", label: "Skills Lab", icon: TestTubes },
      { href: "/status", label: "Status", icon: Activity },
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

// Flat list for keyboard shortcuts
const ALL_NAV_ITEMS = NAV_SECTIONS.flatMap((s) => s.items);
const SHORTCUT_MAP = ALL_NAV_ITEMS.reduce<Record<string, string>>((acc, item) => {
  if (item.shortcut) acc[item.shortcut] = item.href;
  return acc;
}, {});

// Accent color classes per section
const ACCENT_CLASSES: Record<string, { active: string; text: string }> = {
  "clay-500": {
    active: "bg-clay-500/10 text-clay-200 hover:bg-clay-500/15 hover:text-clay-200",
    text: "text-clay-300",
  },
  "kiln-teal": {
    active: "bg-kiln-teal/10 text-kiln-teal hover:bg-kiln-teal/15 hover:text-kiln-teal",
    text: "text-kiln-teal",
  },
  "kiln-indigo": {
    active: "bg-kiln-indigo/10 text-kiln-indigo hover:bg-kiln-indigo/15 hover:text-kiln-indigo",
    text: "text-kiln-indigo",
  },
};

function getSectionForPath(pathname: string): NavSection | undefined {
  return NAV_SECTIONS.find((s) =>
    s.items.some((item) =>
      item.href === "/" ? pathname === "/" : pathname.startsWith(item.href)
    )
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const handleToggle = () => setMobileOpen((prev) => !prev);
    document.addEventListener("toggle-mobile-sidebar", handleToggle);
    return () =>
      document.removeEventListener("toggle-mobile-sidebar", handleToggle);
  }, []);

  // Keyboard shortcuts for navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && SHORTCUT_MAP[e.key]) {
        e.preventDefault();
        window.location.href = SHORTCUT_MAP[e.key];
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname === href || pathname.startsWith(href + "/");
  };

  const renderSectionNav = (compact: boolean, onNavigate?: () => void) => (
    <nav className="flex flex-col gap-0.5">
      {NAV_SECTIONS.map((section, sIdx) => {
        const accent = ACCENT_CLASSES[section.accentColor] || ACCENT_CLASSES["clay-500"];

        return (
          <div key={section.id} className={sIdx > 0 ? "mt-4" : ""}>
            {/* Section header */}
            {!compact && (
              <div className="flex items-center gap-2 px-3 mb-1.5">
                {section.icon && (
                  <section.icon className={cn("h-3.5 w-3.5", accent.text)} />
                )}
                <span className="text-[11px] font-semibold text-clay-300 uppercase tracking-[0.1em]">
                  {section.label}
                </span>
              </div>
            )}

            {compact && sIdx > 0 && (
              <div className="mx-2 mb-2 border-t border-clay-600" />
            )}

            {/* Section items */}
            <div className="flex flex-col gap-0.5">
              {section.items.map((item) => {
                const active = isActive(item.href);
                const btn = (
                  <Button
                    key={item.href}
                    variant="ghost"
                    asChild
                    className={cn(
                      "h-9 transition-all duration-150 relative",
                      compact ? "justify-center px-2" : "justify-start gap-3 px-3",
                      active
                        ? accent.active
                        : "text-clay-200 hover:bg-clay-700 hover:text-clay-100"
                    )}
                  >
                    <Link href={item.href} onClick={onNavigate}>
                      {/* Active accent bar */}
                      {active && !compact && (
                        <span className={cn(
                          "absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-5 rounded-full",
                          section.accentColor === "kiln-indigo" ? "bg-kiln-indigo" : "bg-kiln-teal"
                        )} />
                      )}
                      <item.icon className="h-4.5 w-4.5 shrink-0" />
                      {!compact && (
                        <>
                          <span className="flex-1 text-sm">{item.label}</span>
                          {item.shortcut && (
                            <kbd className="retro-keycap hidden lg:inline-block">
                              {"\u2318"}{item.shortcut}
                            </kbd>
                          )}
                        </>
                      )}
                    </Link>
                  </Button>
                );

                if (compact) {
                  return (
                    <Tooltip key={item.href}>
                      <TooltipTrigger asChild>{btn}</TooltipTrigger>
                      <TooltipContent side="right">
                        <span className="flex items-center gap-2">
                          {item.label}
                          {item.shortcut && (
                            <kbd className="retro-keycap">
                              {"\u2318"}{item.shortcut}
                            </kbd>
                          )}
                        </span>
                      </TooltipContent>
                    </Tooltip>
                  );
                }

                return btn;
              })}
            </div>
          </div>
        );
      })}
    </nav>
  );

  // Mobile bottom nav — 5-item bar
  const mobileBottomItems: { href: string; label: string; icon: LucideIcon; matchPrefix?: string }[] = [
    { href: "/", label: "Dashboard", icon: LayoutDashboard },
    { href: "/outbound", label: "Outbound", icon: PenLine, matchPrefix: "/outbound" },
    { href: "/run", label: "Run", icon: FlaskConical },
    { href: "/analyze", label: "Analyze", icon: Radar, matchPrefix: "/analyze" },
    { href: "/settings", label: "More", icon: MoreHorizontal, matchPrefix: "/settings" },
  ];

  return (
    <>
      {/* Desktop sidebar: full width on lg, icon-only on md */}
      <aside className="relative z-10 hidden md:flex shrink-0 border-r border-clay-600 bg-clay-800 p-4 flex-col gap-1 lg:w-56 w-16">
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
            <h1 className="text-lg font-bold text-clay-100 font-[family-name:var(--font-sans)] tracking-tight">
              Clay OS
            </h1>
            <p className="text-[10px] text-clay-300 tracking-[0.1em] uppercase font-mono">
              Webhook Dashboard
            </p>
          </div>
        </div>

        {/* Nav - compact on md, full on lg */}
        <div className="hidden lg:block flex-1 overflow-y-auto">{renderSectionNav(false)}</div>
        <div className="lg:hidden flex-1 overflow-y-auto">{renderSectionNav(true)}</div>
      </aside>

      {/* Mobile drawer */}
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-64 bg-clay-800 border-clay-600 p-4">
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
              <h1 className="text-lg font-bold text-clay-100 font-[family-name:var(--font-sans)] tracking-tight">
                Clay OS
              </h1>
              <p className="text-[10px] text-clay-300 tracking-[0.1em] uppercase font-mono">
                Webhook Dashboard
              </p>
            </div>
          </div>
          {renderSectionNav(false, () => setMobileOpen(false))}
        </SheetContent>
      </Sheet>

      {/* Mobile bottom nav — 5-item */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 z-50 border-t border-clay-600 bg-clay-800/95 backdrop-blur-sm">
        <nav className="flex items-center justify-around py-2">
          {mobileBottomItems.map((item) => {
            const active = item.matchPrefix
              ? pathname.startsWith(item.matchPrefix)
              : pathname === item.href;
            const section = getSectionForPath(item.href);
            const colorClass = active
              ? section?.accentColor === "kiln-indigo"
                ? "text-kiln-indigo"
                : "text-kiln-teal"
              : "text-clay-300";
            const dotColor = section?.accentColor === "kiln-indigo"
              ? "bg-kiln-indigo shadow-[0_0_6px_rgba(67,56,202,0.5)]"
              : "bg-kiln-teal shadow-[0_0_6px_rgba(74,158,173,0.5)]";

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex flex-col items-center gap-0.5 px-3 py-1 transition-colors duration-150",
                  colorClass
                )}
              >
                <item.icon className="h-5 w-5" />
                <span className="text-[10px]">{item.label}</span>
                {active && <span className={cn("h-1 w-1 rounded-full", dotColor)} />}
              </Link>
            );
          })}
        </nav>
      </div>
    </>
  );
}

export { NAV_SECTIONS, ALL_NAV_ITEMS };
export type { NavSection, NavItem };
