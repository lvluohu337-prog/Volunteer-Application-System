const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(/\/$/, "");
const USE_MOCK = import.meta.env.VITE_USE_MOCK !== "false";

function normalizeQuery(query = {}) {
  return Object.fromEntries(
    Object.entries(query).filter(([, value]) => {
      if (value === undefined || value === null || value === "") {
        return false;
      }

      if (Array.isArray(value) && value.length === 0) {
        return false;
      }

      return true;
    })
  );
}

function buildQueryString(query = {}) {
  const searchParams = new URLSearchParams();

  Object.entries(normalizeQuery(query)).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach((item) => searchParams.append(key, item));
      return;
    }

    searchParams.append(key, String(value));
  });

  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : "";
}

function buildUrl(path, query) {
  if (/^https?:\/\//.test(path)) {
    return `${path}${buildQueryString(query)}`;
  }

  const basePath = API_BASE_URL
    ? `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`
    : path;

  return `${basePath}${buildQueryString(query)}`;
}

function parseContentDispositionFilename(headerValue) {
  if (!headerValue) {
    return "";
  }

  const utf8Match = headerValue.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      return utf8Match[1];
    }
  }

  const plainMatch = headerValue.match(/filename="?([^"]+)"?/i);
  return plainMatch?.[1] ?? "";
}

function triggerBrowserDownload(blob, filename) {
  const objectUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename || "download";
  anchor.style.display = "none";
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 1000);
}

function resolveResponsePayload(payload, unwrapData = true) {
  if (
    unwrapData &&
    payload &&
    typeof payload === "object" &&
    !Array.isArray(payload) &&
    Object.prototype.hasOwnProperty.call(payload, "data")
  ) {
    return payload.data;
  }

  return payload;
}

export async function apiRequest(path, options = {}) {
  const {
    mockData,
    transform,
    query,
    body,
    method = body ? "POST" : "GET",
    unwrapData = true,
    ...fetchOptions
  } = options;

  if (!API_BASE_URL && USE_MOCK && mockData !== undefined) {
    return typeof transform === "function" ? transform(mockData) : mockData;
  }

  try {
    const response = await fetch(buildUrl(path, query), {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(fetchOptions.headers ?? {})
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      ...fetchOptions
    });

    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    const payload = await response.json();
    const resolvedData = resolveResponsePayload(payload, unwrapData);
    return typeof transform === "function" ? transform(resolvedData) : resolvedData;
  } catch (error) {
    if (USE_MOCK && mockData !== undefined) {
      return typeof transform === "function" ? transform(mockData) : mockData;
    }

    throw error;
  }
}

export async function downloadRequest(path, options = {}) {
  const {
    query,
    body,
    method = body ? "POST" : "GET",
    filename,
    ...fetchOptions
  } = options;

  const headers = {
    ...(fetchOptions.headers ?? {})
  };
  if (body !== undefined && !Object.prototype.hasOwnProperty.call(headers, "Content-Type")) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(buildUrl(path, query), {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    ...fetchOptions
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  const blob = await response.blob();
  const resolvedFilename =
    filename ||
    parseContentDispositionFilename(response.headers.get("Content-Disposition")) ||
    "download";

  triggerBrowserDownload(blob, resolvedFilename);

  return {
    filename: resolvedFilename,
    contentType: response.headers.get("Content-Type") || blob.type || "",
    size: blob.size,
  };
}

export { API_BASE_URL, USE_MOCK, buildQueryString, buildUrl, normalizeQuery };
