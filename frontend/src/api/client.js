const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, { status = 0, code = "REQUEST_FAILED", field = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.field = field;
  }
}

async function parseBody(response) {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  const text = await response.text();
  return text ? { detail: text } : null;
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });
  } catch {
    throw new ApiError(
      "Cannot reach the backend. Start the FastAPI server and retry.",
      { code: "BACKEND_OFFLINE" },
    );
  }

  const body = await parseBody(response);
  if (!response.ok) {
    const detail = body?.detail;
    throw new ApiError(
      typeof detail === "string"
        ? detail
        : detail?.message || `Request failed with status ${response.status}.`,
      {
        status: response.status,
        code: detail?.code || "REQUEST_FAILED",
        field: detail?.field || null,
      },
    );
  }
  return body;
}

export function getHealth() {
  return request("/api/health");
}

export function getParameters() {
  return request("/api/parameters");
}

export function getScenarios() {
  return request("/api/scenarios");
}

export function getResults() {
  return request("/api/results");
}

export function simulate(configuration) {
  return request("/api/simulate", {
    method: "POST",
    body: JSON.stringify(configuration),
  });
}

export function simulateBatch(configuration = {}) {
  return request("/api/simulate/batch", {
    method: "POST",
    body: JSON.stringify(configuration),
  });
}

export function runValidation(correctionMode = "pool_carrera_flux") {
  return request("/api/validate", {
    method: "POST",
    body: JSON.stringify({ correction_mode: correctionMode }),
  });
}

export function generateDataset(correctionMode = "pool_carrera_flux") {
  return request("/api/dataset/generate", {
    method: "POST",
    body: JSON.stringify({
      correction_mode: correctionMode,
      run_validation_after: true,
    }),
  });
}

export async function downloadDataset() {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/api/dataset/download`);
  } catch {
    throw new ApiError(
      "Cannot reach the backend to download the dataset.",
      { code: "BACKEND_OFFLINE" },
    );
  }
  if (!response.ok) {
    const body = await parseBody(response);
    const detail = body?.detail;
    throw new ApiError(
      detail?.message || "The dataset is not available yet.",
      {
        status: response.status,
        code: detail?.code || "DOWNLOAD_FAILED",
      },
    );
  }
  return response.blob();
}

export { API_BASE_URL };
