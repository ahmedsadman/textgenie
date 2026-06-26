import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { server } from "@/mocks/server";
import SettingsPage from "@/pages/SettingsPage";
import { renderWithRouter } from "@/test-utils";

const mockWebhook = {
  webhook_url: "http://localhost:8001/api/webhook/test-token-123",
  webhook_token: "test-token-123",
};

function mockSettingsHandlers(
  opts: {
    blacklist?: string[];
    senders?: string[];
  } = {},
) {
  server.use(
    http.get("/api/settings/webhook", () => HttpResponse.json(mockWebhook)),
    http.get("/api/settings/metadata-blacklist", () =>
      HttpResponse.json({ senders: opts.blacklist ?? [] }),
    ),
    http.get("/api/messages/senders", () =>
      HttpResponse.json(opts.senders ?? []),
    ),
  );
}

describe("SettingsPage", () => {
  beforeEach(() => {
    mockSettingsHandlers();
  });

  it("shows page title and sections", async () => {
    renderWithRouter(<SettingsPage />);
    await screen.findByText("Settings");
    expect(screen.getByText("Webhook")).toBeInTheDocument();
    expect(screen.getByText("Metadata blacklist")).toBeInTheDocument();
  });

  it("displays the webhook URL", async () => {
    renderWithRouter(<SettingsPage />);
    await screen.findByDisplayValue(mockWebhook.webhook_url);
  });

  it("copies webhook URL to clipboard", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      writable: true,
      configurable: true,
    });

    renderWithRouter(<SettingsPage />);
    await screen.findByDisplayValue(mockWebhook.webhook_url);

    await user.click(screen.getByLabelText("Copy webhook URL"));
    expect(writeText).toHaveBeenCalledWith(mockWebhook.webhook_url);
  });

  it("regenerates the webhook token and shows the new URL", async () => {
    const newWebhook = {
      webhook_url: "http://localhost:8001/api/webhook/new-token-456",
      webhook_token: "new-token-456",
    };
    server.use(
      http.post("/api/settings/webhook/regenerate", () =>
        HttpResponse.json(newWebhook),
      ),
    );

    const user = userEvent.setup();
    renderWithRouter(<SettingsPage />);

    await screen.findByDisplayValue(mockWebhook.webhook_url);

    await user.click(screen.getByLabelText("Regenerate token"));
    await screen.findByText("Regenerate token", {
      selector: "[data-slot='alert-dialog-title']",
    });
    await user.click(screen.getByRole("button", { name: "Regenerate" }));

    await screen.findByDisplayValue(newWebhook.webhook_url);
  });

  it("loads and displays existing blacklist senders as chips", async () => {
    mockSettingsHandlers({ blacklist: ["brac", "gp"] });
    renderWithRouter(<SettingsPage />);

    await screen.findByText("brac", { selector: "[data-slot='chip'] span" });
    expect(
      screen.getByText("gp", { selector: "[data-slot='chip'] span" }),
    ).toBeInTheDocument();
  });

  it("adds a sender chip and saves the blacklist", async () => {
    let receivedBody: { senders: string[] } | null = null;
    server.use(
      http.put("/api/settings/metadata-blacklist", async ({ request }) => {
        receivedBody = (await request.json()) as { senders: string[] };
        return HttpResponse.json({ senders: ["telco"] });
      }),
    );

    const user = userEvent.setup();
    renderWithRouter(<SettingsPage />);

    const input = await screen.findByLabelText("Blacklisted senders");
    await user.type(input, "telco{Enter}");

    expect(
      screen.getByText("telco", { selector: "[data-slot='chip'] span" }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(receivedBody).toEqual({ senders: ["telco"] });
    });
    await screen.findByText("Blacklist saved");
  });

  it("disables Save until the blacklist changes", async () => {
    mockSettingsHandlers({ blacklist: ["existing"] });
    renderWithRouter(<SettingsPage />);
    await screen.findByText("existing", {
      selector: "[data-slot='chip'] span",
    });

    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
  });

  it("offers recent senders as autocomplete suggestions", async () => {
    mockSettingsHandlers({
      blacklist: [],
      senders: ["BRACBANK", "EBL", "GP"],
    });

    const user = userEvent.setup();
    renderWithRouter(<SettingsPage />);

    const input = await screen.findByLabelText("Blacklisted senders");
    await user.click(input);

    // Suggestions appear immediately on focus
    expect(await screen.findByRole("listbox")).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: "BRACBANK" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "EBL" })).toBeInTheDocument();

    // Typing filters them
    await user.type(input, "br");
    expect(
      screen.queryByRole("option", { name: "EBL" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: "BRACBANK" }),
    ).toBeInTheDocument();
  });

  it("commits a suggestion as a chip when clicked", async () => {
    mockSettingsHandlers({ blacklist: [], senders: ["BRACBANK"] });

    const user = userEvent.setup();
    renderWithRouter(<SettingsPage />);

    const input = await screen.findByLabelText("Blacklisted senders");
    await user.click(input);

    await user.click(screen.getByRole("option", { name: "BRACBANK" }));

    expect(
      screen.getByText("BRACBANK", { selector: "[data-slot='chip'] span" }),
    ).toBeInTheDocument();
  });
});
