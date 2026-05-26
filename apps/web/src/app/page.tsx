import { Button, Card, CardContent, CardHeader, CardTitle } from "@tcgscan/ui";
import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col items-center justify-center gap-8 px-4 py-16">
      <div className="text-center">
        <p className="text-sm font-medium uppercase tracking-wider text-zinc-500">TCG Scan</p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight sm:text-5xl">
          Scan once. Know the market.
        </h1>
        <p className="mt-4 text-lg text-zinc-600">
          Price guide for every modern TCG and sports card — sold comps, active listings,{" "}
          <strong className="font-semibold text-zinc-800">condition estimates</strong>, and grading
          ROI verdicts.
        </p>
      </div>
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Try a scan</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <p className="text-sm text-zinc-600">
            Scan a card, see cross-marketplace comps, condition estimates, and grading ROI — across
            Pokemon, sports, and every major TCG.
          </p>
          <Button asChild>
            <Link href="/scan">Open scanner</Link>
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}
