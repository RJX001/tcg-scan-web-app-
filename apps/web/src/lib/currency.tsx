"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { getFxRates } from "@tcgscan/sdk-ts";

/** Display currencies we support. All prices are stored USD-normalised. */
export const CURRENCIES = ["USD", "GBP", "EUR", "JPY", "CAD", "AUD", "CHF"] as const;
export type Currency = (typeof CURRENCIES)[number];

const STORAGE_KEY = "tcgscan:currency"; // UI preference only

const EURO_REGIONS = new Set([
  "AT", "BE", "CY", "DE", "EE", "ES", "FI", "FR", "GR", "HR",
  "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PT", "SI", "SK",
]);

function detectCurrency(locale: string): Currency {
  const region = locale.split("-")[1]?.toUpperCase() ?? "";
  if (region === "GB") return "GBP";
  if (region === "JP" || locale.startsWith("ja")) return "JPY";
  if (region === "CA") return "CAD";
  if (region === "AU" || region === "NZ") return "AUD";
  if (region === "CH") return "CHF";
  if (EURO_REGIONS.has(region)) return "EUR";
  return "USD";
}

type CurrencyContextValue = {
  currency: Currency;
  setCurrency: (c: Currency) => void;
  /** Convert a USD amount to the display currency and format per user locale. */
  fmt: (usd: number | null | undefined) => string;
  /** Locale-aware plain number formatting (population counts, sales, …). */
  fmtNum: (n: number | null | undefined) => string;
  /** True once live FX rates are loaded (until then non-USD falls back to USD). */
  ratesLoaded: boolean;
};

const CurrencyContext = createContext<CurrencyContextValue | null>(null);

export function CurrencyProvider({ children }: { children: React.ReactNode }) {
  const [currency, setCurrencyState] = useState<Currency>("USD");
  const [rates, setRates] = useState<Record<string, number>>({ USD: 1 });

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored && (CURRENCIES as readonly string[]).includes(stored)) {
      setCurrencyState(stored as Currency);
    } else {
      setCurrencyState(detectCurrency(navigator.language));
    }
    getFxRates()
      .then((fx) => setRates({ USD: 1, ...fx.rates }))
      .catch(() => {
        // keep USD-only — better than guessing rates
      });
  }, []);

  const setCurrency = useCallback((c: Currency) => {
    setCurrencyState(c);
    window.localStorage.setItem(STORAGE_KEY, c);
  }, []);

  const value = useMemo<CurrencyContextValue>(() => {
    const rate = rates[currency];
    const effective: Currency = rate ? currency : "USD";
    const fmt = (usd: number | null | undefined) => {
      if (usd == null) return "—";
      const amount = effective === "USD" ? usd : usd / rates[effective];
      return new Intl.NumberFormat(undefined, {
        style: "currency",
        currency: effective,
        maximumFractionDigits: Math.abs(amount) >= 1000 ? 0 : 2,
      }).format(amount);
    };
    const fmtNum = (n: number | null | undefined) =>
      n == null ? "—" : new Intl.NumberFormat(undefined).format(n);
    return {
      currency: effective,
      setCurrency,
      fmt,
      fmtNum,
      ratesLoaded: Object.keys(rates).length > 1,
    };
  }, [currency, rates, setCurrency]);

  return <CurrencyContext.Provider value={value}>{children}</CurrencyContext.Provider>;
}

export function useCurrency(): CurrencyContextValue {
  const ctx = useContext(CurrencyContext);
  if (!ctx) throw new Error("useCurrency must be used inside <CurrencyProvider>");
  return ctx;
}

/** Render a USD amount in the user's display currency (safe in Server Components). */
export function Money({ usd }: { usd: number | null | undefined }) {
  const { fmt } = useCurrency();
  return <>{fmt(usd)}</>;
}

/** Locale-aware plain number (safe in Server Components). */
export function Num({ n }: { n: number | null | undefined }) {
  const { fmtNum } = useCurrency();
  return <>{fmtNum(n)}</>;
}

export function CurrencySelect({ className }: { className?: string }) {
  const { currency, setCurrency } = useCurrency();
  return (
    <select
      value={currency}
      onChange={(e) => setCurrency(e.target.value as Currency)}
      aria-label="Display currency"
      className={
        className ??
        "rounded-lg border border-zinc-300 bg-white px-2 py-1 text-xs font-medium text-zinc-600"
      }
    >
      {CURRENCIES.map((c) => (
        <option key={c} value={c}>
          {c}
        </option>
      ))}
    </select>
  );
}
