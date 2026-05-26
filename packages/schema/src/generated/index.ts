import { z } from "zod";

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
