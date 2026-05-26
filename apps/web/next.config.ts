import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@tcgscan/ui", "@tcgscan/sdk-ts"],
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "images.pokemontcg.io", pathname: "/**" },
      { protocol: "https", hostname: "cards.scryfall.io", pathname: "/**" },
    ],
  },
};

export default nextConfig;
