import { PortfolioClient } from "./portfolio-client";

export default function PortfolioPage() {
  return (
    <main className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-2xl font-bold">Portfolio</h1>
      <p className="mt-2 text-sm text-zinc-600">Track cards you own — dev auth uses X-Dev-User-Id.</p>
      <div className="mt-8">
        <PortfolioClient />
      </div>
    </main>
  );
}
