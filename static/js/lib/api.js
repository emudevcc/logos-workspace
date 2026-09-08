// Small JSON fetch helpers with structured errors.

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `HTTP ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/**
 * @param {string} path
 * @returns {Promise<any>}
 */
export async function apiGet(path) {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new ApiError(response.status, await safeDetail(response));
  }
  return response.json();
}

/**
 * @param {string} path
 * @param {object} body
 * @returns {Promise<any>}
 */
export async function apiPost(path, body) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await safeDetail(response));
  }
  return response.json();
}

async function safeDetail(response) {
  try {
    const data = await response.json();
    return data.detail;
  } catch {
    return response.statusText;
  }
}
