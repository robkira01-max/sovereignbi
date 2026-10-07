import { test, expect } from "@playwright/test";

const VIEWER_KEY = process.env.SOVEREIGN_VIEWER_KEY || "test-viewer";
const EDITOR_KEY = process.env.SOVEREIGN_EDITOR_KEY || "test-editor";

test.describe("Upload + Ask flow", () => {
  test("Upload CSV then GET /health shows table", async ({ request }) => {
    const csv = "product,sales\nWidgets,1000\nGadgets,2000\n";
    const upload = await request.post("/api/v1/upload", {
      headers: { "X-Api-Key": EDITOR_KEY },
      multipart: {
        file: {
          name: "sales.csv",
          mimeType: "text/csv",
          buffer: Buffer.from(csv),
        },
      },
    });
    expect(upload.status()).toBe(200);
    const { tables } = await upload.json();
    expect(tables).toContain("sales");

    const health = await request.get("/api/v1/health");
    const body = await health.json();
    expect(body.tables).toContain("sales");
  });

  test("POST /ask without data returns 400", async ({ request }) => {
    const r = await request.post("/ask", {
      headers: { "X-Api-Key": VIEWER_KEY },
      data: { question: "How many rows?" },
    });
    expect(r.status()).toBe(400);
  });

  test("POST /ask without key returns 401", async ({ request }) => {
    const r = await request.post("/ask", {
      data: { question: "How many rows?" },
    });
    expect(r.status()).toBe(401);
  });
});
