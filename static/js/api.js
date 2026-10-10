/**
 * Centralised API client. Every browser -> Django JSON call goes through `window.api`
 * so auth, CSRF, error handling and base URL live in one place.
 *
 *   const health = await api.get("/health/");
 *   await api.post("/attempts/123/items/1/save/", { response: {...} });
 *   await api.upload("/attempts/123/items/1/audio/", formData);
 *   api.setHeader("Authorization", "Bearer <token>");   // future token auth
 *   api.onRequest((req) => req);                          // mutate outgoing requests
 *   api.onUnauthorized((err) => (location.href = "/accounts/login/"));
 */
(function (global) {
  "use strict";

  const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

  const config = {
    baseUrl: "/api",
    timeoutMs: 30000,
    headers: { Accept: "application/json" },
  };
  const requestHooks = [];
  const responseHooks = [];
  const unauthorizedHooks = [];

  class ApiError extends Error {
    constructor(message, { status = 0, data = null, response = null } = {}) {
      super(message);
      this.name = "ApiError";
      this.status = status;
      this.data = data;
      this.response = response;
    }
  }

  function getCookie(name) {
    const match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[1]) : null;
  }

  function csrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return (meta && meta.content) || getCookie("csrftoken");
  }

  function buildUrl(path, params) {
    const isAbsolute = /^https?:\/\//.test(path);
    const base = isAbsolute ? "" : config.baseUrl.replace(/\/$/, "");
    const url = new URL(base + (path.startsWith("/") ? path : "/" + path), global.location.origin);
    Object.entries(params || {}).forEach(([key, value]) => {
      if (value === undefined || value === null) return;
      [].concat(value).forEach((v) => url.searchParams.append(key, v));
    });
    return url.toString();
  }

  async function parseBody(response) {
    if (response.status === 204) return null;
    const type = response.headers.get("content-type") || "";
    return type.includes("application/json") ? response.json() : response.text();
  }

  async function request(method, path, options = {}) {
    const { params, body, headers, signal, timeoutMs = config.timeoutMs } = options;
    method = method.toUpperCase();

    let req = {
      method,
      url: buildUrl(path, params),
      headers: { ...config.headers, ...headers },
      body,
    };

    if (body !== undefined && !(body instanceof FormData) && !(body instanceof Blob)) {
      req.headers["Content-Type"] = "application/json";
      req.body = JSON.stringify(body);
    }
    if (!SAFE_METHODS.has(method)) {
      const token = csrfToken();
      if (token) req.headers["X-CSRFToken"] = token;
    }
    for (const hook of requestHooks) req = (await hook(req)) || req;

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    if (signal) signal.addEventListener("abort", () => controller.abort(), { once: true });

    let response;
    try {
      response = await fetch(req.url, {
        method: req.method,
        headers: req.headers,
        body: req.body,
        credentials: "same-origin",
        signal: controller.signal,
      });
    } catch (err) {
      const message = err.name === "AbortError" ? "Request timed out" : "Network error";
      throw new ApiError(message, { status: 0, data: err });
    } finally {
      clearTimeout(timer);
    }

    const data = await parseBody(response);
    for (const hook of responseHooks) await hook(response, data);

    if (!response.ok) {
      const message = (data && data.error) || response.statusText || "Request failed";
      const error = new ApiError(message, { status: response.status, data, response });
      if (response.status === 401 || response.status === 403) {
        unauthorizedHooks.forEach((hook) => hook(error));
      }
      throw error;
    }
    return data;
  }

  global.api = {
    ApiError,
    config,
    configure(overrides) {
      Object.assign(config, overrides);
    },
    setHeader(name, value) {
      config.headers[name] = value;
    },
    removeHeader(name) {
      delete config.headers[name];
    },
    onRequest(hook) {
      requestHooks.push(hook);
    },
    onResponse(hook) {
      responseHooks.push(hook);
    },
    onUnauthorized(hook) {
      unauthorizedHooks.push(hook);
    },
    request,
    get: (path, options) => request("GET", path, options),
    post: (path, body, options) => request("POST", path, { ...options, body }),
    put: (path, body, options) => request("PUT", path, { ...options, body }),
    patch: (path, body, options) => request("PATCH", path, { ...options, body }),
    delete: (path, options) => request("DELETE", path, options),
    upload: (path, formData, options) => request("POST", path, { ...options, body: formData }),
  };
})(window);
