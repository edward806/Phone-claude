# Test Coverage Analysis — Phone-claude

> Generated against commit on branch `claude/analyze-test-coverage-QRIRm`.
> All 38 tests pass. Coverage figures come from `npm run test:coverage`.

---

## 1. Current Coverage Summary

| Scope | Statements | Branches | Functions | Lines |
|---|---|---|---|---|
| **All files** | 59.54 % | 60.21 % | 55.81 % | 60.36 % |
| `config/index.js` | 33 % | 89 % | **0 %** | 33 % |
| `middleware/rateLimiter.js` | 95 % | 78 % | 100 % | 95 % |
| `middleware/twilioAuth.js` | 24 % | **0 %** | **0 %** | 24 % |
| `routes/outbound.js` | **0 %** | 100 % | **0 %** | **0 %** |
| `routes/voice.js` | 76 % | 50 % | 80 % | 76 % |
| `services/claudeService.js` | 77 % | 71 % | 75 % | 77 % |
| `services/sessionService.js` | **20 %** | **14 %** | **10 %** | **22 %** |
| `services/twilioService.js` | 70 % | 69 % | 60 % | 70 % |
| `utils/logger.js` | 100 % | 100 % | 100 % | 100 % |
| `utils/validators.js` | 100 % | 100 % | 100 % | 100 % |

**Configured thresholds (70 % globally) are currently not met.**
The three biggest contributors to the gap are `sessionService.js`, `twilioAuth.js`, and `routes/outbound.js`.

---

## 2. Detailed Gap Analysis

### 2.1 `services/sessionService.js` — 20 % statements / 14 % branches / 10 % functions

This is the most critical gap. `SessionService` manages all per-call conversation state; bugs here would silently drop history or corrupt sessions. Yet it has virtually no tests because every method requires a live Redis connection.

**Untested paths (lines 14–98):**
- `connect()` — first-call connection, idempotency guard, Redis error event
- `disconnect()` — quit path and idempotency guard
- `get()` — cache hit, cache miss (`null`), JSON parse failure (corrupt data)
- `set()` — `setEx` call with correct TTL
- `appendMessage()` — creates new session when none exists, appends to existing
- `delete()` — `del` call
- `historyLength()` — returns 0 for missing session, correct count otherwise

**Recommended fix:** Inject a fake Redis client (or use `ioredis-mock` / `jest-mock-redis`) so every method can be exercised without a running Redis server.

```js
// Example: inject a fake client
const fakRedis = {
  get: jest.fn().mockResolvedValue(null),
  setEx: jest.fn().mockResolvedValue('OK'),
  del: jest.fn().mockResolvedValue(1),
  connect: jest.fn(),
  quit: jest.fn(),
  on: jest.fn(),
};
const svc = new SessionService(fakRedis);
svc._connected = true; // skip connect() in unit tests
```

---

### 2.2 `middleware/twilioAuth.js` — 24 % statements / 0 % branches / 0 % functions

The Twilio webhook signature validator is bypassed in every existing test via a module-level mock (`jest.mock('../../src/middleware/twilioAuth', () => ...)`). As a result, none of the actual implementation is ever exercised.

**Untested branches:**
- `SKIP_TWILIO_AUTH=true` — bypass path (warn log + `next()`)
- Missing `x-twilio-signature` header → 403
- Invalid signature → 403
- Valid signature → `next()`

**Recommended fix:** Write a dedicated unit test that:
1. Imports the real middleware (no mock)
2. Stubs `twilio.validateRequest` to return `true` / `false`
3. Constructs a mock `req` / `res` / `next` to assert each branch

The integration test suite should remove the blanket mock and instead set `SKIP_TWILIO_AUTH=true` in the test environment so the bypass branch is exercised rather than circumvented.

---

### 2.3 `routes/outbound.js` — 0 % across all metrics

The outbound-call route (`POST /outbound/call`) has **no tests at all**. It has two reachable branches: the happy path (202 + `callSid`) and the error path (502).

**Tests needed:**
```
POST /outbound/call
  ✓ returns 202 with callSid on success
  ✓ returns 400 when "to" is not a valid E.164 number
  ✓ returns 400 when webhookUrl is missing
  ✓ returns 502 when TwilioService.makeCall() throws
```

---

### 2.4 `routes/voice.js` — 50 % branches (lines 73–131 uncovered)

The `/voice/respond` handler has four uncovered execution paths:

| Lines | Missing scenario |
|---|---|
| 73–77 | Farewell phrase detected → `buildHangupResponse()` called, session deleted |
| 85–87 | History token budget exceeded → `summariseHistory()` called |
| 96–101 | `claude.respond()` throws → graceful 200 TwiML fallback returned |
| 124–131 | `/voice/status` route — call completion triggers `session.delete()` |

Each of these is a meaningful business-logic branch. The farewell and error-fallback paths in particular would be exercised by real callers immediately.

---

### 2.5 `services/claudeService.js` — `summariseHistory()` untested (lines 60–73)

`summariseHistory()` is the mechanism that prevents context windows from overflowing on long calls. It has two logical branches:

- Empty / missing history → returns `''` immediately (not tested)
- Non-empty history → formats transcript and calls `this.respond()` (not tested)

Both branches are straightforward to cover with the existing client mock pattern used in `claudeService.test.js`.

---

### 2.6 `services/twilioService.js` — `makeCall()` and `validateRequest()` untested (lines 63–86)

`makeCall()` (lines 75–86) is the only async method in `TwilioService` and covers the main outbound-calling flow. It is also the only place that can throw a `TypeError` for missing arguments.

**Tests needed:**
```
makeCall()
  ✓ calls this.client.calls.create with correct params
  ✓ returns the created call object
  ✓ throws TypeError when "to" is missing
  ✓ throws TypeError when "url" is missing
  ✓ propagates errors from Twilio client
```

`validateRequest()` is a thin wrapper around `twilio.validateRequest`. A single test confirming the delegation happens (and that the return value is passed through) is sufficient.

---

### 2.7 `middleware/rateLimiter.js` — sliding-window expiry and `middleware()` untested

Branch coverage is 78 % with one uncovered line (line 63 — the `middleware()` body). Two gaps:

1. **Sliding-window expiry**: The limiter filters out timestamps older than the window, but no test advances the clock (`jest.useFakeTimers`) to verify that expired requests are correctly purged and the limit resets.

2. **`middleware()` express integration**: The `req.body.From` vs `req.ip` fallback, the 429 response, and the `next()` call are untested.

---

### 2.8 `config/index.js` — `validate()` function at 0 % function coverage

`validate()` throws when required environment variables are missing. It is never called in the test suite, so misconfigured deployments cannot be caught by CI.

**Tests needed:**
```
validate()
  ✓ does not throw when all required keys are present
  ✓ throws listing all missing keys
  ✓ throws on a single missing key (e.g. ANTHROPIC_API_KEY)
```

---

## 3. Prioritised Improvement Roadmap

| Priority | File / Area | Impact | Effort |
|---|---|---|---|
| **P0** | `sessionService.js` — all methods | Critical data-loss risk; core stateful component | Medium (need Redis mock) |
| **P0** | `routes/outbound.js` — entire route | Zero coverage; user-facing API | Low |
| **P1** | `middleware/twilioAuth.js` — all branches | Security control — wrong result = unauthenticated webhooks accepted | Low |
| **P1** | `routes/voice.js` — farewell + error fallback | User-visible behaviour; error paths most likely to regress | Low |
| **P1** | `routes/voice.js` — `/status` route | Session-leak risk if cleanup never runs | Low |
| **P2** | `services/claudeService.js` — `summariseHistory()` | Long-call stability | Low |
| **P2** | `services/twilioService.js` — `makeCall()` | Outbound-call reliability | Low |
| **P2** | `middleware/rateLimiter.js` — expiry + middleware | DoS protection correctness | Low |
| **P3** | `config/index.js` — `validate()` | Catches misconfigured deploys in CI | Low |

---

## 4. Recommended Structural Improvements

### 4.1 Introduce a test helper for session stubs

Repeated `jest.fn()` setup for `SessionService` is currently duplicated. Extract it:

```js
// tests/helpers/sessionStub.js
function makeSessionStub(overrides = {}) {
  return {
    get: jest.fn().mockResolvedValue(null),
    set: jest.fn().mockResolvedValue(),
    delete: jest.fn().mockResolvedValue(),
    appendMessage: jest.fn().mockResolvedValue(),
    historyLength: jest.fn().mockResolvedValue(0),
    connect: jest.fn(),
    ...overrides,
  };
}
module.exports = { makeSessionStub };
```

### 4.2 Add `ioredis-mock` for SessionService unit tests

```bash
npm install --save-dev ioredis-mock
```

This lets `SessionService` tests use a real in-memory Redis client without infrastructure:

```js
const RedisMock = require('ioredis-mock');
const svc = new SessionService(new RedisMock());
svc._connected = true;
```

### 4.3 Separate unit and integration CI jobs

Run `tests/unit` on every push (fast, no infrastructure), and `tests/integration` in a separate job that spins up Redis via Docker. This prevents flaky infrastructure tests from blocking unit-test feedback.

### 4.4 Increase coverage thresholds progressively

Once P0 and P1 gaps are closed, the global thresholds can be raised:

```json
"coverageThreshold": {
  "global": { "statements": 80, "branches": 75, "functions": 80, "lines": 80 },
  "./src/services/sessionService.js": {
    "statements": 90, "branches": 85, "functions": 90, "lines": 90
  }
}
```

Per-file thresholds for critical modules (session, auth middleware) ensure future contributors cannot silently drop coverage in sensitive areas.

### 4.5 Add a `validate()` smoke-test to the CI pipeline

Even before full unit tests for `config/validate()` are written, a small CI step that runs the server with missing env vars and confirms a non-zero exit code provides meaningful regression protection.

---

## 5. Quick-win Test Stubs

The following test stubs can be copy-pasted as starting points:

```js
// tests/unit/sessionService.test.js
const SessionService = require('../../src/services/sessionService');

function makeRedis(overrides = {}) {
  return {
    get: jest.fn().mockResolvedValue(null),
    setEx: jest.fn().mockResolvedValue('OK'),
    del: jest.fn().mockResolvedValue(1),
    connect: jest.fn(),
    quit: jest.fn(),
    on: jest.fn(),
    ...overrides,
  };
}

describe('SessionService', () => {
  let svc, redis;
  beforeEach(() => {
    redis = makeRedis();
    svc = new SessionService(redis);
    svc._connected = true;
  });

  describe('get()', () => {
    it('returns null on cache miss', async () => { /* TODO */ });
    it('parses and returns stored JSON', async () => { /* TODO */ });
    it('returns null and logs warning on corrupt JSON', async () => { /* TODO */ });
  });

  describe('set()', () => {
    it('calls setEx with the correct TTL', async () => { /* TODO */ });
  });

  describe('appendMessage()', () => {
    it('creates a new session if none exists', async () => { /* TODO */ });
    it('appends to an existing session history', async () => { /* TODO */ });
  });

  describe('delete()', () => {
    it('calls del with the namespaced key', async () => { /* TODO */ });
  });

  describe('historyLength()', () => {
    it('returns 0 for a missing session', async () => { /* TODO */ });
    it('returns the correct turn count', async () => { /* TODO */ });
  });
});
```

---

*End of analysis. All figures are from a real `jest --coverage` run on this codebase.*
