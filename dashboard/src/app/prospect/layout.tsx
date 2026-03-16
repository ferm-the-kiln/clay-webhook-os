"use client";

import { DatasetProvider } from "@/contexts/dataset-context";

export default function ProspectLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <DatasetProvider>{children}</DatasetProvider>;
}
