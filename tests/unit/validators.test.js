const {
  twilioWebhookSchema,
  outboundCallSchema,
  validate,
} = require('../../src/utils/validators');

describe('validators', () => {
  describe('twilioWebhookSchema', () => {
    const validPayload = {
      CallSid: 'CA' + 'a'.repeat(32),
      From: '+15551234567',
      To: '+15559876543',
      CallStatus: 'in-progress',
    };

    it('accepts a valid webhook payload', () => {
      const { error } = validate(twilioWebhookSchema, validPayload);
      expect(error).toBeUndefined();
    });

    it('rejects a payload with a missing CallSid', () => {
      const { error } = validate(twilioWebhookSchema, {
        ...validPayload,
        CallSid: undefined,
      });
      expect(error).toBeDefined();
    });

    it('rejects a malformed CallSid', () => {
      const { error } = validate(twilioWebhookSchema, {
        ...validPayload,
        CallSid: 'INVALID',
      });
      expect(error).toBeDefined();
    });

    it('rejects an invalid CallStatus', () => {
      const { error } = validate(twilioWebhookSchema, {
        ...validPayload,
        CallStatus: 'unknown-status',
      });
      expect(error).toBeDefined();
    });

    it('allows an optional SpeechResult', () => {
      const { error } = validate(twilioWebhookSchema, {
        ...validPayload,
        SpeechResult: 'Hello world',
      });
      expect(error).toBeUndefined();
    });
  });

  describe('outboundCallSchema', () => {
    it('accepts a valid E.164 number and URL', () => {
      const { error } = validate(outboundCallSchema, {
        to: '+14155552671',
        webhookUrl: 'https://example.com/voice/incoming',
      });
      expect(error).toBeUndefined();
    });

    it('rejects a non-E.164 phone number', () => {
      const { error } = validate(outboundCallSchema, {
        to: '5551234567',
        webhookUrl: 'https://example.com/voice/incoming',
      });
      expect(error).toBeDefined();
    });

    it('rejects a missing webhookUrl', () => {
      const { error } = validate(outboundCallSchema, {
        to: '+14155552671',
      });
      expect(error).toBeDefined();
    });
  });

  // NOTE: bodyValidator() middleware is not unit-tested here.
  //       It is partially exercised by route integration tests,
  //       but edge cases (multiple field errors, header set) are not covered.
});
