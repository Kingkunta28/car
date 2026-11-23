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

function uploadWithProgress(url, form, headers, signal, onUploadProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const abort = () => xhr.abort();
    xhr.open("POST", url);
    xhr.withCredentials = true;
    Object.entries(headers).forEach(([key, value]) => xhr.setRequestHeader(key, value));
    xhr.upload.addEventListener("progress", (event) => {
      onUploadProgress({ loaded: event.loaded, total: event.total, percent: event.lengthComputable
        ? Math.round((event.loaded / Math.max(event.total, 1)) * 100) : null });
    });
    xhr.onload = () => {
      signal?.removeEventListener("abort", abort);
      const contentType = xhr.getResponseHeader("content-type") || "";
      let data = null;
      if (contentType.includes("application/json")) {
        try { data = JSON.parse(xhr.responseText); } catch { data = null; }
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(data);
      else reject(new ApiError(xhr.status, data));
    };
    xhr.onerror = () => {
      signal?.removeEventListener("abort", abort);
      reject(new TypeError("Network request failed"));
    };
    xhr.onabort = () => {
      signal?.removeEventListener("abort", abort);
      reject(new DOMException("The upload was cancelled.", "AbortError"));
    };
    if (signal?.aborted) {
      xhr.abort();
      return;
    }
    signal?.addEventListener("abort", abort, { once: true });
    xhr.send(form);
  });
}

/**
 * request(path, { method, body, form, guest, raw })
 *  - body: JSON payload; form: FormData (multipart)
 *  - guest: { reference, token } → sent as headers, never in the URL
 *  - raw: return the Response (for file downloads)
 */
export async function request(path, { method = "GET", body, form, guest, raw, params, signal, onUploadProgress } = {}) {
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
  const url = `${BASE}${path}${qs}`;
  if (form && onUploadProgress) return uploadWithProgress(url, form, headers, signal, onUploadProgress);
  const res = await fetch(url, {
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

/** Fetch a protected PDF into a blob URL for preview and/or download. */
export async function fetchPdf(path, opts = {}, fallbackName = "document.pdf") {
  const res = await request(path, { ...opts, raw: true });
  const blob = await res.blob();
  const cd = res.headers.get("content-disposition") || "";
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(cd);
  const name = match ? decodeURIComponent(match[1]) : fallbackName;
  const url = URL.createObjectURL(blob);
  return { url, name };
}

export function triggerDownload(url, name) {
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  document.body.appendChild(a);
  a.click();
  a.remove();
}

/** Download a protected PDF and save it with the server-provided filename. */
export async function download(path, opts = {}, fallbackName = "document.pdf") {
  const { url, name } = await fetchPdf(path, opts, fallbackName);
  if (opts.preview) {
    window.open(url, "_blank", "noopener");
  } else {
    triggerDownload(url, name);
  }
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
