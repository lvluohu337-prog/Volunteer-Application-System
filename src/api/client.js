const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(/\/$/, "");

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

async function buildHttpError(response) {
  let message =
    response.status >= 500
      ? "后端服务暂时不可用，请稍后重试。"
      : `请求失败（状态码 ${response.status}）。`;

  try {
    const contentType = response.headers.get("Content-Type") || "";
    if (contentType.includes("application/json")) {
      const payload = await response.json();
      const resolvedMessage =
        payload?.message ||
        payload?.detail ||
        payload?.error ||
        payload?.data?.message ||
        payload?.data?.detail;
      if (resolvedMessage) {
        message = String(resolvedMessage);
      }
    } else if (response.status < 500) {
      const text = (await response.text()).trim();
      if (text) {
        message = text;
      }
    }
  } catch {
    // Keep the fallback HTTP status message.
  }

  return new Error(message);
}

export async function apiRequest(path, options = {}) {
  const {
    transform,
    query,
    body,
    method = body ? "POST" : "GET",
    unwrapData = true,
    ...fetchOptions
  } = options;

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
      throw await buildHttpError(response);
    }

    const payload = await response.json();
    const resolvedData = resolveResponsePayload(payload, unwrapData);
    return typeof transform === "function" ? transform(resolvedData) : resolvedData;
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error("后端接口当前不可达，请确认服务是否已启动后重试。");
    }
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("请求失败，请检查网络或稍后重试。");
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
    throw await buildHttpError(response);
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

export { API_BASE_URL, buildQueryString, buildUrl, normalizeQuery };
