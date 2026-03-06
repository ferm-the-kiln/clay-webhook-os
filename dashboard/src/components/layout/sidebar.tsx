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
import { LayoutDashboard, FlaskConical, Layers, BookOpen, GitBranch, TestTubes, BarChart3, Settings, Rocket, ClipboardCheck } from "lucide-react";

const NAV = [
  {
    href: "/",
    label: "Dashboard",
    icon: LayoutDashboard,
    asset: "/brand-assets/v2-dashboard.png",
    shortcut: "1",
  },
  {
    href: "/playground",
    label: "Playground",
    icon: FlaskConical,
    asset: "/brand-assets/v2-playground.png",
    shortcut: "2",
  },
  {
    href: "/batch",
    label: "Batch",
    icon: Layers,
    asset: "/brand-assets/v2-batch.png",
    shortcut: "3",
  },
  {
    href: "/context",
    label: "Context",
    icon: BookOpen,
    asset: "",
    shortcut: "4",
  },
  {
    href: "/pipelines",
    label: "Pipelines",
    icon: GitBranch,
    asset: "",
    shortcut: "5",
  },
  {
    href: "/lab",
    label: "Skills Lab",
    icon: TestTubes,
    asset: "",
    shortcut: "6",
  },
  {
    href: "/campaigns",
    label: "Campaigns",
    icon: Rocket,
    asset: "",
    shortcut: "7",
  },
  {
    href: "/review",
    label: "Review",
    icon: ClipboardCheck,
    asset: "",
    shortcut: "8",
  },
  {
    href: "/analytics",
    label: "Analytics",
    icon: BarChart3,
    asset: "",
    shortcut: "9",
  },
  {
    href: "/settings",
    label: "Settings",
    icon: Settings,
    asset: "",
    shortcut: "0",
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
      if ((e.metaKey || e.ctrlKey) && ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"].includes(e.key)) {
        e.preventDefault();
        const idx = e.key === "0" ? 9 : parseInt(e.key) - 1;
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
        return (
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
              {item.asset ? (
                <Image
                  src={item.asset}
                  alt={item.label}
                  width={24}
                  height={24}
                  className="shrink-0 rounded-sm"
                />
              ) : (
                <item.icon className="h-6 w-6 shrink-0" />
              )}
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
      })}
    </nav>
  );

  return (
    <>
      {/* Desktop sidebar: full width on lg, icon-only on md */}
      <aside className="relative z-10 hidden md:flex shrink-0 border-r border-clay-800 bg-[#151413] p-4 flex-col gap-1 lg:w-56 w-16">
        {/* Logo */}
        <div className="mb-6 px-3 flex items-center gap-3">
          <Image
            src="/brand-assets/v2-the-kiln-logo.png"
            alt="Kiln"
            width={32}
            height={32}
            className="motion-safe:animate-float-slow"
          />
          <div className="hidden lg:block">
            <h1 className="text-lg font-bold text-kiln-cream font-[family-name:var(--font-sans)]">
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

        {/* Decorative star */}
        <div className="mt-auto flex justify-center pb-2 opacity-30">
          <Image
            src="/brand-assets/decor-star.png"
            alt=""
            width={24}
            height={24}
            className="motion-safe:animate-float"
          />
        </div>
      </aside>

      {/* Mobile drawer */}
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-64 bg-[#151413] border-clay-800 p-4">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <SheetDescription className="sr-only">Main navigation menu</SheetDescription>
          <div className="mb-6 px-3 flex items-center gap-3">
            <Image
              src="/brand-assets/v2-the-kiln-logo.png"
              alt="Kiln"
              width={32}
              height={32}
            />
            <div>
              <h1 className="text-lg font-bold text-kiln-cream font-[family-name:var(--font-sans)]">
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

      {/* Mobile bottom nav - fixed at bottom on small screens */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 z-50 border-t border-clay-800 bg-[#151413]/95 backdrop-blur-sm">
        <nav className="flex items-center justify-around py-2">
          {NAV.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex flex-col items-center gap-0.5 px-3 py-1 text-xs transition-colors",
                  active ? "text-kiln-teal" : "text-clay-500"
                )}
              >
                <item.icon className="h-5 w-5" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </>
  );
}

export { NAV };
