import type { NextConfig } from "next";
import { getValidatedFastapiUrl } from "./src/lib/validate-fastapi-url";

const fastapiUrl = getValidatedFastapiUrl();

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${fastapiUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
