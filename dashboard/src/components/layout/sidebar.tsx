"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { LayoutDashboard, FlaskConical, Layers } from "lucide-react";

const NAV = [
  {
    href: "/",
    label: "Dashboard",
    icon: LayoutDashboard,
    asset: "/brand-assets/v2-dashboard.png",
  },
  {
    href: "/playground",
    label: "Playground",
    icon: FlaskConical,
    asset: "/brand-assets/v2-playground.png",
  },
  {
    href: "/batch",
    label: "Batch",
    icon: Layers,
    asset: "/brand-assets/v2-batch.png",
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="relative z-10 w-56 shrink-0 border-r border-clay-800 bg-[#151413] p-4 flex flex-col gap-1">
      {/* Logo */}
      <div className="mb-6 px-3 flex items-center gap-3">
        <Image
          src="/brand-assets/v2-the-kiln-logo.png"
          alt="Kiln"
          width={32}
          height={32}
          className="animate-float-slow"
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

      {/* Nav */}
      <nav className="flex flex-col gap-1">
        {NAV.map((item) => {
          const active = pathname === item.href;
          return (
            <Button
              key={item.href}
              variant="ghost"
              asChild
              className={cn(
                "justify-start gap-3 h-10 px-3 transition-all duration-200",
                active
                  ? "bg-kiln-teal/10 text-kiln-teal hover:bg-kiln-teal/15 hover:text-kiln-teal"
                  : "text-clay-400 hover:bg-clay-800 hover:text-clay-200"
              )}
            >
              <Link href={item.href}>
                <Image
                  src={item.asset}
                  alt={item.label}
                  width={24}
                  height={24}
                  className="shrink-0 rounded-sm"
                />
                {item.label}
              </Link>
            </Button>
          );
        })}
      </nav>

      {/* Decorative star */}
      <div className="mt-auto flex justify-center pb-2 opacity-30">
        <Image
          src="/brand-assets/decor-star.png"
          alt=""
          width={24}
          height={24}
          className="animate-float"
        />
      </div>
    </aside>
  );
}
