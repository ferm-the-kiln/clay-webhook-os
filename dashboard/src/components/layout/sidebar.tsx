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
  Rocket,
  Library,
  Settings,
  Activity,
  FolderTree,
  PenLine,
  Radar,
  Mail,
  CheckSquare,
  Brain,
  Search,
  Target,
  MoreHorizontal,
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
      { href: "/outbound", label: "Outbound Home", icon: PenLine },
      { href: "/outbound/campaigns", label: "Campaigns", icon: Rocket, shortcut: "3" },
      { href: "/outbound/sequences", label: "Sequences", icon: Mail, shortcut: "4" },
      { href: "/outbound/review", label: "Review Queue", icon: CheckSquare, shortcut: "5" },
    ],
  },
  {
    id: "analyze",
    label: "Analyze",
    icon: Radar,
    accentColor: "kiln-indigo",
    items: [
      { href: "/analyze", label: "Analyze Home", icon: Brain },
      { href: "/analyze/research", label: "Research", icon: Search, shortcut: "6" },
      { href: "/analyze/scoring", label: "Scoring", icon: Target, shortcut: "7" },
      { href: "/analyze/plays", label: "Plays", icon: Library, shortcut: "8" },
    ],
  },
  {
    id: "platform",
    label: "Platform",
    accentColor: "clay-500",
    items: [
      { href: "/context", label: "Context", icon: FolderTree, shortcut: "9" },
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
    active: "bg-clay-500/10 text-clay-300 hover:bg-clay-500/15 hover:text-clay-300",
    text: "text-clay-500",
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
                <span className="text-[10px] font-semibold text-clay-500 uppercase tracking-wider">
                  {section.label}
                </span>
              </div>
            )}

            {compact && sIdx > 0 && (
              <div className="mx-2 mb-2 border-t border-clay-800" />
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
                      "h-9 transition-all duration-200",
                      compact ? "justify-center px-2" : "justify-start gap-3 px-3",
                      active
                        ? accent.active
                        : "text-clay-400 hover:bg-clay-800 hover:text-clay-200"
                    )}
                  >
                    <Link href={item.href} onClick={onNavigate}>
                      <item.icon className="h-4.5 w-4.5 shrink-0" />
                      {!compact && (
                        <>
                          <span className="flex-1 text-sm">{item.label}</span>
                          {item.shortcut && (
                            <kbd className="hidden lg:inline-block text-[10px] text-clay-600 font-mono border border-clay-800 rounded px-1 py-0.5">
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
                      <TooltipContent
                        side="right"
                        className="bg-clay-900 border-clay-700 text-clay-200 text-xs"
                      >
                        <span className="flex items-center gap-2">
                          {item.label}
                          {item.shortcut && (
                            <kbd className="rounded border border-clay-700 bg-clay-800 px-1 py-0.5 font-mono text-[10px] text-clay-400">
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
        <div className="hidden lg:block flex-1 overflow-y-auto">{renderSectionNav(false)}</div>
        <div className="lg:hidden flex-1 overflow-y-auto">{renderSectionNav(true)}</div>
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
          {renderSectionNav(false, () => setMobileOpen(false))}
        </SheetContent>
      </Sheet>

      {/* Mobile bottom nav — 5-item */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 z-50 border-t border-clay-800 bg-white/95 backdrop-blur-sm">
        <nav className="flex items-center justify-around py-2">
          {mobileBottomItems.map((item) => {
            const active = item.matchPrefix
              ? pathname.startsWith(item.matchPrefix)
              : pathname === item.href;
            const section = getSectionForPath(item.href);
            const colorClass = active
              ? section?.accentColor === "kiln-indigo"
                ? "text-kiln-indigo"
                : section?.accentColor === "kiln-teal"
                  ? "text-kiln-teal"
                  : "text-kiln-teal"
              : "text-clay-500";
            const dotColor = section?.accentColor === "kiln-indigo"
              ? "bg-kiln-indigo"
              : "bg-kiln-teal";

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex flex-col items-center gap-0.5 px-3 py-1 transition-colors",
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
