const express = require('express');
const router = express.Router();
const ClaudeService = require('../services/claudeService');
const SessionService = require('../services/sessionService');
const TwilioService = require('../services/twilioService');
const twilioAuth = require('../middleware/twilioAuth');
const RateLimiter = require('../middleware/rateLimiter');
const { bodyValidator, twilioWebhookSchema } = require('../utils/validators');
const { config } = require('../config');
const logger = require('../utils/logger');

const claude = new ClaudeService();
const session = new SessionService();
const twilioSvc = new TwilioService();
const limiter = new RateLimiter();

const MAX_HISTORY_TOKENS = 2000;

/**
 * POST /voice/incoming
 * Twilio calls this when a new inbound call arrives.
 */
router.post(
  '/incoming',
  twilioAuth,
  limiter.middleware(),
  bodyValidator(twilioWebhookSchema),
  async (req, res) => {
    const { CallSid, From } = req.validatedBody;

    logger.info('Inbound call received', { CallSid, From });

    await session.set(CallSid, {
      history: [],
      metadata: { from: From, startedAt: new Date().toISOString() },
    });

    const twiml = twilioSvc.buildSpeechResponse(
      'Hello! I\'m Claude, your AI assistant. How can I help you today?',
      { action: '/voice/respond', gather: true }
    );

    res.type('text/xml').send(twiml);
  }
);

/**
 * POST /voice/respond
 * Twilio posts here with the caller's transcribed speech.
 */
router.post(
  '/respond',
  twilioAuth,
  limiter.middleware(),
  bodyValidator(twilioWebhookSchema),
  async (req, res) => {
    const { CallSid, SpeechResult, Confidence } = req.validatedBody;

    logger.info('Speech received', { CallSid, Confidence });

    const userSpeech = SpeechResult?.trim();

    if (!userSpeech) {
      const twiml = twilioSvc.buildSpeechResponse(
        "I'm sorry, I didn't catch that. Could you please repeat?",
        { action: '/voice/respond', gather: true }
      );
      return res.type('text/xml').send(twiml);
    }

    // Check for farewell intent
    if (isFarewell(userSpeech)) {
      await session.delete(CallSid);
      const twiml = twilioSvc.buildHangupResponse(
        'Thank you for calling. Have a great day! Goodbye.'
      );
      return res.type('text/xml').send(twiml);
    }

    const existingSession = await session.get(CallSid);
    let history = existingSession?.history || [];

    // Summarise if context is getting long
    if (claude.estimateTokens(history) > MAX_HISTORY_TOKENS) {
      logger.info('Summarising history', { CallSid, turns: history.length });
      const summary = await claude.summariseHistory(history);
      history = [{ role: 'assistant', content: `[Summary of prior conversation: ${summary}]` }];
    }

    history.push({ role: 'user', content: userSpeech });

    let reply;
    try {
      reply = await claude.respond(userSpeech, history.slice(0, -1));
    } catch (err) {
      logger.error('Claude error', { error: err.message, CallSid });
      const twiml = twilioSvc.buildSpeechResponse(
        "I'm having trouble processing that right now. Please try again.",
        { action: '/voice/respond', gather: true }
      );
      return res.type('text/xml').send(twiml);
    }

    history.push({ role: 'assistant', content: reply });
    await session.set(CallSid, {
      history,
      metadata: existingSession?.metadata || {},
    });

    const twiml = twilioSvc.buildSpeechResponse(reply, {
      action: '/voice/respond',
      gather: true,
    });

    res.type('text/xml').send(twiml);
  }
);

/**
 * POST /voice/status
 * Twilio calls this with call status updates.
 */
router.post('/status', twilioAuth, async (req, res) => {
  const { CallSid, CallStatus } = req.body;
  logger.info('Call status update', { CallSid, CallStatus });

  if (['completed', 'busy', 'no-answer', 'failed', 'canceled'].includes(CallStatus)) {
    await session.delete(CallSid);
  }

  res.sendStatus(204);
});

/**
 * Heuristic check for call-ending phrases.
 * @param {string} text
 * @returns {boolean}
 */
function isFarewell(text) {
  const lower = text.toLowerCase();
  return ['goodbye', 'bye', 'end call', 'hang up', 'stop', 'quit', 'exit'].some(
    (phrase) => lower.includes(phrase)
  );
}

module.exports = router;
module.exports.isFarewell = isFarewell;
