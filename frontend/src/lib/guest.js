// Guest booking credentials live in sessionStorage only (cleared when the tab
// closes) and are read from the URL *fragment*, which is never sent to servers.
const KEY = "rafiki.guest";

export function saveGuest(reference, token) {
  try {
    sessionStorage.setItem(KEY, JSON.stringify({ reference, token }));
  } catch { /* storage unavailable — page still works via the link */ }
}

export function loadGuest() {
  const hash = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  const ref = hash.get("ref");
  const token = hash.get("token");
  if (ref && token) {
    saveGuest(ref, token);
    // Remove credentials from the address bar / history.
    window.history.replaceState(null, "", window.location.pathname + window.location.search);
    return { reference: ref, token };
  }
  try {
    const v = JSON.parse(sessionStorage.getItem(KEY) || "null");
    return v?.reference && v?.token ? v : null;
  } catch {
    return null;
  }
}

export function clearGuest() {
  try { sessionStorage.removeItem(KEY); } catch { /* ignore */ }
}
