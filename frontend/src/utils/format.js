export function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatCompact(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }
  const numeric = Number(value);
  if (numeric === 0) return "0";
  if (Math.abs(numeric) >= 1000) {
    return numeric.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }
  if (Math.abs(numeric) >= 1) {
    return numeric.toLocaleString(undefined, { maximumFractionDigits: 3 });
  }
  if (Math.abs(numeric) < 1e-3) {
    return numeric.toExponential(2);
  }
  return numeric.toPrecision(4);
}

export function formatDifference(value, digits = 3) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }
  const numeric = Number(value);
  if (numeric === 0) return "0";
  const sign = numeric > 0 ? "+" : "";
  if (Math.abs(numeric) < 1e-3) {
    return `${sign}${numeric.toExponential(2)}`;
  }
  return `${sign}${numeric.toFixed(digits)}`;
}

export function statusLabel(status) {
  if (!status) return "Not run";
  return status.replaceAll("_", " ");
}
