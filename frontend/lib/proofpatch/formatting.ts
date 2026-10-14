export function text(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(text).join("\n");
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    if (record.msg || record.message || record.detail)
      return text(record.msg ?? record.message ?? record.detail);
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}
export function timing(seconds?: number) {
  if (seconds == null || !Number.isFinite(seconds)) return "—";
  if (seconds === 0) return "0 s";
  const [value, unit] =
    Math.abs(seconds) < 0.001
      ? [seconds * 1e6, "µs"]
      : Math.abs(seconds) < 1
        ? [seconds * 1e3, "ms"]
        : [seconds, "s"];
  return `${Number(value).toPrecision(5)} ${unit}`;
}
export function percent(value?: number) {
  return value == null || !Number.isFinite(value)
    ? "—"
    : `${value.toFixed(2)}%`;
}
export function date(value: string, timeOnly = false) {
  const d = new Date(value);
  return Number.isNaN(d.getTime())
    ? "—"
    : timeOnly
      ? d.toLocaleTimeString()
      : d.toLocaleString();
}
export function githubURL(value?: string) {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    return url.protocol === "https:" && url.hostname === "github.com"
      ? url.href
      : undefined;
  } catch {
    return undefined;
  }
}
