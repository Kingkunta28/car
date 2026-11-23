// Thin fetch wrapper. All requests go to same-origin /api (proxied in dev,
// rewritten in production), so session cookies and CSRF behave normally.
import i18n from "../i18n";
const BASE = (import.meta.env.VITE_API_BASE || "") + "/api/v1";

export class ApiError extends Error {
  constructor(status, body) {
    const err = body?.error || {};
    super("");
    this.status = status;
    this.code = err.code;
    this.originalMessage = err.message || `Request failed (${status})`;
    this.details = err.details || null;
  }
  get message() {
    const code = this.code || (this.status === 404 ? "not_found"
      : this.status === 409 ? "conflict"
        : this.status >= 500 || this.status === 401 || this.status === 403 || this.status === 405 || this.status === 429
          ? "server_error" : this.status === 400 ? "validation_error" : null);
    const key = code ? `errors.api.${code}` : "";
    return key && i18n.exists(key) ? i18n.t(key) : this.originalMessage;
  }
  fieldErrors() {
    const out = {};
    const walk = (obj, prefix = "") => {
      if (!obj || typeof obj !== "object") return;
      for (const [k, v] of Object.entries(obj)) {
        const key = prefix ? `${prefix}.${k}` : k;
        if (Array.isArray(v) && v.every((x) => typeof x === "string")) out[key] = v[0];
        else if (typeof v === "string") out[key] = v;
        else walk(v, key);
      }
    };
    walk(this.details);
    return out;
  }
}

function getCookie(name) {
  return document.cookie.split("; ").find((c) => c.startsWith(name + "="))?.split("=")[1];
}

let csrfPromise = null;
export async function ensureCsrf() {
  if (getCookie("csrftoken")) return decodeURIComponent(getCookie("csrftoken"));
  csrfPromise ||= fetch(`${BASE}/admin/auth/csrf/`, { credentials: "include" }).then((r) => r.json());
  const data = await csrfPromise;
  csrfPromise = null;
  return data.csrfToken;
}

/**
 * request(path, { method, body, form, guest, raw })
 *  - body: JSON payload; form: FormData (multipart)
 *  - guest: { reference, token } → sent as headers, never in the URL
 *  - raw: return the Response (for file downloads)
 */
export async function request(path, { method = "GET", body, form, guest, raw, params, signal } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (guest) {
    headers["X-Booking-Reference"] = guest.reference;
    headers["X-Booking-Token"] = guest.token;
  }
  // Public APIs use AllowAny and do not rely on a browser session. Only the
  // session-authenticated admin endpoints need a CSRF token; avoid an extra
  // CSRF round trip for public quote and booking requests.
  if (method !== "GET" && method !== "HEAD" && path.startsWith("/admin/")) {
    headers["X-CSRFToken"] = await ensureCsrf();
  }
  const qs = params ? "?" + new URLSearchParams(Object.entries(params).filter(([, v]) => v !== "" && v != null)) : "";
  const res = await fetch(`${BASE}${path}${qs}`, {
    method, headers, credentials: "include", signal,
    body: form || (body !== undefined ? JSON.stringify(body) : undefined),
  });
  if (raw && res.ok) return res;
  if (res.status === 204) return null;
  const ct = res.headers.get("content-type") || "";
  const data = ct.includes("application/json") ? await res.json() : null;
  if (!res.ok) throw new ApiError(res.status, data);
  return data;
}

/** Download a file response and save it with the server-provided filename. */
export async function download(path, opts = {}, fallbackName = "document.pdf") {
  const res = await request(path, { ...opts, raw: true });
  const blob = await res.blob();
  const cd = res.headers.get("content-disposition") || "";
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(cd);
  const name = match ? decodeURIComponent(match[1]) : fallbackName;
  const url = URL.createObjectURL(blob);
  if (opts.preview) {
    window.open(url, "_blank", "noopener");
  } else {
    const a = Object.assign(document.createElement("a"), { href: url, download: name });
    document.body.appendChild(a);
    a.click();
    a.remove();
  }
  setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

/** Save a PDF included as base64 in a successful booking response. */
export function downloadBase64Pdf(encoded, fileName) {
  if (typeof encoded !== "string" || !encoded) throw new Error("The voucher PDF was empty.");
  const binary = window.atob(encoded);
  const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
  const blob = new Blob([bytes], { type: "application/pdf" });
  if (blob.size < 5 || new TextDecoder().decode(bytes.subarray(0, 5)) !== "%PDF-") {
    throw new Error("The voucher response was not a valid PDF.");
  }
  const url = URL.createObjectURL(blob);
  const link = Object.assign(document.createElement("a"), { href: url, download: fileName });
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

export const api = {
  get: (p, o) => request(p, { ...o, method: "GET" }),
  post: (p, body, o) => request(p, { ...o, method: "POST", body }),
  patch: (p, body, o) => request(p, { ...o, method: "PATCH", body }),
  del: (p, o) => request(p, { ...o, method: "DELETE" }),
  upload: (p, form, o) => request(p, { ...o, method: "POST", form }),
  uploadPatch: (p, form, o) => request(p, { ...o, method: "PATCH", form }),
};
