/**
 * quo-client.ts: typed, dependency-free Quo (formerly OpenPhone) REST client
 * for server-side TypeScript. Copy it into your app (for example
 * `src/server/quo/quo-client.ts`). It never runs in the browser because the
 * API key has full workspace access.
 *
 * Covers both live API surfaces on https://api.quo.com:
 *   - v1:          `/v1/...` paths, no version header. Still the only way to SEND.
 *   - 2026-03-30:  unprefixed paths, `Quo-Api-Version: 2026-03-30` header REQUIRED,
 *                  `{ data, nextCursor }` envelope, `limit` (1-50) + `after` cursor,
 *                  bracket filters such as `status[in]=...`. Range operators differ per
 *                  endpoint (/calls: createdAt[gte|lte]; /messages: createdAt[gt|lt] only).
 *
 * Built-in behaviour every Quo integration needs:
 *   - Raw key in `Authorization` (no "Bearer ").
 *   - One limiter per client: 10 requests/second per key, shared by parallel tool
 *     calls and pagination IN THIS PROCESS ONLY. Two processes on one key each get
 *     their own budget, so split `maxRps` (e.g. worker 5 + web 4) or pass a
 *     cross-process `limiter` (Redis and so on), or give each integration its own key.
 *     Create ONE client per process and inject it into every route, webhook handler
 *     and tool there; a second client in the same process doubles the budget.
 *   - Retries only requests marked safe (GET by default, plus the mark-as-* POSTs
 *     and task status/due-date updates that opt in with `retry: true`) on 429/5xx
 *     with backoff + jitter. A POST that sends a
 *     message is NEVER retried automatically: a timeout does not mean "not sent".
 *   - Errors become `QuoApiError` with status, title, trace id and field-level
 *     `issues`, which a tool can hand back to the model so it can fix its call.
 */

export const QUO_API_VERSION = '2026-03-30' as const;

export type QuoSurface = 'v1' | typeof QUO_API_VERSION;
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

/**
 * Query values. Arrays serialize as repeated keys on v1 (`participants=a&participants=b`)
 * and as comma lists on 2026-03-30. Objects become bracket operators on
 * 2026-03-30: `{ createdAt: { gte: '...' } }` -> `createdAt[gte]=...`,
 * `{ status: { in: ['missed', 'no-answer'] } }` -> `status[in]=missed,no-answer`.
 */
export type QueryValue =
  | string
  | number
  | boolean
  | null
  | undefined
  | ReadonlyArray<string | number>
  | { readonly [op: string]: string | number | ReadonlyArray<string | number> | null | undefined };

export interface QuoRequest {
  surface: QuoSurface;
  method: HttpMethod;
  /** Path without host; v1 paths include the `/v1` prefix. */
  path: string;
  query?: Record<string, QueryValue>;
  body?: unknown;
  /** Defaults to true for GET, false otherwise. Never set true for sends. */
  retry?: boolean;
  signal?: AbortSignal;
}

export interface QuoIssue {
  path?: string;
  message: string;
  value?: unknown;
}

export class QuoApiError extends Error {
  readonly status: number;
  readonly title: string;
  readonly trace?: string;
  readonly issues: QuoIssue[];
  readonly retryable: boolean;

  constructor(init: {
    status: number;
    title: string;
    message: string;
    trace?: string;
    issues?: QuoIssue[];
  }) {
    super(init.message);
    this.name = 'QuoApiError';
    this.status = init.status;
    this.title = init.title;
    this.trace = init.trace;
    this.issues = init.issues ?? [];
    this.retryable = init.status === 429 || init.status >= 500;
  }

  /** Compact, secret-free shape that is safe to return to a model as a tool result. */
  toToolError() {
    return {
      ok: false as const,
      status: this.status,
      error: this.title,
      message: this.message,
      issues: this.issues,
      trace: this.trace,
      hint: hintFor(this.status),
    };
  }
}

function hintFor(status: number): string {
  if (status === 400 || status === 422) return 'Fix the fields named in issues, then call again.';
  if (status === 401) return 'Server API key is missing or invalid. Do not retry; tell the user.';
  if (status === 403) return 'Not allowed for this key, plan, or workspace setting. Do not retry.';
  if (status === 404) return 'Id not found in this workspace. Look it up with a list tool first.';
  if (status === 429) return 'Rate limited (10 req/s). Wait, then make fewer, larger requests.';
  return 'Quo server error. Reads can be retried later; never resend a message without checking it was not delivered.';
}

export interface QuoClientOptions {
  apiKey?: string;
  baseUrl?: string;
  /** Requests per second for this process. Quo allows 10 per key across ALL processes using it. */
  maxRps?: number;
  /**
   * Cross-process rate limiter. Resolve when one request may start. Use this when
   * several processes or serverless instances share one key; it replaces `maxRps`.
   */
  limiter?: (signal?: AbortSignal) => Promise<void>;
  maxRetries?: number;
  fetch?: typeof fetch;
  /** Called once per HTTP attempt; for logging and metrics. Never receives the key. */
  onRequest?: (info: { method: HttpMethod; url: string; status: number; ms: number; attempt: number }) => void;
}

export interface QuoPage<T> {
  data: T[];
  nextCursor: string | null;
}

export interface QuoClient {
  request<T = unknown>(req: QuoRequest): Promise<T>;
  /** 2026-03-30 helper. Returns the parsed body (usually `{ data }` or `{ data, nextCursor }`). */
  v2<T = unknown>(method: HttpMethod, path: string, init?: Omit<QuoRequest, 'surface' | 'method' | 'path'>): Promise<T>;
  /** v1 helper. `path` must start with `/v1/`. */
  v1<T = unknown>(method: HttpMethod, path: string, init?: Omit<QuoRequest, 'surface' | 'method' | 'path'>): Promise<T>;
  /** Walk a 2026-03-30 list until `nextCursor` is null or `max` items were read. */
  listAll<T>(path: string, query?: Record<string, QueryValue>, opts?: { max?: number; signal?: AbortSignal }): Promise<T[]>;
}

const sleep = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    if (signal?.aborted) return reject(signal.reason);
    const t = setTimeout(resolve, ms);
    signal?.addEventListener('abort', () => {
      clearTimeout(t);
      reject(signal.reason);
    }, { once: true });
  });

/** Sliding one-second window shared by every call made through one client. */
function createLimiter(maxRps: number) {
  const stamps: number[] = [];
  let chain: Promise<void> = Promise.resolve();
  return function acquire(signal?: AbortSignal): Promise<void> {
    const next = chain.then(async () => {
      for (;;) {
        const now = Date.now();
        while (stamps.length && now - stamps[0]! >= 1000) stamps.shift();
        if (stamps.length < maxRps) {
          stamps.push(now);
          return;
        }
        await sleep(1000 - (now - stamps[0]!) + 5, signal);
      }
    });
    chain = next.catch(() => undefined);
    return next;
  };
}

function serializeQuery(url: URL, surface: QuoSurface, query: Record<string, QueryValue> = {}) {
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null) continue;
    if (Array.isArray(value)) {
      if (surface === 'v1') for (const v of value) url.searchParams.append(key, String(v));
      else if (value.length) url.searchParams.set(key, value.join(','));
      continue;
    }
    if (typeof value === 'object') {
      for (const [op, v] of Object.entries(value)) {
        if (v === undefined || v === null) continue;
        url.searchParams.set(`${key}[${op}]`, Array.isArray(v) ? v.join(',') : String(v));
      }
      continue;
    }
    url.searchParams.set(key, String(value));
  }
}

async function toError(res: Response): Promise<QuoApiError> {
  const text = await res.text().catch(() => '');
  let json: any;
  try {
    json = text ? JSON.parse(text) : undefined;
  } catch {
    json = undefined;
  }
  // 2026-03-30 envelope: { title, message, docs, trace?, errors?: [{ path, message, value, schema }] }
  // v1 envelope:        { message, code, status, docs, title, trace?, errors?: [...] } (fields vary)
  const issues: QuoIssue[] = Array.isArray(json?.errors)
    ? json.errors.map((e: any) => ({ path: e.path, message: String(e.message ?? e), value: e.value }))
    : [];
  return new QuoApiError({
    status: res.status,
    title: json?.title ?? res.statusText ?? 'Error',
    message: json?.message ?? json?.error?.message ?? (text.slice(0, 300) || `HTTP ${res.status}`),
    trace: json?.trace ?? undefined,
    issues,
  });
}

export function createQuoClient(options: QuoClientOptions = {}): QuoClient {
  const apiKey = options.apiKey ?? process.env.QUO_API_KEY ?? process.env.OPENPHONE_API_KEY;
  if (!apiKey) throw new Error('Quo API key required: set QUO_API_KEY or pass { apiKey }.');
  if (/^bearer\s/i.test(apiKey)) throw new Error('Remove the "Bearer " prefix: Quo expects the raw key.');
  const baseUrl = (options.baseUrl ?? process.env.QUO_BASE_URL ?? 'https://api.quo.com').replace(/\/v1\/?$/, '').replace(/\/+$/, '');
  const maxRetries = options.maxRetries ?? 4;
  const doFetch = options.fetch ?? globalThis.fetch;
  const acquire = options.limiter ?? createLimiter(Math.max(1, Math.min(options.maxRps ?? 8, 10)));

  async function request<T>(req: QuoRequest): Promise<T> {
    if (req.surface === 'v1' && !req.path.startsWith('/v1/')) throw new Error(`v1 path must start with /v1/: ${req.path}`);
    if (req.surface !== 'v1' && req.path.startsWith('/v1/')) throw new Error(`2026-03-30 paths have no /v1 prefix: ${req.path}`);
    const url = new URL(baseUrl + req.path);
    serializeQuery(url, req.surface, req.query);
    const canRetry = req.retry ?? req.method === 'GET';

    for (let attempt = 0; ; attempt++) {
      await acquire(req.signal);
      const started = Date.now();
      const res = await doFetch(url, {
        method: req.method,
        signal: req.signal,
        headers: {
          Authorization: apiKey!, // raw key, never `Bearer ...`
          Accept: 'application/json',
          ...(req.surface === 'v1' ? {} : { 'Quo-Api-Version': req.surface }),
          ...(req.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        },
        body: req.body !== undefined ? JSON.stringify(req.body) : undefined,
      });
      options.onRequest?.({ method: req.method, url: url.pathname + url.search, status: res.status, ms: Date.now() - started, attempt });

      if (res.ok) {
        if (res.status === 204) return undefined as T;
        const text = await res.text();
        return (text ? JSON.parse(text) : undefined) as T;
      }
      if (canRetry && (res.status === 429 || res.status >= 500) && attempt < maxRetries) {
        const retryAfter = Number(res.headers.get('retry-after'));
        const wait = Number.isFinite(retryAfter) && retryAfter > 0
          ? retryAfter * 1000
          : Math.min(1000 * 2 ** attempt, 16000) + Math.floor(Math.random() * 400);
        await res.body?.cancel().catch(() => undefined);
        await sleep(wait, req.signal);
        continue;
      }
      throw await toError(res);
    }
  }

  const client: QuoClient = {
    request,
    v2: (method, path, init = {}) => request({ ...init, surface: QUO_API_VERSION, method, path }),
    v1: (method, path, init = {}) => request({ ...init, surface: 'v1', method, path }),
    async listAll<T>(path: string, query: Record<string, QueryValue> = {}, opts: { max?: number; signal?: AbortSignal } = {}) {
      const max = opts.max ?? 500;
      const out: T[] = [];
      let after: string | null = null;
      do {
        const page: QuoPage<T> = await client.v2<QuoPage<T>>('GET', path, {
          query: { ...query, limit: 50, after: after ?? undefined },
          signal: opts.signal,
        });
        out.push(...page.data);
        after = page.nextCursor;
      } while (after && out.length < max);
      return out.slice(0, max);
    },
  };
  return client;
}
