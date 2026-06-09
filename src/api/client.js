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

export { API_BASE_URL, USE_MOCK, buildQueryString, normalizeQuery };
