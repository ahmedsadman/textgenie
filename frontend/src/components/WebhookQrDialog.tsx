import { QRCodeSVG } from "qrcode.react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { buildWebhookQrPayload } from "@/lib/webhookQr";

interface WebhookQrDialogProps {
  url: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function WebhookQrDialog({
  url,
  open,
  onOpenChange,
}: WebhookQrDialogProps) {
  const payload = url ? buildWebhookQrPayload(url) : "";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Webhook QR code</DialogTitle>
          <DialogDescription>
            Open the TextGenie mobile app, go to Settings, and tap "Scan QR".
          </DialogDescription>
        </DialogHeader>
        <div className="flex justify-center py-2">
          {payload ? (
            <div
              className="rounded-md bg-white p-4"
              data-testid="webhook-qr"
              data-payload={payload}
            >
              <QRCodeSVG value={payload} size={240} level="M" />
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Webhook URL is not available.
            </p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
