const ClaudeService = require('../../src/services/claudeService');

// Minimal mock of the Anthropic client
function makeClient(overrides = {}) {
  return {
    messages: {
      create: jest.fn().mockResolvedValue({
        content: [{ type: 'text', text: 'Hello from Claude!' }],
        usage: { input_tokens: 10, output_tokens: 5 },
        stop_reason: 'end_turn',
      }),
      ...overrides,
    },
  };
}

describe('ClaudeService', () => {
  describe('respond()', () => {
    it('returns text from the first text block', async () => {
      const client = makeClient();
      const svc = new ClaudeService(client);

      const result = await svc.respond('Hi');

      expect(result).toBe('Hello from Claude!');
      expect(client.messages.create).toHaveBeenCalledTimes(1);
    });

    it('passes history as preceding messages', async () => {
      const client = makeClient();
      const svc = new ClaudeService(client);
      const history = [{ role: 'user', content: 'First message' }];

      await svc.respond('Second message', history);

      const callArgs = client.messages.create.mock.calls[0][0];
      expect(callArgs.messages).toHaveLength(2);
      expect(callArgs.messages[0]).toEqual(history[0]);
    });

    it('throws TypeError for non-string userMessage', async () => {
      const svc = new ClaudeService(makeClient());
      await expect(svc.respond(null)).rejects.toThrow(TypeError);
      await expect(svc.respond(123)).rejects.toThrow(TypeError);
    });

    it('throws TypeError for empty userMessage', async () => {
      const svc = new ClaudeService(makeClient());
      // empty string is falsy – should also throw
      await expect(svc.respond('')).rejects.toThrow(TypeError);
    });

    it('concatenates multiple text blocks', async () => {
      const client = makeClient();
      client.messages.create.mockResolvedValueOnce({
        content: [
          { type: 'text', text: 'Part one. ' },
          { type: 'text', text: 'Part two.' },
        ],
        usage: {},
        stop_reason: 'end_turn',
      });
      const svc = new ClaudeService(client);
      const result = await svc.respond('Hello');
      expect(result).toBe('Part one. Part two.');
    });

    it('throws when Claude returns an empty content array', async () => {
      const client = makeClient();
      client.messages.create.mockResolvedValueOnce({
        content: [],
        usage: {},
        stop_reason: 'end_turn',
      });
      const svc = new ClaudeService(client);
      await expect(svc.respond('Hello')).rejects.toThrow('Empty response');
    });
  });

  describe('estimateTokens()', () => {
    it('returns 0 for empty history', () => {
      const svc = new ClaudeService(makeClient());
      expect(svc.estimateTokens([])).toBe(0);
    });

    it('approximates token count by character length', () => {
      const svc = new ClaudeService(makeClient());
      // 8 chars → ceil(8/4) = 2
      const history = [{ role: 'user', content: '12345678' }];
      expect(svc.estimateTokens(history)).toBe(2);
    });

    it('sums tokens across multiple turns', () => {
      const svc = new ClaudeService(makeClient());
      const history = [
        { role: 'user', content: '1234' },      // 1 token
        { role: 'assistant', content: '12345678' }, // 2 tokens
      ];
      expect(svc.estimateTokens(history)).toBe(3);
    });
  });

  // NOTE: summariseHistory() is NOT tested here – gap identified in coverage analysis
});
