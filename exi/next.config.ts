import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Exi lives inside another Next.js repo; pin the root so the parent app's
  // middleware and lockfile aren't picked up.
  turbopack: { root: path.join(__dirname) },
  outputFileTracingRoot: path.join(__dirname),
};

export default nextConfig;
