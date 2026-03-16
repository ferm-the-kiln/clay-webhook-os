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
  Table2,
  TestTubes,
  Library,
  Settings,
  Activity,
  FolderTree,
  PenLine,
  MoreHorizontal,
  Mail,
  ListOrdered,
  UserSearch,
  Send,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { fetchDataset } from "@/lib/api";
import type { Dataset } from "@/lib/types";

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
    id: "prospect",
    label: "Prospect",
    icon: UserSearch,
    accentColor: "kiln-teal",
    items: [
      { href: "/prospect", label: "Workbench", icon: UserSearch, shortcut: "1" },
    ],
  },
  {
    id: "generate",
    label: "Generate",
    icon: PenLine,
    accentColor: "kiln-indigo",
    items: [
      { href: "/pipeline/email-lab", label: "Email Lab", icon: Mail, shortcut: "2" },
      { href: "/pipeline/sequence-lab", label: "Sequence Lab", icon: ListOrdered, shortcut: "3" },
    ],
  },
  {
    id: "deliver",
    label: "Deliver",
    icon: Send,
    accentColor: "kiln-indigo",
    items: [
      { href: "/pipeline/send", label: "Send", icon: Send, shortcut: "4" },
      { href: "/pipeline/plays", label: "Plays", icon: Library, shortcut: "5" },
    ],
  },
  {
    id: "platform",
    label: "Platform",
    accentColor: "clay-500",
    items: [
      { href: "/", label: "Dashboard", icon: LayoutDashboard },
      { href: "/run", label: "Run", icon: FlaskConical },
      { href: "/batch-results", label: "Batch Results", icon: Table2 },
      { href: "/context", label: "Context", icon: FolderTree },
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

// Map nav items to pipeline stages for completion dots
const STAGE_NAV_MAP: Record<string, string> = {
  "/pipeline/email-lab": "email-gen",
  "/pipeline/send": "send",
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
  const [activeDataset, setActiveDataset] = useState<Dataset | null>(null);

  // Fetch active dataset for sidebar indicator (outside DatasetProvider)
  useEffect(() => {
    if (!pathname.startsWith("/pipeline") && !pathname.startsWith("/prospect")) {
      setActiveDataset(null);
      return;
    }
    const storedId = localStorage.getItem("clay-os-active-dataset-id");
    if (!storedId) {
      setActiveDataset(null);
      return;
    }
    fetchDataset(storedId)
      .then((ds) => setActiveDataset(ds))
      .catch(() => setActiveDataset(null));
  }, [pathname]);

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
          <div key={section.id} className={sIdx > 0 ? "mt-3" : ""}>
            {/* Section header */}
            {!compact && (
              <div className="flex items-center gap-2 px-3 mb-1">
                {section.icon && (
                  <section.icon className={cn("h-3 w-3", accent.text)} />
                )}
                <span className="text-[10px] font-semibold text-clay-300 uppercase tracking-[0.1em]">
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
                      "h-8 transition-all duration-150 relative",
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
                          "absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-4 rounded-full",
                          section.accentColor === "kiln-indigo" ? "bg-kiln-indigo" : section.accentColor === "kiln-teal" ? "bg-kiln-teal" : "bg-clay-400"
                        )} />
                      )}
                      <item.icon className="h-4 w-4 shrink-0" />
                      {!compact && (
                        <>
                          <span className="flex-1 text-[13px] flex items-center gap-1.5">
                            {item.label}
                            {activeDataset && STAGE_NAV_MAP[item.href] && activeDataset.stages_completed.includes(STAGE_NAV_MAP[item.href]) && (
                              <span className="h-1.5 w-1.5 rounded-full bg-kiln-teal shrink-0" />
                            )}
                          </span>
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
    { href: "/prospect", label: "Prospect", icon: UserSearch, matchPrefix: "/prospect" },
    { href: "/pipeline/email-lab", label: "Email Lab", icon: PenLine },
    { href: "/pipeline/send", label: "Send", icon: Send },
    { href: "/pipeline/plays", label: "Plays", icon: Library },
    { href: "/settings", label: "More", icon: MoreHorizontal, matchPrefix: "/settings" },
  ];

  return (
    <>
      {/* Desktop sidebar: full width on lg, icon-only on md */}
      <aside className="relative z-10 hidden md:flex shrink-0 border-r border-clay-600 bg-clay-800 p-4 flex-col gap-1 lg:w-56 w-16">
        {/* Logo */}
        <div className="mb-5 px-3 flex items-center gap-3">
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
              Pipeline Dashboard
            </p>
          </div>
        </div>

        {/* Active dataset indicator */}
        {activeDataset && (pathname.startsWith("/pipeline") || pathname.startsWith("/prospect")) && (
          <div className="hidden lg:block px-3 mb-3">
            <div className="text-[10px] text-clay-400 truncate">
              <span className="text-kiln-teal">●</span>{" "}
              {activeDataset.name}
              <span className="text-clay-500 ml-1">({activeDataset.row_count})</span>
            </div>
          </div>
        )}

        {/* Nav - compact on md, full on lg */}
        <div className="hidden lg:block flex-1 overflow-y-auto">{renderSectionNav(false)}</div>
        <div className="lg:hidden flex-1 overflow-y-auto">{renderSectionNav(true)}</div>
      </aside>

      {/* Mobile drawer */}
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-64 bg-clay-800 border-clay-600 p-4">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <SheetDescription className="sr-only">Main navigation menu</SheetDescription>
          <div className="mb-5 px-3 flex items-center gap-3">
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
                Pipeline Dashboard
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
