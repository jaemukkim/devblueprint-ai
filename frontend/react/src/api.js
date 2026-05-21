const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function requestJson(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (response.status === 204) {
    return null;
  }

  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    const message = body.detail || `API 요청에 실패했습니다. status=${response.status}`;
    throw new Error(message);
  }

  return body;
}

export function createBlueprint(idea) {
  return requestJson("/api/v1/blueprint/generate", {
    method: "POST",
    body: JSON.stringify({ idea }),
  });
}

export function listBlueprints() {
  return requestJson("/api/v1/blueprints");
}

export function getBlueprint(id) {
  return requestJson(`/api/v1/blueprints/${id}`);
}

export function reviseBlueprint(id, instruction) {
  return requestJson(`/api/v1/blueprints/${id}/revise`, {
    method: "POST",
    body: JSON.stringify({ instruction }),
  });
}

export function deleteBlueprint(id) {
  return requestJson(`/api/v1/blueprints/${id}`, {
    method: "DELETE",
  });
}
