const RateLimiter = require('../../src/middleware/rateLimiter');

describe('RateLimiter', () => {
  describe('isAllowed()', () => {
    it('allows requests under the limit', () => {
      const limiter = new RateLimiter({ windowMs: 60_000, maxRequests: 3 });
      expect(limiter.isAllowed('user1')).toBe(true);
      expect(limiter.isAllowed('user1')).toBe(true);
      expect(limiter.isAllowed('user1')).toBe(true);
    });

    it('blocks requests over the limit', () => {
      const limiter = new RateLimiter({ windowMs: 60_000, maxRequests: 2 });
      limiter.isAllowed('user2');
      limiter.isAllowed('user2');
      expect(limiter.isAllowed('user2')).toBe(false);
    });

    it('tracks different keys independently', () => {
      const limiter = new RateLimiter({ windowMs: 60_000, maxRequests: 1 });
      limiter.isAllowed('a');
      expect(limiter.isAllowed('a')).toBe(false);
      expect(limiter.isAllowed('b')).toBe(true); // 'b' has its own bucket
    });

    it('resets a key correctly', () => {
      const limiter = new RateLimiter({ windowMs: 60_000, maxRequests: 1 });
      limiter.isAllowed('user3');
      expect(limiter.isAllowed('user3')).toBe(false);
      limiter.reset('user3');
      expect(limiter.isAllowed('user3')).toBe(true);
    });
  });

  // NOTE: sliding-window expiry and middleware() are NOT tested – identified as gaps
});
