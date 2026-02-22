const twilio = require('twilio');
const { config } = require('../config');
const logger = require('../utils/logger');

/**
 * Express middleware that validates incoming Twilio webhook signatures.
 * Requests that fail validation are rejected with 403.
 *
 * Bypass in development by setting SKIP_TWILIO_AUTH=true.
 */
function twilioAuth(req, res, next) {
  if (process.env.SKIP_TWILIO_AUTH === 'true') {
    logger.warn('Twilio webhook signature validation is DISABLED');
    return next();
  }

  const signature = req.headers['x-twilio-signature'];
  if (!signature) {
    logger.warn('Missing Twilio signature header');
    return res.status(403).json({ error: 'Missing Twilio signature' });
  }

  const url = `${req.protocol}://${req.get('host')}${req.originalUrl}`;
  const isValid = twilio.validateRequest(
    config.twilio.authToken,
    signature,
    url,
    req.body
  );

  if (!isValid) {
    logger.warn('Invalid Twilio signature', { url });
    return res.status(403).json({ error: 'Invalid Twilio signature' });
  }

  next();
}

module.exports = twilioAuth;
