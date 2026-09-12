import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    if (process.env.NODE_ENV === "production") return [];
    const localApiOrigin = process.env.LOCAL_API_ORIGIN || "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${localApiOrigin}/api/:path*` }];
  },
};

export default nextConfig;
