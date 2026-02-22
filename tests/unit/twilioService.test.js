const TwilioService = require('../../src/services/twilioService');

describe('TwilioService', () => {
  describe('buildSpeechResponse()', () => {
    it('returns XML containing the text', () => {
      const svc = new TwilioService({ calls: { create: jest.fn() } });
      const xml = svc.buildSpeechResponse('Hello caller');
      expect(xml).toContain('Hello caller');
      expect(xml).toContain('<Response>');
    });

    it('includes a Gather verb by default', () => {
      const svc = new TwilioService({ calls: { create: jest.fn() } });
      const xml = svc.buildSpeechResponse('Pick up');
      expect(xml).toContain('<Gather');
    });

    it('omits Gather when gather=false', () => {
      const svc = new TwilioService({ calls: { create: jest.fn() } });
      const xml = svc.buildSpeechResponse('Farewell', { gather: false });
      expect(xml).not.toContain('<Gather');
      expect(xml).toContain('<Say');
    });
  });

  describe('buildHangupResponse()', () => {
    it('contains a Hangup verb', () => {
      const svc = new TwilioService({ calls: { create: jest.fn() } });
      const xml = svc.buildHangupResponse();
      expect(xml).toContain('<Hangup');
    });

    it('uses the default farewell message', () => {
      const svc = new TwilioService({ calls: { create: jest.fn() } });
      const xml = svc.buildHangupResponse();
      expect(xml).toContain('Thank you for calling');
    });
  });

  // NOTE: makeCall() and validateRequest() are NOT tested.
  //       makeCall() requires integration-level testing with a Twilio mock.
  //       validateRequest() delegates directly to the twilio SDK and needs
  //       signature fixture data to test properly.
});
