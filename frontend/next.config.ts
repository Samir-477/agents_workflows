import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (apiUrl) {
      return [
        {
          source: "/api/backend/:path*",
          destination: `${apiUrl.replace(/\/$/, "")}/:path*`,
        },
      ];
    }
    return [];
  },
};

export default nextConfig;
