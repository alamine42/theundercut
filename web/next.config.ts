import type { NextConfig } from "next";

function getValidatedFastapiUrl(): string {
  const raw = process.env.FASTAPI_URL || "http://localhost:8000";

  let parsed: URL;
  try {
    parsed = new URL(raw);
  } catch {
    throw new Error(
      `Invalid FASTAPI_URL: "${raw}" is not a valid URL.`,
    );
  }

  const allowedProtocols = ["http:", "https:"];
  if (!allowedProtocols.includes(parsed.protocol)) {
    throw new Error(
      `Invalid FASTAPI_URL protocol: "${parsed.protocol}". Only http and https are allowed.`,
    );
  }

  // Block well-known internal/metadata endpoints to prevent SSRF
  const blockedHosts = [
    "169.254.169.254", // Cloud metadata (AWS, GCP, Azure)
    "metadata.google.internal",
    "100.100.100.200", // Alibaba Cloud metadata
  ];
  if (blockedHosts.includes(parsed.hostname)) {
    throw new Error(
      `Invalid FASTAPI_URL: "${parsed.hostname}" is a blocked internal host.`,
    );
  }

  // Strip any trailing slash for consistent rewrite behavior
  return parsed.origin + parsed.pathname.replace(/\/+$/, "");
}

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
