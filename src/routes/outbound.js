const express = require('express');
const router = express.Router();
const TwilioService = require('../services/twilioService');
const { bodyValidator, outboundCallSchema } = require('../utils/validators');
const logger = require('../utils/logger');

const twilioSvc = new TwilioService();

/**
 * POST /outbound/call
 * Initiate an outbound call.
 */
router.post('/call', bodyValidator(outboundCallSchema), async (req, res) => {
  const { to, webhookUrl } = req.validatedBody;

  try {
    const call = await twilioSvc.makeCall(to, webhookUrl);
    res.status(202).json({ callSid: call.sid, status: call.status });
  } catch (err) {
    logger.error('Failed to create outbound call', { error: err.message });
    res.status(502).json({ error: 'Failed to initiate call' });
  }
});

module.exports = router;
