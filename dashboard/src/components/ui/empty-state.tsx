import Image from "next/image";
import { Card, CardContent } from "@/components/ui/card";

export function EmptyState({
  title,
  description,
  asset = "/brand-assets/hero-empty-bowl.png",
}: {
  title: string;
  description: string;
  asset?: string;
}) {
  return (
    <Card className="border-clay-800 bg-clay-900/50">
      <CardContent className="flex flex-col items-center justify-center py-12 text-center">
        <Image
          src={asset}
          alt=""
          width={120}
          height={120}
          className="mb-4 animate-float opacity-80 rounded-lg"
        />
        <p className="text-clay-300 font-medium font-[family-name:var(--font-sans)]">
          {title}
        </p>
        <p className="mt-1 text-sm text-clay-500 max-w-sm">{description}</p>
      </CardContent>
    </Card>
  );
}
