/** Shared formatting helpers for Albion Craft Ranker. */

export function formatPct(value: number): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`;
}

export function formatSilver(value: number): string {
  const abs = Math.abs(value);
  const formatted =
    abs >= 1_000_000
      ? `${(abs / 1_000_000).toFixed(1)}M`
      : abs >= 1_000
        ? `${(abs / 1_000).toFixed(1)}K`
        : abs.toLocaleString("pt-BR", { maximumFractionDigits: 0 });
  return value < 0 ? `-${formatted}` : formatted;
}

export function extractItemName(productId: string): string {
  return productId
    .replace(/^T\d+_/, "")
    .replace(/@\d+$/, "")
    .replace(/_/g, " ");
}

export function extractTier(productId: string): string {
  const match = productId.match(/^T(\d+)/);
  return match ? `T${match[1]}` : "";
}

export function extractEnchantment(productId: string): string {
  const match = productId.match(/@(\d+)$/);
  return match ? `@${match[1]}` : "@0";
}

export function itemIconUrl(productId: string, size = 64): string {
  return `https://render.albiononline.com/v1/item/${encodeURIComponent(productId)}.png?size=${size}&quality=1`;
}
