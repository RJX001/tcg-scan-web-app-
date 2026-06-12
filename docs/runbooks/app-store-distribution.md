# App store distribution

TCG Scan ships as a **PWA-first** product: one Next.js codebase (`apps/web`) serves the
website, the installable mobile app, and the app-store builds. This is how Card Ladder
parity on mobile is achieved without forking the frontend.

## What is already in place (this repo)

- Web app manifest: `apps/web/src/app/manifest.ts` (id, icons, shortcuts, standalone display)
- App icon: `apps/web/public/icons/icon.svg` (full-bleed, maskable-safe)
- Service worker: `apps/web/public/sw.js` — offline shell, cache-first static assets,
  **never caches `/v1/` API responses** (prices must be live). Registered in production
  only via `src/components/pwa-register.tsx`.
- Install metadata: `appleWebApp` + `viewport`/`themeColor` in `src/app/layout.tsx`
- Camera capture already uses `getUserMedia` with `<input capture="environment">` fallback,
  which works in installed PWAs on both platforms.

Result: users can **Add to Home Screen** today on iOS Safari and Android Chrome and get a
standalone, full-screen app.

## Google Play Store (Android) — TWA, no code changes

Package the deployed site as a Trusted Web Activity with [Bubblewrap](https://github.com/GoogleChromeLabs/bubblewrap):

```bash
npm i -g @bubblewrap/cli
bubblewrap init --manifest https://<prod-domain>/manifest.webmanifest
bubblewrap build   # produces an .aab for the Play Console
```

Requirements:

1. Production HTTPS deploy of `apps/web`.
2. Digital Asset Links: host `/.well-known/assetlinks.json` with the signing-key
   fingerprint Bubblewrap prints (add it under `apps/web/public/.well-known/`).
3. A 512×512 PNG icon for the Play listing — export from `icons/icon.svg`
   (`npx svgexport icon.svg icon-512.png 512:512`).

The TWA renders the live site in Chrome with no browser UI. Web deploys update the app
instantly; only manifest/icon changes need a store re-submission.

## Apple App Store (iOS)

Two options, in order of preference:

1. **Installed PWA (no store)** — already works via Safari "Add to Home Screen".
   Push notifications for installed PWAs are supported since iOS 16.4.
2. **Store listing via Capacitor wrapper** — Apple does not accept bare site wrappers,
   so a store build should add native value (camera capture via native APIs, push,
   widgets). This adds a new build target + dependency to the stack and therefore
   **requires an ADR in `docs/adr/`** before starting (per root AGENTS.md). Sketch:
   a thin `apps/mobile` Capacitor shell pointing at the deployed web app, with the
   scan flow upgraded to `@capacitor/camera`.

## Hard rules for store builds

- The app talks **only** to `apps/api` (`/v1`) — same as the website. No marketplace
  calls from the client.
- `localStorage` stays UI-preferences-only; auth tokens come from Clerk's SDK.
- Secrets never ship in the bundle; the web app holds no secrets today — keep it that way.
