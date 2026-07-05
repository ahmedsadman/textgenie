import { http, HttpResponse, type RequestHandler } from "msw";

// Global defaults. Individual tests can override these with server.use(...).
// Kept minimal — only defaults that are hit incidentally (not the primary
// data under test) should live here.
export const handlers: RequestHandler[] = [
  http.get("/api/settings/currency", () =>
    HttpResponse.json({ currency: "BDT" }),
  ),
];
