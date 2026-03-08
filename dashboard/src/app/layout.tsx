import type { Metadata } from "next";
import { Sidebar } from "@/components/layout/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/sonner";
import { KeyboardShortcutsDialog } from "@/components/keyboard-shortcuts-dialog";
import "./globals.css";

export const metadata: Metadata = {
  title: "Clay OS — Webhook Dashboard",
  description: "Dashboard for Clay Webhook OS",
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
          href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&family=Inter:wght@400;500;600&family=Fragment+Mono:wght@400&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="flex h-screen overflow-hidden bg-background">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:top-2 focus:left-2 focus:rounded-md focus:bg-kiln-teal focus:px-4 focus:py-2 focus:text-white focus:font-medium"
        >
          Skip to main content
        </a>
        <TooltipProvider>
          <Sidebar />
          <main id="main-content" className="relative flex-1 overflow-auto">{children}</main>
          <KeyboardShortcutsDialog />
        </TooltipProvider>
        <Toaster
          position="bottom-right"
          toastOptions={{
            classNames: {
              success: "!bg-kiln-teal/10 !border-kiln-teal/20 !text-kiln-teal",
              error: "!bg-kiln-coral/10 !border-kiln-coral/20 !text-kiln-coral",
              info: "!bg-kiln-mustard/10 !border-kiln-mustard/20 !text-kiln-mustard",
            },
          }}
        />
      </body>
    </html>
  );
}
