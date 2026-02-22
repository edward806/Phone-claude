require('dotenv').config();

const config = {
  port: parseInt(process.env.PORT, 10) || 3000,
  anthropic: {
    apiKey: process.env.ANTHROPIC_API_KEY,
    model: process.env.CLAUDE_MODEL || 'claude-opus-4-6',
    maxTokens: parseInt(process.env.MAX_TOKENS, 10) || 1024,
    systemPrompt:
      process.env.SYSTEM_PROMPT ||
      'You are a helpful assistant responding via phone call. Keep responses concise and clear.',
  },
  twilio: {
    accountSid: process.env.TWILIO_ACCOUNT_SID,
    authToken: process.env.TWILIO_AUTH_TOKEN,
    phoneNumber: process.env.TWILIO_PHONE_NUMBER,
  },
  redis: {
    url: process.env.REDIS_URL || 'redis://localhost:6379',
    sessionTtl: parseInt(process.env.SESSION_TTL, 10) || 3600, // seconds
  },
  rateLimiting: {
    windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS, 10) || 60_000,
    maxRequests: parseInt(process.env.RATE_LIMIT_MAX, 10) || 20,
  },
};

function validate(cfg) {
  const required = [
    ['anthropic.apiKey', cfg.anthropic.apiKey],
    ['twilio.accountSid', cfg.twilio.accountSid],
    ['twilio.authToken', cfg.twilio.authToken],
    ['twilio.phoneNumber', cfg.twilio.phoneNumber],
  ];

  const missing = required
    .filter(([, val]) => !val)
    .map(([key]) => key);

  if (missing.length > 0) {
    throw new Error(`Missing required config keys: ${missing.join(', ')}`);
  }
}

module.exports = { config, validate };
