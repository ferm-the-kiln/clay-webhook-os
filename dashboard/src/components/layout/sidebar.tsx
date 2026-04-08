"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { getPersona, setPersona, onPreferencesChanged } from "@/lib/user-preferences";
import type { UserPersona } from "@/lib/user-preferences";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import {
  Blocks,
  BookOpen,
  Bug,
  FlaskConical,
  Home,
  MessageSquare,
  Search,
  Send,
  FolderTree,
  Table2,
  Users,
  ArrowLeftRight,
  Layers,
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
  repLabel?: string; // Friendly label shown in rep mode
  icon: LucideIcon;
  repIcon?: LucideIcon; // Different icon in rep mode
  shortcut?: string;
  repOnly?: boolean;   // Only shown in rep mode
  powerOnly?: boolean; // Only shown in power mode
}

interface NavSection {
  id: string;
  label: string;
  icon?: LucideIcon;
  accentColor: string;
  items: NavItem[];
}

// ── Rep mode: 5 items with friendly labels ───────────────

const REP_NAV_SECTIONS: NavSection[] = [
  {
    id: "main",
    label: "Platform",
    accentColor: "kiln-teal",
    items: [
      { href: "/", label: "Home", icon: Home, shortcut: "1" },
      { href: "/enrich", label: "Enrich", icon: Table2, shortcut: "T" },
      { href: "/research", label: "Research", icon: Search, shortcut: "3" },
      { href: "/prep", label: "Prep", icon: BookOpen, shortcut: "P" },
      { href: "/chat", label: "Chat", icon: MessageSquare, shortcut: "2" },
      { href: "/outbound", label: "Outbound", icon: Send, shortcut: "4" },
    ],
  },
];

// ── Power mode: all 9 items in two groups ────────────────

const POWER_NAV_SECTIONS: NavSection[] = [
  {
    id: "build",
    label: "Build",
    accentColor: "kiln-teal",
    items: [
      { href: "/", label: "Functions", icon: Blocks, shortcut: "1" },
      { href: "/chat", label: "Chat", icon: MessageSquare, shortcut: "2" },
      { href: "/workbench", label: "Workbench", icon: FlaskConical, shortcut: "3" },
      { href: "/tables", label: "Tables", icon: Table2, shortcut: "T" },
    ],
  },
  {
    id: "operate",
    label: "Operate",
    accentColor: "kiln-teal",
    items: [
      { href: "/outbound", label: "Outbound", icon: Send, shortcut: "4" },
      { href: "/context", label: "Context", icon: FolderTree, shortcut: "5" },
      { href: "/context/rack", label: "Rack", icon: Layers, shortcut: "" },
      { href: "/debugger", label: "Debugger", icon: Bug, shortcut: "6" },
      { href: "/clients/twelve-labs", label: "Communication", icon: Users, shortcut: "7" },
    ],
  },
];

function getNavSections(persona: UserPersona): NavSection[] {
  return persona === "rep" ? REP_NAV_SECTIONS : POWER_NAV_SECTIONS;
}

function getAllNavItems(persona: UserPersona): NavItem[] {
  return getNavSections(persona).flatMap((s) => s.items);
}

function getShortcutMap(persona: UserPersona): Record<string, string> {
  return getAllNavItems(persona).reduce<Record<string, string>>((acc, item) => {
    if (item.shortcut) acc[item.shortcut] = item.href;
    return acc;
  }, {});
}

// Accent color classes per section
const ACCENT_CLASSES: Record<string, { active: string; text: string }> = {
  "kiln-teal": {
    active: "bg-kiln-teal/10 text-kiln-teal hover:bg-kiln-teal/15 hover:text-kiln-teal",
    text: "text-kiln-teal",
  },
  "kiln-indigo": {
    active: "bg-kiln-indigo/10 text-kiln-indigo hover:bg-kiln-indigo/15 hover:text-kiln-indigo",
    text: "text-kiln-indigo",
  },
  "clay-500": {
    active: "bg-clay-500/10 text-clay-200 hover:bg-clay-500/15 hover:text-clay-200",
    text: "text-clay-300",
  },
};

export function Sidebar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [persona, setPersonaState] = useState<UserPersona>("rep");

  // Hydrate persona from localStorage
  useEffect(() => {
    setPersonaState(getPersona());
    return onPreferencesChanged(() => setPersonaState(getPersona()));
  }, []);

  // Hide sidebar on public portal view pages
  if (pathname.startsWith("/portal-view/")) return null;

  const navSections = getNavSections(persona);
  const shortcutMap = getShortcutMap(persona);

  const handleTogglePersona = () => {
    const next = persona === "rep" ? "power" : "rep";
    setPersona(next);
    setPersonaState(next);
  };

  useEffect(() => {
    const handleToggle = () => setMobileOpen((prev) => !prev);
    document.addEventListener("toggle-mobile-sidebar", handleToggle);
    return () =>
      document.removeEventListener("toggle-mobile-sidebar", handleToggle);
  }, []);

  // Keyboard shortcuts for navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && shortcutMap[e.key]) {
        e.preventDefault();
        window.location.href = shortcutMap[e.key];
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [shortcutMap]);

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname === href || pathname.startsWith(href + "/");
  };

  const renderSectionNav = (compact: boolean, onNavigate?: () => void) => (
    <nav className="flex flex-col gap-1">
      {navSections.map((section, sectionIdx) => {
        const accent = ACCENT_CLASSES[section.accentColor] || ACCENT_CLASSES["kiln-teal"];

        return (
          <div key={section.id}>
            {/* Section label — show for power mode with multiple sections */}
            {persona === "power" && navSections.length > 1 && !compact && (
              <p className={cn(
                "px-3 text-[10px] font-semibold uppercase tracking-wider text-clay-300",
                sectionIdx > 0 ? "mt-4 mb-1.5" : "mb-1.5"
              )}>
                {section.label}
              </p>
            )}
            {persona === "power" && navSections.length > 1 && compact && sectionIdx > 0 && (
              <div className="my-2 mx-2 border-t border-clay-600" />
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
                        <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-4 rounded-full bg-kiln-teal" />
                      )}
                      <item.icon className="h-4 w-4 shrink-0" />
                      {!compact && (
                        <>
                          <span className="flex-1 text-[13px]">
                            {item.label}
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

  const renderModeToggle = (compact: boolean) => (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          onClick={handleTogglePersona}
          className={cn(
            "flex items-center gap-2 rounded-lg px-3 py-2 text-clay-300 hover:text-clay-200 hover:bg-clay-700 transition-colors duration-150",
            compact && "justify-center px-2"
          )}
        >
          <ArrowLeftRight className="h-3.5 w-3.5 shrink-0" />
          {!compact && (
            <span className="text-[11px]">
              {persona === "rep" ? "Power mode" : "Rep mode"}
            </span>
          )}
        </button>
      </TooltipTrigger>
      <TooltipContent side={compact ? "right" : "top"}>
        Switch to {persona === "rep" ? "power" : "rep"} mode
      </TooltipContent>
    </Tooltip>
  );

  // Mobile bottom nav — persona-aware
  const mobileBottomItems = persona === "rep"
    ? [
        { href: "/", label: "Home", icon: Home },
        { href: "/enrich", label: "Enrich", icon: Table2 },
        { href: "/research", label: "Research", icon: Search },
        { href: "/prep", label: "Prep", icon: BookOpen },
        { href: "/outbound", label: "Outbound", icon: Send },
      ]
    : [
        { href: "/", label: "Functions", icon: Blocks },
        { href: "/tables", label: "Tables", icon: Table2 },
        { href: "/chat", label: "Chat", icon: MessageSquare },
        { href: "/outbound", label: "Outbound", icon: Send },
      ];

  return (
    <>
      {/* Desktop sidebar: full width on lg, icon-only on md */}
      <aside className="relative z-10 hidden md:flex shrink-0 border-r border-clay-600 bg-clay-800 p-4 flex-col gap-1 lg:w-56 w-16">
        {/* Logo */}
        <div className="mb-5 px-3 flex items-center gap-3">
          <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-clay-700 border border-clay-500">
            <Image
              src="/brand-assets/the-kiln-logo.png"
              alt="The Kiln"
              width={24}
              height={24}
              className="invert"
            />
          </div>
          <h1 className="hidden lg:block text-lg font-bold text-clay-100 font-[family-name:var(--font-sans)] tracking-tight">
            Webhook OS
          </h1>
        </div>

        {/* Nav - compact on md, full on lg */}
        <div className="hidden lg:block flex-1 overflow-y-auto">{renderSectionNav(false)}</div>
        <div className="lg:hidden flex-1 overflow-y-auto">{renderSectionNav(true)}</div>

        {/* Mode toggle at bottom */}
        <div className="mt-auto pt-3 border-t border-clay-700">
          <div className="hidden lg:block">{renderModeToggle(false)}</div>
          <div className="lg:hidden">{renderModeToggle(true)}</div>
        </div>
      </aside>

      {/* Mobile drawer */}
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-64 bg-clay-800 border-clay-600 p-4">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <SheetDescription className="sr-only">Main navigation menu</SheetDescription>
          <div className="mb-5 px-3 flex items-center gap-3">
            <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-clay-700 border border-clay-500">
              <Image
                src="/brand-assets/the-kiln-logo.png"
                alt="The Kiln"
                width={24}
                height={24}
                className="invert"
              />
            </div>
            <h1 className="text-lg font-bold text-clay-100 font-[family-name:var(--font-sans)] tracking-tight">
              Webhook OS
            </h1>
          </div>
          {renderSectionNav(false, () => setMobileOpen(false))}
          <div className="mt-6 pt-3 border-t border-clay-700">
            {renderModeToggle(false)}
          </div>
        </SheetContent>
      </Sheet>

      {/* Mobile bottom nav — persona-aware 4-item bar */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 z-50 border-t border-clay-600 bg-clay-800/95 backdrop-blur-sm">
        <nav className="flex items-center justify-around py-2">
          {mobileBottomItems.map((item) => {
            const active = item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex flex-col items-center gap-0.5 px-3 py-1 transition-colors duration-150",
                  active ? "text-kiln-teal" : "text-clay-300"
                )}
              >
                <item.icon className="h-5 w-5" />
                <span className="text-[10px]">{item.label}</span>
                {active && <span className="h-1 w-1 rounded-full bg-kiln-teal shadow-[0_0_6px_rgba(74,158,173,0.5)]" />}
              </Link>
            );
          })}
        </nav>
      </div>
    </>
  );
}

// Export all nav sections for use by other components (e.g., keyboard shortcuts help)
export const NAV_SECTIONS = POWER_NAV_SECTIONS;
export const ALL_NAV_ITEMS = NAV_SECTIONS.flatMap((s) => s.items);
export type { NavSection, NavItem };
