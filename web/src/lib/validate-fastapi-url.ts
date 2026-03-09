/**
 * Validates the FASTAPI_URL environment variable.
 *
 * Ensures the URL is well-formed, uses an allowed protocol (http/https),
 * and does not point to known internal/metadata endpoints (SSRF prevention).
 *
 * @param raw - The raw URL string (defaults to FASTAPI_URL env var or localhost fallback)
 * @returns The validated, normalized URL string (trailing slashes removed)
 * @throws Error if the URL is invalid, uses a disallowed protocol, or targets a blocked host
 */
export function getValidatedFastapiUrl(raw?: string): string {
  const url = raw ?? process.env.FASTAPI_URL ?? "http://localhost:8000";

  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    throw new Error(`Invalid FASTAPI_URL: "${url}" is not a valid URL.`);
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
