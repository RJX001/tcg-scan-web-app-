"use client";

import { useEffect, useState } from "react";
import { fmtSoldAtLocal } from "@/lib/format";

type Props = {
  iso: string;
  className?: string;
};

/** Renders sold_at on the client so locale + timezone match the user's region. */
export function SoldAtCell({ iso, className }: Props) {
  const [text, setText] = useState("");

  useEffect(() => {
    setText(fmtSoldAtLocal(iso));
  }, [iso]);

  return (
    <td className={className} suppressHydrationWarning>
      {text || "\u00a0"}
    </td>
  );
}
