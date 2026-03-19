import type { Metadata } from "next";
import { Sidebar } from "@/components/layout/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/sonner";
import { KeyboardShortcutsDialog } from "@/components/keyboard-shortcuts-dialog";
import "./globals.css";

export const metadata: Metadata = {
  title: "Webhook OS — Dashboard",
  description: "Dashboard for Webhook OS",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Fragment+Mono:wght@400&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="flex h-screen overflow-hidden bg-background retro-grain retro-scanlines">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:top-2 focus:left-2 focus:rounded-md focus:bg-kiln-teal focus:px-4 focus:py-2 focus:text-clay-950 focus:font-medium"
        >
          Skip to main content
        </a>
        <TooltipProvider>
          <Sidebar />
          <main id="main-content" className="relative flex-1 overflow-auto z-[2]">{children}</main>
          <KeyboardShortcutsDialog />
        </TooltipProvider>
        <Toaster
          position="top-right"
          toastOptions={{
            classNames: {
              success: "!bg-status-success/10 !border-status-success/25 !text-status-success",
              error: "!bg-kiln-coral/10 !border-kiln-coral/25 !text-kiln-coral",
              info: "!bg-kiln-mustard/10 !border-kiln-mustard/25 !text-kiln-mustard",
            },
          }}
        />
      </body>
    </html>
  );
}
