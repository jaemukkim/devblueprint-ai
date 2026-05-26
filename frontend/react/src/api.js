const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL;

// 로컬 Docker API 포트와 충돌하는 8000 설정이 주입되면, 패치된 로컬 FastAPI 서버인 8010으로 보정합니다.
const API_BASE_URL = configuredApiBaseUrl === "http://localhost:8000"
  ? "http://localhost:8010"
  : configuredApiBaseUrl || "http://localhost:8010";

async function requestJson(path, options = {}) {
  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });
  } catch (err) {
    throw createRequestError(
      "API 서버에 연결하지 못했습니다. FastAPI가 켜져 있는지, API 주소가 맞는지 확인해 주세요.",
      "network",
      0,
      err,
    );
  }

  if (response.status === 204) {
    return null;
  }

  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    const message = body.detail || `API 요청에 실패했습니다. status=${response.status}`;
    throw createRequestError(message, classifyApiError(response.status, message), response.status);
  }

  return body;
}

// UI에서 연결 대상과 오류 유형을 함께 보여줄 수 있도록 API 기본 주소를 공개합니다.
export const apiBaseUrl = API_BASE_URL;

// API 상태 점검 패널에서 FastAPI health endpoint를 호출합니다.
export function getHealth() {
  return requestJson("/health");
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

export function regenerateBlueprintSection(id, section, instruction) {
  return requestJson(`/api/v1/blueprints/${id}/sections/${section}/regenerate`, {
    method: "POST",
    body: JSON.stringify(instruction ? { instruction } : {}),
  });
}

export function deleteBlueprint(id) {
  return requestJson(`/api/v1/blueprints/${id}`, {
    method: "DELETE",
  });
}

// 서버 응답 문구와 status를 바탕으로 사용자가 이해하기 쉬운 오류 범주를 만듭니다.
function classifyApiError(status, message) {
  if (status === 503 && message.includes("OpenAI API")) {
    return "openai";
  }
  if (status === 503 && message.includes("품질 검증")) {
    return "validation";
  }
  if (status >= 500) {
    return "server";
  }
  if (status === 409) {
    return "duplicate";
  }
  if (status === 404) {
    return "not_found";
  }
  return "request";
}

// Error 객체에 분류 정보를 붙여 화면에서 상세 안내를 선택할 수 있게 합니다.
function createRequestError(message, type, status = 0, cause = null) {
  const error = new Error(message);
  error.type = type;
  error.status = status;
  error.cause = cause;
  return error;
}
