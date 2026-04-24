import type { NextConfig } from "next";
import { loadEnvConfig } from "@next/env";
import path from "node:path";

loadEnvConfig(path.resolve(process.cwd(), "../.."), true, console, true);

const nextConfig: NextConfig = {
  eslint: {
    ignoreDuringBuilds: true
  }
};

export default nextConfig;
