import { describe, it, expect } from "vitest";
import {
  formatPct,
  formatSilver,
  extractItemName,
  extractTier,
  extractEnchantment,
} from "@/lib/format";

describe("formatPct", () => {
  it("formats positive percentage with + prefix", () => {
    expect(formatPct(15.23)).toBe("+15.2%");
  });

  it("formats negative percentage", () => {
    expect(formatPct(-3.78)).toBe("-3.8%");
  });

  it("formats zero as +0.0%", () => {
    expect(formatPct(0)).toBe("+0.0%");
  });
});

describe("formatSilver", () => {
  it("formats millions with M suffix", () => {
    expect(formatSilver(2_500_000)).toBe("2.5M");
  });

  it("formats thousands with K suffix", () => {
    expect(formatSilver(12_300)).toBe("12.3K");
  });

  it("formats small values without suffix", () => {
    expect(formatSilver(850)).toBe("850");
  });

  it("formats negative values", () => {
    expect(formatSilver(-45_000)).toBe("-45.0K");
  });

  it("formats zero", () => {
    expect(formatSilver(0)).toBe("0");
  });
});

describe("extractItemName", () => {
  it("strips tier prefix and underscores", () => {
    expect(extractItemName("T4_SHOES_CLOTH")).toBe("SHOES CLOTH");
  });

  it("strips enchantment suffix", () => {
    expect(extractItemName("T6_2H_ARCANESTAFF@2")).toBe("2H ARCANESTAFF");
  });
});

describe("extractTier", () => {
  it("extracts tier number", () => {
    expect(extractTier("T4_SHOES_CLOTH")).toBe("T4");
  });

  it("extracts higher tier", () => {
    expect(extractTier("T8_HEAD_PLATE@3")).toBe("T8");
  });

  it("returns empty for invalid", () => {
    expect(extractTier("INVALID")).toBe("");
  });
});

describe("extractEnchantment", () => {
  it("extracts enchantment suffix", () => {
    expect(extractEnchantment("T6_2H_ARCANESTAFF@2")).toBe("@2");
  });

  it("returns @0 when no enchantment", () => {
    expect(extractEnchantment("T4_SHOES_CLOTH")).toBe("@0");
  });
});
