import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    // Fewer cache writes on F:\ (slow drive); faster cold starts, slightly slower restarts.
    turbopackFileSystemCacheForDev: false,
    optimizePackageImports: ["lucide-react", "framer-motion"],
  },
};

export default nextConfig;
