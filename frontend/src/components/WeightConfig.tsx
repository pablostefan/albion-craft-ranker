"use client";

import { useCallback } from "react";

interface Weights {
  profit_weight: number;
  focus_weight: number;
  volume_weight: number;
  freshness_weight: number;
}

type WeightKey = keyof Weights;

const WEIGHT_LABELS: { key: WeightKey; label: string }[] = [
  { key: "profit_weight", label: "Lucro" },
  { key: "focus_weight", label: "Foco" },
  { key: "volume_weight", label: "Vol. Diário" },
  { key: "freshness_weight", label: "Atualização" },
];

interface WeightConfigProps {
  weights: Weights;
  onChange: (weights: Weights) => void;
  defaults: Weights | null;
  onReset: () => void;
}

function normalize(weights: Weights, changedKey: WeightKey): Weights {
  const changedVal = weights[changedKey];
  const remaining = 1.0 - changedVal;
  const otherKeys = WEIGHT_LABELS.map((w) => w.key).filter(
    (k) => k !== changedKey,
  );

  const otherSum = otherKeys.reduce((sum, k) => sum + weights[k], 0);

  const result = { ...weights };

  if (otherSum === 0) {
    const share = Math.round((remaining / otherKeys.length) * 100) / 100;
    for (const k of otherKeys) {
      result[k] = share;
    }
  } else {
    const ratio = remaining / otherSum;
    for (const k of otherKeys) {
      result[k] = Math.round(weights[k] * ratio * 100) / 100;
    }
  }

  // Fix rounding drift — adjust the largest "other" key
  const currentSum = WEIGHT_LABELS.reduce((s, w) => s + result[w.key], 0);
  const drift = Math.round((1.0 - currentSum) * 100) / 100;
  if (drift !== 0) {
    const largestOther = otherKeys.reduce((a, b) =>
      result[a] >= result[b] ? a : b,
    );
    result[largestOther] = Math.round((result[largestOther] + drift) * 100) / 100;
  }

  return result;
}

export default function WeightConfig({
  weights,
  onChange,
  defaults,
  onReset,
}: WeightConfigProps) {
  const handleSliderChange = useCallback(
    (key: WeightKey, rawValue: number) => {
      const value = Math.round(rawValue * 100) / 100;
      const updated = { ...weights, [key]: value };
      onChange(normalize(updated, key));
    },
    [weights, onChange],
  );

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span
          className="text-xs font-semibold uppercase tracking-wider"
          style={{
            fontFamily: "var(--font-cinzel), Cinzel, Georgia, serif",
            color: "var(--color-text-secondary)",
          }}
        >
          Pesos do Score
        </span>
        {defaults && (
          <button
            onClick={onReset}
            className="text-xs underline"
            style={{ color: "var(--color-info)" }}
          >
            Restaurar padrões
          </button>
        )}
      </div>

      {WEIGHT_LABELS.map(({ key, label }) => (
        <div key={key}>
          <div className="mb-1 flex items-center justify-between">
            <label
              htmlFor={`weight-${key}`}
              className="text-xs"
              style={{ color: "var(--color-text-secondary)" }}
            >
              {label}
            </label>
            <span
              className="text-xs tabular-nums"
              style={{
                fontFamily: "var(--font-plex-mono), IBM Plex Mono, monospace",
                color: "var(--color-text-primary)",
              }}
            >
              {weights[key].toFixed(2)}
            </span>
          </div>
          <input
            id={`weight-${key}`}
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={weights[key]}
            onChange={(e) => handleSliderChange(key, parseFloat(e.target.value))}
            className="w-full accent-[var(--color-accent-gold)]"
            aria-label={`Peso de ${label}`}
          />
        </div>
      ))}
    </div>
  );
}
