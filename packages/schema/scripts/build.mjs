import { writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const outDir = join(root, "src", "generated");
mkdirSync(outDir, { recursive: true });

// Minimal generator: emit Zod stubs from schema titles (full codegen in a later PR).
const stubs = `import { z } from "zod";

export const HealthResponseSchema = z.object({
  status: z.enum(["ok", "degraded"]),
  version: z.string().optional(),
});
export type HealthResponse = z.infer<typeof HealthResponseSchema>;

export const CardIdentitySchema = z.object({
  id: z.string().uuid(),
  game: z.enum([
    "pokemon",
    "mtg",
    "yugioh",
    "one_piece",
    "lorcana",
    "sports_baseball",
    "sports_basketball",
    "sports_football",
    "other",
  ]),
  name: z.string(),
  set_code: z.string().optional(),
  set_name: z.string().optional(),
  number: z.string().optional(),
  rarity: z.string().optional(),
  variants: z.record(z.unknown()).optional(),
  attributes: z.record(z.unknown()).optional(),
  image_urls: z.record(z.unknown()).optional(),
  external_ids: z.record(z.unknown()).optional(),
});
export type CardIdentity = z.infer<typeof CardIdentitySchema>;
`;

writeFileSync(join(outDir, "index.ts"), stubs);
console.log("schema:build — wrote packages/schema/src/generated/index.ts");
