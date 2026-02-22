const twilio = require('twilio');
const { config } = require('../config');
const logger = require('../utils/logger');

const VoiceResponse = twilio.twiml.VoiceResponse;

class TwilioService {
  constructor(client) {
    this.client =
      client ||
      twilio(config.twilio.accountSid, config.twilio.authToken);
  }

  /**
   * Build a TwiML response that reads text aloud and optionally gathers more speech.
   * @param {string} text           Text to say
   * @param {object} opts
   * @param {boolean} opts.gather   Whether to add a <Gather> for follow-up input
   * @param {string}  opts.action   Webhook URL for gathered speech
   * @param {string}  opts.voice    Twilio voice identifier
   * @returns {string}              TwiML XML string
   */
  buildSpeechResponse(text, { gather = true, action = '/voice/respond', voice = 'Polly.Joanna' } = {}) {
    const twiml = new VoiceResponse();

    if (gather) {
      const g = twiml.gather({
        input: 'speech',
        action,
        method: 'POST',
        speechTimeout: 'auto',
        language: 'en-US',
      });
      g.say({ voice }, text);
    } else {
      twiml.say({ voice }, text);
    }

    return twiml.toString();
  }

  /**
   * Build a TwiML response that ends the call with a farewell message.
   * @param {string} message
   * @returns {string}
   */
  buildHangupResponse(message = 'Thank you for calling. Goodbye!') {
    const twiml = new VoiceResponse();
    twiml.say(message);
    twiml.hangup();
    return twiml.toString();
  }

  /**
   * Validate that an incoming request originated from Twilio.
   * @param {string} authToken
   * @param {string} signature   X-Twilio-Signature header
   * @param {string} url         Full request URL
   * @param {object} params      POST body params
   * @returns {boolean}
   */
  validateRequest(authToken, signature, url, params) {
    return twilio.validateRequest(authToken, signature, url, params);
  }

  /**
   * Initiate an outbound call.
   * @param {string} to   Destination phone number
   * @param {string} url  TwiML URL to execute when the call connects
   * @returns {Promise<object>}
   */
  async makeCall(to, url) {
    if (!to || !url) {
      throw new TypeError('to and url are required');
    }

    logger.info('Initiating outbound call', { to });

    const call = await this.client.calls.create({
      to,
      from: config.twilio.phoneNumber,
      url,
    });

    logger.info('Outbound call created', { callSid: call.sid });
    return call;
  }
}

module.exports = TwilioService;
