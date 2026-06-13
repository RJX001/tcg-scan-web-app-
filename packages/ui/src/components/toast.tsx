import * as React from "react";
import { cn } from "../lib/utils";

export type ToastProps = {
  title: string;
  description?: string;
  variant?: "default" | "destructive";
};

export function Toast({ title, description, variant = "default" }: ToastProps) {
  return (
    <div
      role="status"
      className={cn(
        "pointer-events-auto w-full max-w-sm rounded-lg border p-4 shadow-lg",
        variant === "destructive" ? "border-red-200 bg-red-50" : "border-zinc-200 bg-white",
      )}
    >
      <p className="text-sm font-semibold">{title}</p>
      {description ? <p className="mt-1 text-sm text-zinc-600">{description}</p> : null}
    </div>
  );
}
