const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL;

// Vite 환경변수에 지정된 FastAPI 주소를 그대로 사용합니다.
const API_BASE_URL = configuredApiBaseUrl || "http://localhost:8010";

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
    const errorDetail = normalizeErrorDetail(body.detail, response.status);
    throw createRequestError(
      errorDetail.message,
      classifyApiError(response.status, errorDetail),
      response.status,
      null,
      errorDetail,
    );
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

export function listBlueprintRunEvents(id) {
  return requestJson(`/api/v1/blueprints/${id}/runs`);
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

export function applyBlueprintSectionPreview(id, section, result, instruction) {
  return requestJson(`/api/v1/blueprints/${id}/sections/${section}/apply`, {
    method: "POST",
    body: JSON.stringify({
      result,
      ...(instruction ? { instruction } : {}),
    }),
  });
}

export function deleteBlueprint(id) {
  return requestJson(`/api/v1/blueprints/${id}`, {
    method: "DELETE",
  });
}

// 서버의 표준 오류 구조와 status를 바탕으로 사용자가 이해하기 쉬운 오류 범주를 만듭니다.
function classifyApiError(status, errorDetail) {
  const code = errorDetail.errorCode || "";
  const message = errorDetail.message || "";

  if (code.includes("openai")) {
    return "openai";
  }
  if (code.includes("validation") || (status === 503 && message.includes("품질 검증"))) {
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

// 이전 문자열 detail과 새 구조화 detail을 같은 형태로 맞춥니다.
function normalizeErrorDetail(detail, status) {
  if (detail && typeof detail === "object") {
    return {
      message: detail.message || detail.detail || `API 요청에 실패했습니다. status=${status}`,
      errorCode: detail.error_code || detail.errorCode || "",
      hint: detail.hint || "",
      extra: detail.extra || null,
    };
  }

  return {
    message: detail || `API 요청에 실패했습니다. status=${status}`,
    errorCode: "",
    hint: "",
    extra: null,
  };
}

// Error 객체에 분류 정보를 붙여 화면에서 상세 안내를 선택할 수 있게 합니다.
function createRequestError(message, type, status = 0, cause = null, detail = null) {
  const error = new Error(message);
  error.type = type;
  error.status = status;
  error.cause = cause;
  error.errorCode = detail?.errorCode || "";
  error.hint = detail?.hint || "";
  error.extra = detail?.extra || null;
  return error;
}
