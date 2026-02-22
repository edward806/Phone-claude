const Joi = require('joi');

/**
 * Validate an incoming Twilio voice webhook payload.
 */
const twilioWebhookSchema = Joi.object({
  CallSid: Joi.string().pattern(/^CA[a-f0-9]{32}$/).required(),
  From: Joi.string().required(),
  To: Joi.string().required(),
  CallStatus: Joi.string()
    .valid('queued', 'ringing', 'in-progress', 'completed', 'busy', 'no-answer', 'failed', 'canceled')
    .required(),
  SpeechResult: Joi.string().allow('').optional(),
  Confidence: Joi.number().min(0).max(1).optional(),
}).unknown(true); // Twilio sends many extra fields

/**
 * Validate a request to initiate an outbound call.
 */
const outboundCallSchema = Joi.object({
  to: Joi.string()
    .pattern(/^\+[1-9]\d{6,14}$/)
    .required()
    .messages({
      'string.pattern.base': '"to" must be a valid E.164 phone number',
    }),
  webhookUrl: Joi.string().uri().required(),
});

/**
 * @param {object} schema  A Joi schema
 * @param {object} data
 * @returns {{ value: object, error: Joi.ValidationError|undefined }}
 */
function validate(schema, data) {
  return schema.validate(data, { abortEarly: false });
}

/**
 * Express middleware that validates req.body against the given schema.
 * Responds 400 with validation errors on failure.
 */
function bodyValidator(schema) {
  return (req, res, next) => {
    const { error, value } = validate(schema, req.body);
    if (error) {
      return res.status(400).json({
        error: 'Validation failed',
        details: error.details.map((d) => d.message),
      });
    }
    req.validatedBody = value;
    next();
  };
}

module.exports = {
  twilioWebhookSchema,
  outboundCallSchema,
  validate,
  bodyValidator,
};
