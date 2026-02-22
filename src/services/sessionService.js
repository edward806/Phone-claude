const { createClient } = require('redis');
const { config } = require('../config');
const logger = require('../utils/logger');

const SESSION_PREFIX = 'phone:session:';

class SessionService {
  constructor(redisClient) {
    this._client = redisClient || null;
    this._connected = false;
  }

  async connect() {
    if (this._connected) return;

    if (!this._client) {
      this._client = createClient({ url: config.redis.url });
      this._client.on('error', (err) =>
        logger.error('Redis error', { error: err.message })
      );
    }

    await this._client.connect();
    this._connected = true;
    logger.info('Connected to Redis');
  }

  async disconnect() {
    if (!this._connected) return;
    await this._client.quit();
    this._connected = false;
  }

  _key(callSid) {
    return `${SESSION_PREFIX}${callSid}`;
  }

  /**
   * Retrieve session data for a call.
   * Returns null when no session exists.
   * @param {string} callSid
   * @returns {Promise<{history: Array, metadata: object}|null>}
   */
  async get(callSid) {
    const raw = await this._client.get(this._key(callSid));
    if (!raw) return null;

    try {
      return JSON.parse(raw);
    } catch {
      logger.warn('Corrupt session data', { callSid });
      return null;
    }
  }

  /**
   * Persist session data for a call.
   * @param {string} callSid
   * @param {{history: Array, metadata: object}} session
   */
  async set(callSid, session) {
    await this._client.setEx(
      this._key(callSid),
      config.redis.sessionTtl,
      JSON.stringify(session)
    );
  }

  /**
   * Append a new message turn to an existing session (or create one).
   * @param {string} callSid
   * @param {{role:string, content:string}} message
   */
  async appendMessage(callSid, message) {
    const session = (await this.get(callSid)) || {
      history: [],
      metadata: { createdAt: new Date().toISOString() },
    };
    session.history.push(message);
    await this.set(callSid, session);
  }

  /**
   * Delete a session (e.g. when call ends).
   * @param {string} callSid
   */
  async delete(callSid) {
    await this._client.del(this._key(callSid));
  }

  /**
   * Return the number of turns in a session's history.
   * @param {string} callSid
   * @returns {Promise<number>}
   */
  async historyLength(callSid) {
    const session = await this.get(callSid);
    return session ? session.history.length : 0;
  }
}

module.exports = SessionService;
