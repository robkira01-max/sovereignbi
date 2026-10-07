import { test, expect } from "@playwright/test";

test.describe("API Health", () => {
  test("GET /health returns status ok", async ({ request }) => {
    const r = await request.get("/health");
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(body.status).toBe("ok");
  });

  test("GET /api/v1/health includes api_version", async ({ request }) => {
    const r = await request.get("/api/v1/health");
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(body.api_version).toBe("v1");
  });

  test("Response includes X-API-Version header", async ({ request }) => {
    const r = await request.get("/health");
    expect(r.headers()["x-api-version"]).toBe("v1");
  });
});
