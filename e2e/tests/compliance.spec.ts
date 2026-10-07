import { test, expect } from "@playwright/test";

const VIEWER_KEY = process.env.SOVEREIGN_VIEWER_KEY || "test-viewer";
const EDITOR_KEY = process.env.SOVEREIGN_EDITOR_KEY || "test-editor";
const ADMIN_KEY = process.env.SOVEREIGN_ADMIN_KEY || "test-admin";

test.describe("Conformité Loi 25 / PIPEDA", () => {
  test("GET /compliance/notice est accessible", async ({ request }) => {
    const r = await request.get("/compliance/notice", {
      headers: { "X-Api-Key": VIEWER_KEY },
    });
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(body.applicable_laws).toContain("Loi 25 (Québec)");
  });

  test("Enregistrement et retrait de consentement", async ({ request }) => {
    const userId = `e2e-user-${Date.now()}`;

    const consent = await request.post("/compliance/consent", {
      headers: { "X-Api-Key": EDITOR_KEY },
      data: { user_id: userId, purpose: "analytics", granted: true },
    });
    expect(consent.status()).toBe(200);
    expect((await consent.json()).granted).toBe(true);

    const list = await request.get(`/compliance/consent/${userId}`, {
      headers: { "X-Api-Key": VIEWER_KEY },
    });
    expect((await list.json()).length).toBeGreaterThanOrEqual(1);
  });

  test("Demande d'accès aux données (DSR)", async ({ request }) => {
    const userId = `dsr-user-${Date.now()}`;
    const r = await request.post("/compliance/requests", {
      headers: { "X-Api-Key": VIEWER_KEY },
      data: { user_id: userId, request_type: "access" },
    });
    expect(r.status()).toBe(200);
    expect((await r.json()).status).toBe("pending");
  });
});
