import { SearchForm } from "./search-form";

export default function SearchPage() {
  return (
    <main className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-2xl font-bold">Search catalog</h1>
      <p className="mt-2 text-sm text-zinc-600">
        Find cards by name, set, or collector number across supported games.
      </p>
      <div className="mt-8">
        <SearchForm />
      </div>
    </main>
  );
}
