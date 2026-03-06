import { Card, CardContent } from "@/components/ui/card";
import { Inbox } from "lucide-react";
import { type ReactNode } from "react";

export function EmptyState({
  title,
  description,
  icon: Icon = Inbox,
  children,
}: {
  title: string;
  description: string;
  icon?: React.ComponentType<{ className?: string }>;
  children?: ReactNode;
}) {
  return (
    <Card className="border-clay-800 bg-clay-900/50">
      <CardContent className="flex flex-col items-center justify-center py-12 text-center">
        <div className="mb-4 flex items-center justify-center h-16 w-16 rounded-2xl bg-clay-800/50">
          <Icon className="h-8 w-8 text-clay-500" />
        </div>
        <p className="text-clay-300 font-medium font-[family-name:var(--font-sans)]">
          {title}
        </p>
        <p className="mt-1 text-sm text-clay-500 max-w-sm">{description}</p>
        {children && <div className="mt-4 flex gap-2">{children}</div>}
      </CardContent>
    </Card>
  );
}
