import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

import WebhookQrDialog from "@/components/WebhookQrDialog";
import { buildWebhookQrPayload } from "@/lib/webhookQr";

function Harness({ url, initialOpen }: { url: string; initialOpen: boolean }) {
  const [open, setOpen] = useState(initialOpen);
  return (
    <>
      <button onClick={() => setOpen(true)}>open</button>
      <WebhookQrDialog url={url} open={open} onOpenChange={setOpen} />
    </>
  );
}

describe("WebhookQrDialog", () => {
  it("renders the QR code with the JSON envelope payload when open", async () => {
    const url = "https://api.example.com/api/webhook/token-abc";
    render(<Harness url={url} initialOpen={true} />);

    const qr = await screen.findByTestId("webhook-qr");
    expect(qr).toBeInTheDocument();
    expect(qr.getAttribute("data-payload")).toBe(buildWebhookQrPayload(url));
    expect(qr.querySelector("svg")).not.toBeNull();
    expect(screen.getByText(/Scan QR/i)).toBeInTheDocument();
  });

  it("shows a fallback when the webhook URL is empty", async () => {
    render(<Harness url="" initialOpen={true} />);
    expect(
      await screen.findByText(/Webhook URL is not available/i),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("webhook-qr")).not.toBeInTheDocument();
  });

  it("does not render QR content when closed", () => {
    render(<Harness url="https://api.example.com/x" initialOpen={false} />);
    expect(screen.queryByTestId("webhook-qr")).not.toBeInTheDocument();
  });

  it("closes when the user presses Escape", async () => {
    const user = userEvent.setup();
    render(<Harness url="https://api.example.com/x" initialOpen={true} />);

    expect(await screen.findByTestId("webhook-qr")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    await screen.findByRole("button", { name: "open" });
    expect(screen.queryByTestId("webhook-qr")).not.toBeInTheDocument();
  });
});
