/**
 * Integration tests for the /voice routes.
 *
 * These tests are intentionally incomplete to illustrate coverage gaps.
 * They stub out external dependencies (Claude, Redis, Twilio auth) so
 * the suite can run without live credentials.
 */

const request = require('supertest');
const express = require('express');

// ── Stub config before any service module loads ──────────────────────────────
jest.mock('../../src/config', () => ({
  config: {
    anthropic: { apiKey: 'test', model: 'claude-opus-4-6', maxTokens: 1024, systemPrompt: 'test' },
    twilio: { accountSid: 'ACtest', authToken: 'authtest', phoneNumber: '+10000000000' },
    redis: { url: 'redis://localhost', sessionTtl: 3600 },
    rateLimiting: { windowMs: 60_000, maxRequests: 100 },
  },
  validate: jest.fn(),
}));

// ── Stub Twilio auth so all requests pass ────────────────────────────────────
jest.mock('../../src/middleware/twilioAuth', () => (req, res, next) => next());

// ── Stub SessionService ──────────────────────────────────────────────────────
const mockSession = {
  get: jest.fn(),
  set: jest.fn(),
  delete: jest.fn(),
  connect: jest.fn(),
};
jest.mock('../../src/services/sessionService', () => jest.fn(() => mockSession));

// ── Stub ClaudeService ───────────────────────────────────────────────────────
const mockClaude = {
  respond: jest.fn().mockResolvedValue('This is a Claude reply.'),
  estimateTokens: jest.fn().mockReturnValue(10),
  summariseHistory: jest.fn().mockResolvedValue('Summary.'),
};
jest.mock('../../src/services/claudeService', () => jest.fn(() => mockClaude));

// ── Build the app without starting a server ──────────────────────────────────
let app;
beforeAll(() => {
  const voiceRoutes = require('../../src/routes/voice');
  app = express();
  app.use(express.urlencoded({ extended: false }));
  app.use(express.json());
  app.use('/voice', voiceRoutes);
});

beforeEach(() => {
  jest.clearAllMocks();
  mockSession.get.mockResolvedValue(null);
  mockSession.set.mockResolvedValue();
  mockSession.delete.mockResolvedValue();
});

// ── Helper: build a minimal Twilio-style POST body ───────────────────────────
function twilioBody(overrides = {}) {
  return {
    CallSid: 'CA' + 'a'.repeat(32),
    From: '+15550001111',
    To: '+15559999999',
    CallStatus: 'in-progress',
    ...overrides,
  };
}

// ── /voice/incoming ──────────────────────────────────────────────────────────
describe('POST /voice/incoming', () => {
  it('responds with TwiML containing a greeting', async () => {
    const res = await request(app)
      .post('/voice/incoming')
      .send(twilioBody())
      .expect(200);

    expect(res.headers['content-type']).toMatch(/xml/);
    expect(res.text).toContain("Hello");
    expect(mockSession.set).toHaveBeenCalledTimes(1);
  });

  it('returns 400 for an invalid CallSid', async () => {
    await request(app)
      .post('/voice/incoming')
      .send(twilioBody({ CallSid: 'INVALID' }))
      .expect(400);
  });
});

// ── /voice/respond ───────────────────────────────────────────────────────────
describe('POST /voice/respond', () => {
  it('calls Claude and returns its reply in TwiML', async () => {
    mockSession.get.mockResolvedValue({ history: [], metadata: {} });

    const res = await request(app)
      .post('/voice/respond')
      .send(twilioBody({ SpeechResult: 'What is the capital of France?' }))
      .expect(200);

    expect(res.text).toContain('This is a Claude reply.');
    expect(mockClaude.respond).toHaveBeenCalledTimes(1);
  });

  it('prompts caller to repeat when SpeechResult is empty', async () => {
    const res = await request(app)
      .post('/voice/respond')
      .send(twilioBody({ SpeechResult: '' }))
      .expect(200);

    expect(res.text).toContain("didn't catch that");
    expect(mockClaude.respond).not.toHaveBeenCalled();
  });

  // MISSING TESTS (coverage gaps):
  // - Farewell detection triggers hangup TwiML
  // - History summarisation is invoked when token budget exceeded
  // - Claude API error causes graceful fallback response
  // - Session is persisted with updated history after successful reply
});

// ── /voice/status ────────────────────────────────────────────────────────────
// ENTIRELY MISSING – the /voice/status route has zero test coverage.
