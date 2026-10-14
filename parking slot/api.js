async function apiRequest(url, options = {}) {
    const response = await fetch(url, {
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "Something went wrong.");
    return data;
}
async function requireLogin() {
    try { return (await apiRequest("/api/me")).user; }
    catch (e) { location.href = "login.html"; return null; }
}
