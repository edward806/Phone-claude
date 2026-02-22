const { config } = require('../config');
const logger = require('../utils/logger');

/**
 * Simple in-memory sliding-window rate limiter.
 *
 * In production this should be backed by Redis so that limits are
 * shared across multiple server instances, but for simplicity this
 * implementation stores state in a Map.
 */
class RateLimiter {
  /**
   * @param {object} opts
   * @param {number} opts.windowMs      Time window in ms
   * @param {number} opts.maxRequests   Max requests per window per key
   */
  constructor({ windowMs, maxRequests } = config.rateLimiting) {
    this.windowMs = windowMs;
    this.maxRequests = maxRequests;
    /** @type {Map<string, number[]>} */
    this._store = new Map();
  }

  /**
   * Check whether a key is within the rate limit.
   * Automatically removes timestamps outside the current window.
   * @param {string} key   e.g. caller phone number
   * @returns {boolean}    true if the request should be allowed
   */
  isAllowed(key) {
    const now = Date.now();
    const windowStart = now - this.windowMs;

    const timestamps = (this._store.get(key) || []).filter(
      (ts) => ts > windowStart
    );

    if (timestamps.length >= this.maxRequests) {
      logger.warn('Rate limit exceeded', { key });
      return false;
    }

    timestamps.push(now);
    this._store.set(key, timestamps);
    return true;
  }

  /**
   * Reset tracking for a specific key (e.g. for testing).
   * @param {string} key
   */
  reset(key) {
    this._store.delete(key);
  }

  /**
   * Express middleware that limits by caller phone number (req.body.From).
   */
  middleware() {
    return (req, res, next) => {
      const key = req.body?.From || req.ip;
      if (!this.isAllowed(key)) {
        return res.status(429).json({ error: 'Too many requests' });
      }
      next();
    };
  }
}

module.exports = RateLimiter;
