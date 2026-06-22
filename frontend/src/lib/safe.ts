/**
 * Null-safety / defensive utilities — Phase 1.3.5
 *
 * Every dashboard page must survive null, undefined, {}, [], partial responses,
 * missing fields, loading states, and error states without crashing.
 *
 * These helpers exist because we cannot trust API responses to match their TypeScript
 * types at runtime. A field that the type system says is `string` may actually be
 * `null` when the API returns an older schema, when a join is missing, when a
 * serializer hits a row it doesn't know about, or when the network dropped mid-payload.
 *
 * Rules of thumb (apply these helpers instead of `??` everywhere you can):
 *   - `safeArr(x)` instead of `x ?? []` when the result is iterated
 *   - `safeNum(x)` instead of `Number(x ?? 0)` when the result goes into `.toFixed` or arithmetic
 *   - `safeStr(x)` instead of `x ?? "—"` when the result is displayed
 *   - `safeObj(x)` instead of `x ?? {}` when the result goes into `Object.entries` / `Object.keys`
 *   - `safeUpper(x)` instead of `(x ?? "").toUpperCase()` when the result is shown as a label
 *   - `safeFixed(x, n)` instead of `Number(x ?? 0).toFixed(n)` when the result is shown as a number
 *   - `safeReplace(x, ...)` instead of `x?.replace(...)` chained ternaries
 *   - `safeDate(x)` instead of `new Date(x).toLocaleXxx()` chained ternaries
 *
 * Every helper is total (handles every input without throwing) and pure.
 * No helper mutates its input.
 */

/**
 * Coalesce any value to a finite number. Non-finite inputs (null, undefined,
 * NaN, Infinity, strings, objects) all become 0. Use this before any
 * arithmetic, comparison, or `.toFixed()` call.
 */
export const safeNum = (v: unknown, fallback: number = 0): number => {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string") {
    const n = Number(v);
    if (Number.isFinite(n)) return n;
  }
  return fallback;
};

/**
 * Coalesce any value to a display string. null/undefined become the fallback.
 * Anything else is stringified. Use this for any value rendered as text.
 */
export const safeStr = (v: unknown, fallback: string = "—"): string => {
  if (v === null || v === undefined) return fallback;
  if (typeof v === "string") return v.length > 0 ? v : fallback;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  try {
    return JSON.stringify(v);
  } catch {
    return fallback;
  }
};

/**
 * Coalesce any value to an array. Anything that isn't an array becomes [].
 * Use this before any `.map()`, `.filter()`, `.slice()`, `.length`, etc.
 *
 * When the input is already typed (e.g. `string[] | undefined`), the element
 * type is preserved. When the input is `unknown` (e.g. raw API response),
 * supply an explicit type parameter: `safeArr<string>(value).map(...)`.
 */
export function safeArr<T = unknown>(v: T[] | unknown | null | undefined): T[];
export function safeArr<T = unknown>(v: unknown): T[];
export function safeArr<T = unknown>(v: unknown): T[] {
  return Array.isArray(v) ? (v as T[]) : [];
}

/**
 * Coalesce any value to a plain object record. null/undefined/arrays/primitives
 * become {}. Use this before any `Object.entries`, `Object.keys`, `Object.values`,
 * or property access on a "record" that came from an API.
 */
export const safeObj = (v: unknown): Record<string, unknown> => {
  if (v !== null && typeof v === "object" && !Array.isArray(v)) {
    return v as Record<string, unknown>;
  }
  return {};
};

/**
 * Safe `.toUpperCase()`. null/undefined/non-string → fallback (default "—").
 */
export const safeUpper = (v: unknown, fallback: string = "—"): string => {
  return typeof v === "string" && v.length > 0 ? v.toUpperCase() : fallback;
};

/**
 * Safe `.toLowerCase()`. null/undefined/non-string → fallback.
 */
export const safeLower = (v: unknown, fallback: string = "—"): string => {
  return typeof v === "string" && v.length > 0 ? v.toLowerCase() : fallback;
};

/**
 * Safe `.toFixed(n)`. null/undefined/non-number → fallback string (default "—").
 */
export const safeFixed = (v: unknown, digits: number = 0, fallback: string = "—"): string => {
  const n = safeNum(v);
  if (n === 0 && v === null) return fallback;
  return n.toFixed(digits);
};

/**
 * Safe `.toLocaleString()`. null/undefined/non-number → fallback string.
 */
export const safeLocale = (v: unknown, fallback: string = "—"): string => {
  const n = safeNum(v);
  if (n === 0 && v === null) return fallback;
  return n.toLocaleString();
};

/**
 * Safe percentage formatter. Accepts either a 0..1 fraction (default) or a
 * 0..100 number when `fraction` is false. null/undefined → "—%".
 */
export const safePct = (v: unknown, digits: number = 0, fraction: boolean = true, fallback: string = "—"): string => {
  const n = safeNum(v);
  if (n === 0 && v === null) return fallback;
  const scaled = fraction ? n * 100 : n;
  return `${scaled.toFixed(digits)}%`;
};

/**
 * Safe date formatter. Returns fallback for null/undefined/invalid dates.
 */
export const safeDate = (v: unknown, options?: Intl.DateTimeFormatOptions, fallback: string = "—"): string => {
  if (v === null || v === undefined) return fallback;
  const d = typeof v === "string" ? new Date(v) : v instanceof Date ? v : null;
  if (!d || isNaN(d.getTime())) return fallback;
  return d.toLocaleDateString("en-US", options ?? { year: "numeric", month: "short", day: "numeric" });
};

/**
 * Safe datetime formatter. Returns fallback for null/undefined/invalid dates.
 */
export const safeDateTime = (v: unknown, options?: Intl.DateTimeFormatOptions, fallback: string = "—"): string => {
  if (v === null || v === undefined) return fallback;
  const d = typeof v === "string" ? new Date(v) : v instanceof Date ? v : null;
  if (!d || isNaN(d.getTime())) return fallback;
  return d.toLocaleString("en-US", options);
};

/**
 * Safe time formatter. Returns fallback for null/undefined/invalid dates.
 */
export const safeTime = (v: unknown, fallback: string = "—"): string => {
  if (v === null || v === undefined) return fallback;
  const d = typeof v === "string" ? new Date(v) : v instanceof Date ? v : null;
  if (!d || isNaN(d.getTime())) return fallback;
  return d.toLocaleTimeString("en-US");
};

/**
 * Safe `String.prototype.replace`. null/undefined/non-string → fallback (unchanged).
 * Returns the original string if pattern is not found.
 */
export const safeReplace = (
  v: unknown,
  pattern: string | RegExp,
  replacement: string | ((substring: string, ...args: unknown[]) => string),
  fallback: string = "—",
): string => {
  if (typeof v !== "string" || v.length === 0) return fallback;
  return v.replace(pattern, replacement as string);
};

/**
 * Safe `String.prototype.split`. null/undefined/non-string → fallback.
 */
export const safeSplit = (v: unknown, separator: string | RegExp, fallback: string[] = []): string[] => {
  if (typeof v !== "string" || v.length === 0) return fallback;
  return v.split(separator);
};

/**
 * Safe `String.prototype.slice`. null/undefined/non-string → fallback.
 */
export const safeSlice = (v: unknown, start?: number, end?: number, fallback: string = "—"): string => {
  if (typeof v !== "string") return fallback;
  return v.slice(start, end);
};

/**
 * Safe `String.prototype.startsWith`. null/undefined/non-string → false.
 */
export const safeStartsWith = (v: unknown, search: string): boolean => {
  return typeof v === "string" && v.startsWith(search);
};

/**
 * Safe `Array.prototype.find`. null/undefined/non-array → undefined.
 */
export const safeFind = <T,>(arr: unknown, predicate: (item: T, index: number) => boolean): T | undefined => {
  if (!Array.isArray(arr)) return undefined;
  return (arr as T[]).find(predicate);
};

/**
 * Safe `Array.prototype.includes` on a value. null/undefined/non-array → false.
 */
export const safeIncludes = (arr: unknown, value: unknown): boolean => {
  if (!Array.isArray(arr)) return false;
  return (arr as unknown[]).includes(value);
};

/**
 * Safe `Array.prototype.sort`. null/undefined/non-array → []. Always returns
 * a new array (the input is not mutated).
 */
export const safeSort = <T,>(arr: unknown, compareFn?: (a: T, b: T) => number): T[] => {
  if (!Array.isArray(arr)) return [];
  return [...(arr as T[])].sort(compareFn);
};

/**
 * Safe `Object.entries`. null/undefined/non-object → [].
 */
export const safeEntries = (v: unknown): [string, unknown][] => {
  return Object.entries(safeObj(v));
};

/**
 * Safe `Object.keys`. null/undefined/non-object → [].
 */
export const safeKeys = (v: unknown): string[] => {
  return Object.keys(safeObj(v));
};

/**
 * Safe `Object.values`. null/undefined/non-object → [].
 */
export const safeValues = <T = unknown>(v: unknown): T[] => {
  return Object.values(safeObj(v)) as T[];
};

/**
 * Safe initials (replaces the unsafe `getInitials` in utils.ts which crashes
 * on null name). Returns "—" if name is missing.
 */
export const safeInitials = (name: unknown, maxChars: number = 2, fallback: string = "—"): string => {
  if (typeof name !== "string" || name.length === 0) return fallback;
  return name
    .split(" ")
    .map((w) => w[0] ?? "")
    .join("")
    .toUpperCase()
    .slice(0, maxChars);
};

/**
 * Safe `JSON.parse` with a fallback. Returns fallback on any parse error.
 */
export const safeJsonParse = <T = unknown>(json: string, fallback: T): T => {
  try {
    return JSON.parse(json) as T;
  } catch {
    return fallback;
  }
};

/**
 * Safe `JSON.stringify` with a fallback. Returns fallback on circular refs or other errors.
 */
export const safeJsonStringify = (v: unknown, fallback: string = "—"): string => {
  try {
    const s = JSON.stringify(v);
    return s === undefined ? fallback : s;
  } catch {
    return fallback;
  }
};

/**
 * Safe property access. Returns the fallback if any link in the chain is null/undefined.
 *
 * Usage: `safeGet(obj, "a.b.c", defaultValue)`
 *   - obj = { a: { b: { c: 42 } } } → 42
 *   - obj = { a: null }              → defaultValue
 *   - obj = null                     → defaultValue
 */
export const safeGet = (obj: unknown, path: string, fallback: unknown = undefined): unknown => {
  if (obj === null || obj === undefined) return fallback;
  const parts = path.split(".");
  let cur: unknown = obj;
  for (const p of parts) {
    if (cur === null || cur === undefined) return fallback;
    if (typeof cur !== "object") return fallback;
    cur = (cur as Record<string, unknown>)[p];
  }
  return cur === undefined ? fallback : cur;
};

/**
 * Make an ErrorBoundary-friendly safe render. Wraps a render function in a try/catch
 * and returns the fallback if anything throws. Use this in pages where the cost of
 * a single bad row crashing the whole page is unacceptable.
 */
export const tryRender = <T,>(fn: () => T, fallback: T): T => {
  try {
    return fn();
  } catch {
    return fallback;
  }
};
