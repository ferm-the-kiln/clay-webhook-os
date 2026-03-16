"use client";

import { DatasetProvider } from "@/contexts/dataset-context";

export default function PipelineLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <DatasetProvider>{children}</DatasetProvider>;
}
