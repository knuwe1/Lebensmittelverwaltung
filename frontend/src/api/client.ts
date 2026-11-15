export interface ApiErrorBody {
  code: string;
  message: string;
  details?: unknown;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: unknown;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.status = status;
    this.code = body.code;
    this.details = body.details;
  }

  /** Validierungsfehler je Feld, wie vom Backend geliefert. */
  get fieldErrors(): Record<string, string> {
    if (!Array.isArray(this.details)) return {};
    return Object.fromEntries(
      (this.details as { field?: string; message?: string }[])
        .filter((d) => d.field)
        .map((d) => [d.field!, d.message ?? '']),
    );
  }
}

/** Netzwerkfehler: Die Anfrage hat den Server nicht erreicht (NFR-REL-003). */
export class NetworkError extends Error {
  constructor() {
    super('Keine Verbindung zum Server. Die Aktion wurde nicht gespeichert.');
  }
}

type Query = Record<string, string | number | boolean | undefined | null | string[]>;

export interface RequestOptions {
  query?: Query;
  body?: unknown;
  /** Schützt Buchungen vor doppelter Ausführung bei Wiederholungen (BR-017). */
  idempotencyKey?: string;
  signal?: AbortSignal;
}

function buildUrl(path: string, query?: Query): string {
  const url = new URL(`/api/v1${path}`, window.location.origin);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value === undefined || value === null || value === '') continue;
    if (Array.isArray(value)) value.forEach((v) => url.searchParams.append(key, v));
    else url.searchParams.set(key, String(value));
  }
  return url.pathname + url.search;
}

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

export async function apiRequest<T>(
  method: string,
  path: string,
  opts: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  let body: BodyInit | undefined;
  if (opts.body instanceof FormData) {
    body = opts.body;
  } else if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(opts.body);
  }
  if (opts.idempotencyKey) headers['Idempotency-Key'] = opts.idempotencyKey;

  let response: Response;
  try {
    response = await fetch(buildUrl(path, opts.query), {
      method,
      headers,
      body,
      credentials: 'same-origin',
      signal: opts.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err;
    throw new NetworkError();
  }

  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith('/auth/login')) onUnauthorized?.();
    const errBody: ApiErrorBody = data?.error ?? {
      code: 'http_error',
      message: `Unerwarteter Serverfehler (${response.status}).`,
    };
    throw new ApiError(response.status, errBody);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string, query?: Query, signal?: AbortSignal) =>
    apiRequest<T>('GET', path, { query, signal }),
  post: <T>(path: string, body?: unknown, opts: Omit<RequestOptions, 'body'> = {}) =>
    apiRequest<T>('POST', path, { ...opts, body }),
  patch: <T>(path: string, body?: unknown) => apiRequest<T>('PATCH', path, { body }),
  put: <T>(path: string, body?: unknown) => apiRequest<T>('PUT', path, { body }),
  delete: <T = void>(path: string) => apiRequest<T>('DELETE', path),
};

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError || err instanceof NetworkError) return err.message;
  return 'Ein unerwarteter Fehler ist aufgetreten.';
}

export function newIdempotencyKey(): string {
  return crypto.randomUUID();
}
