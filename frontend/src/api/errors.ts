/**
 * Normalized Error System for WMS API.
 * Maps HTTP status codes (400, 401, 403, 404, 409, 422, 500) and network failures
 * to user-friendly messages and field-level validation errors without exposing raw stack traces.
 */

export interface FieldValidationError {
  field: string;
  message: string;
}

export class WmsApiError extends Error {
  public readonly status: number;
  public readonly code: string;
  public readonly fieldErrors?: FieldValidationError[];
  public readonly isNetworkError: boolean;

  constructor(params: {
    status: number;
    message: string;
    code?: string;
    fieldErrors?: FieldValidationError[];
    isNetworkError?: boolean;
  }) {
    super(params.message);
    this.name = "WmsApiError";
    this.status = params.status;
    this.code = params.code || `HTTP_${params.status}`;
    this.fieldErrors = params.fieldErrors;
    this.isNetworkError = params.isNetworkError || false;
  }
}

export async function parseApiError(response: Response): Promise<WmsApiError> {
  const status = response.status;
  let body: any = null;

  try {
    body = await response.json();
  } catch {
    // Response body was not JSON
  }

  let message = "";
  let fieldErrors: FieldValidationError[] | undefined;

  // Extract raw detail string or array if provided by FastAPI Pydantic
  const rawDetail = body?.detail || body?.message || body?.error;

  if (Array.isArray(rawDetail)) {
    // 422 Unprocessable Entity - validation error list from Pydantic
    fieldErrors = rawDetail.map((item: any) => {
      const loc = Array.isArray(item.loc) ? item.loc.slice(1).join(".") : "field";
      return {
        field: loc,
        message: item.msg || "Invalid value",
      };
    });
    message = fieldErrors.map((f) => `${f.field}: ${f.message}`).join("; ") || "Validation failed";
  } else if (typeof rawDetail === "string" && rawDetail.trim().length > 0) {
    message = rawDetail;
  }

  // Fallback messages according to HTTP status code guidelines
  if (!message) {
    switch (status) {
      case 400:
        message = "Bad request. Please verify input data.";
        break;
      case 401:
        message = "Session expired. Please sign in again.";
        break;
      case 403:
        message = "You don't have permission to perform this action.";
        break;
      case 404:
        message = "The requested resource was not found.";
        break;
      case 409:
        message = "The operation could not be completed because the resource changed or is locked.";
        break;
      case 422:
        message = "Validation failed. Please check your input.";
        break;
      case 500:
      default:
        message = "Something went wrong on the server. Please try again.";
        break;
    }
  }

  return new WmsApiError({
    status,
    message,
    fieldErrors,
  });
}

export function createNetworkError(err: Error): WmsApiError {
  return new WmsApiError({
    status: 0,
    message: err.message || "Network error. Failed to reach WMS backend server.",
    code: "NETWORK_ERROR",
    isNetworkError: true,
  });
}
