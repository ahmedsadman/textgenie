export const WEBHOOK_QR_TYPE = "textgenie-webhook";

export interface WebhookQrPayload {
  type: typeof WEBHOOK_QR_TYPE;
  url: string;
}

export function buildWebhookQrPayload(url: string): string {
  const payload: WebhookQrPayload = { type: WEBHOOK_QR_TYPE, url };
  return JSON.stringify(payload);
}
