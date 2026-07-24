export function formatUsdFromMicros(micros: number): string {
  const usd = micros / 1_000_000;
  return `$${usd.toLocaleString(undefined, {
    minimumFractionDigits: usd < 0.01 ? 4 : 2,
    maximumFractionDigits: usd < 0.01 ? 4 : 2,
  })}`;
}

export function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(2)}M`;
  if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(1)}K`;
  return `${tokens}`;
}
