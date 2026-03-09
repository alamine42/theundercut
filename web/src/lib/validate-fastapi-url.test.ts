/**
 * Tests for getValidatedFastapiUrl (UND-53).
 *
 * Covers: valid URLs, invalid URLs, blocked protocols, SSRF protection,
 * trailing slash removal, and default fallback behavior.
 */
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { getValidatedFastapiUrl } from "./validate-fastapi-url";

describe("getValidatedFastapiUrl", () => {
  const originalEnv = process.env.FASTAPI_URL;

  beforeEach(() => {
    delete process.env.FASTAPI_URL;
  });

  afterEach(() => {
    if (originalEnv !== undefined) {
      process.env.FASTAPI_URL = originalEnv;
    } else {
      delete process.env.FASTAPI_URL;
    }
  });

  // ── Valid URLs ────────────────────────────────────────────────────
  describe("valid URLs", () => {
    it("should accept a valid http URL", () => {
      expect(getValidatedFastapiUrl("http://example.com")).toBe(
        "http://example.com",
      );
    });

    it("should accept a valid https URL", () => {
      expect(getValidatedFastapiUrl("https://api.example.com")).toBe(
        "https://api.example.com",
      );
    });

    it("should accept a URL with a port", () => {
      expect(getValidatedFastapiUrl("http://localhost:8000")).toBe(
        "http://localhost:8000",
      );
    });

    it("should accept a URL with a path", () => {
      expect(getValidatedFastapiUrl("https://example.com/api")).toBe(
        "https://example.com/api",
      );
    });

    it("should accept a URL with a subdomain", () => {
      expect(
        getValidatedFastapiUrl("https://staging.api.example.com"),
      ).toBe("https://staging.api.example.com");
    });
  });

  // ── Invalid URLs ──────────────────────────────────────────────────
  describe("invalid URLs", () => {
    it("should reject a malformed URL", () => {
      expect(() => getValidatedFastapiUrl("not-a-url")).toThrow(
        'Invalid FASTAPI_URL: "not-a-url" is not a valid URL.',
      );
    });

    it("should reject an empty string", () => {
      expect(() => getValidatedFastapiUrl("")).toThrow(
        "is not a valid URL",
      );
    });

    it("should reject a URL with spaces", () => {
      expect(() => getValidatedFastapiUrl("http://example .com")).toThrow(
        "is not a valid URL",
      );
    });
  });

  // ── Blocked protocols ─────────────────────────────────────────────
  describe("blocked protocols", () => {
    it("should reject ftp protocol", () => {
      expect(() => getValidatedFastapiUrl("ftp://example.com")).toThrow(
        'Invalid FASTAPI_URL protocol: "ftp:"',
      );
    });

    it("should reject file protocol", () => {
      expect(() => getValidatedFastapiUrl("file:///etc/passwd")).toThrow(
        'Invalid FASTAPI_URL protocol: "file:"',
      );
    });

    it("should reject javascript protocol", () => {
      expect(() =>
        getValidatedFastapiUrl("javascript:alert(1)"),
      ).toThrow('Invalid FASTAPI_URL protocol: "javascript:"');
    });

    it("should reject data protocol", () => {
      expect(() =>
        getValidatedFastapiUrl("data:text/html,<h1>hi</h1>"),
      ).toThrow('Invalid FASTAPI_URL protocol: "data:"');
    });
  });

  // ── SSRF protection ───────────────────────────────────────────────
  describe("SSRF protection", () => {
    it("should block AWS/GCP/Azure metadata endpoint", () => {
      expect(() =>
        getValidatedFastapiUrl("http://169.254.169.254"),
      ).toThrow(
        'Invalid FASTAPI_URL: "169.254.169.254" is a blocked internal host.',
      );
    });

    it("should block AWS metadata with path", () => {
      expect(() =>
        getValidatedFastapiUrl(
          "http://169.254.169.254/latest/meta-data/",
        ),
      ).toThrow("is a blocked internal host");
    });

    it("should block Google Cloud internal metadata", () => {
      expect(() =>
        getValidatedFastapiUrl("http://metadata.google.internal"),
      ).toThrow(
        'Invalid FASTAPI_URL: "metadata.google.internal" is a blocked internal host.',
      );
    });

    it("should block Alibaba Cloud metadata endpoint", () => {
      expect(() =>
        getValidatedFastapiUrl("http://100.100.100.200"),
      ).toThrow(
        'Invalid FASTAPI_URL: "100.100.100.200" is a blocked internal host.',
      );
    });

    it("should block SSRF via https as well", () => {
      expect(() =>
        getValidatedFastapiUrl("https://169.254.169.254"),
      ).toThrow("is a blocked internal host");
    });
  });

  // ── Trailing slash removal ────────────────────────────────────────
  describe("trailing slash removal", () => {
    it("should strip a single trailing slash", () => {
      expect(getValidatedFastapiUrl("http://example.com/")).toBe(
        "http://example.com",
      );
    });

    it("should strip multiple trailing slashes", () => {
      expect(getValidatedFastapiUrl("http://example.com///")).toBe(
        "http://example.com",
      );
    });

    it("should strip trailing slash from a path", () => {
      expect(getValidatedFastapiUrl("http://example.com/api/v1/")).toBe(
        "http://example.com/api/v1",
      );
    });

    it("should not modify a URL without trailing slash", () => {
      expect(getValidatedFastapiUrl("http://example.com/api")).toBe(
        "http://example.com/api",
      );
    });
  });

  // ── Default fallback ──────────────────────────────────────────────
  describe("default fallback", () => {
    it("should fall back to localhost:8000 when no argument and no env var", () => {
      delete process.env.FASTAPI_URL;
      expect(getValidatedFastapiUrl()).toBe("http://localhost:8000");
    });

    it("should use FASTAPI_URL env var when no argument is provided", () => {
      process.env.FASTAPI_URL = "https://my-api.example.com";
      expect(getValidatedFastapiUrl()).toBe("https://my-api.example.com");
    });

    it("should prefer explicit argument over env var", () => {
      process.env.FASTAPI_URL = "https://env-api.example.com";
      expect(getValidatedFastapiUrl("https://arg-api.example.com")).toBe(
        "https://arg-api.example.com",
      );
    });
  });
});
