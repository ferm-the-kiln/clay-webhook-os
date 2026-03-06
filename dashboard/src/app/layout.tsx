import type { Metadata } from "next";
import { Sidebar } from "@/components/layout/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";

export const metadata: Metadata = {
  title: "Clay OS — Webhook Dashboard",
  description: "Kiln-branded dashboard for Clay Webhook OS",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&family=Inter:wght@400;500;600&family=Fragment+Mono:wght@400&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="flex h-screen overflow-hidden bg-[url('/brand-assets/bg-clay-texture.png')] bg-repeat bg-[length:400px]">
        <div className="absolute inset-0 bg-clay-950/95 pointer-events-none" />
        <TooltipProvider>
          <Sidebar />
          <main className="relative flex-1 overflow-auto">{children}</main>
        </TooltipProvider>
      </body>
    </html>
  );
}
