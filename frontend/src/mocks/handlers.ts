import { http, HttpResponse, type RequestHandler } from "msw";

// Global defaults. Individual tests can override these with server.use(...).
// Kept minimal — only defaults that are hit incidentally (not the primary
// data under test) should live here.
export const handlers: RequestHandler[] = [
  http.get("/api/settings/currency", () =>
    HttpResponse.json({ currency: "BDT" }),
  ),
  http.get("/api/bills", () =>
    HttpResponse.json({ bills: [], total: 0, page: 1, page_size: 20 }),
  ),
  http.get("/api/transactions/summary", () =>
    HttpResponse.json({ series: [] }),
  ),
  http.get("/api/transactions/trends", () =>
    HttpResponse.json({
      window_months: 3,
      spark_months: [],
      income: {
        recent_avg: "0.00",
        prior_avg: "0.00",
        change_pct: null,
        direction: "new",
        spark: [],
      },
      spend: {
        recent_avg: "0.00",
        prior_avg: "0.00",
        change_pct: null,
        direction: "new",
        spark: [],
      },
      savings_rate: {
        recent: null,
        prior: null,
        change_pp: null,
        direction: "new",
        spark: [],
      },
    }),
  ),
  http.post("/api/auth/extend", () =>
    HttpResponse.json({ message: "Session extended" }),
  ),
];
