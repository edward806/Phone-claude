const Anthropic = require('@anthropic-ai/sdk');
const { config } = require('../config');
const logger = require('../utils/logger');

class ClaudeService {
  constructor(client) {
    this.client = client || new Anthropic({ apiKey: config.anthropic.apiKey });
  }

  /**
   * Send a single-turn message to Claude and return the text response.
   * @param {string} userMessage
   * @param {Array<{role:string, content:string}>} history  Prior conversation turns
   * @returns {Promise<string>}
   */
  async respond(userMessage, history = []) {
    if (!userMessage || typeof userMessage !== 'string') {
      throw new TypeError('userMessage must be a non-empty string');
    }

    const messages = [
      ...history,
      { role: 'user', content: userMessage.trim() },
    ];

    logger.info('Sending message to Claude', { turns: messages.length });

    const response = await this.client.messages.create({
      model: config.anthropic.model,
      max_tokens: config.anthropic.maxTokens,
      system: config.anthropic.systemPrompt,
      messages,
    });

    if (!response.content || response.content.length === 0) {
      throw new Error('Empty response from Claude');
    }

    const text = response.content
      .filter((block) => block.type === 'text')
      .map((block) => block.text)
      .join('');

    logger.info('Received response from Claude', {
      inputTokens: response.usage?.input_tokens,
      outputTokens: response.usage?.output_tokens,
      stopReason: response.stop_reason,
    });

    return text;
  }

  /**
   * Summarise a long conversation into a shorter context string.
   * Used when history grows beyond a token budget.
   * @param {Array<{role:string, content:string}>} history
   * @returns {Promise<string>}
   */
  async summariseHistory(history) {
    if (!Array.isArray(history) || history.length === 0) {
      return '';
    }

    const transcript = history
      .map((m) => `${m.role.toUpperCase()}: ${m.content}`)
      .join('\n');

    const summary = await this.respond(
      `Please summarise the following conversation concisely so it can be used as context:\n\n${transcript}`,
      []
    );

    return summary;
  }

  /**
   * Estimate token count heuristically (4 chars ≈ 1 token).
   * @param {Array<{role:string, content:string}>} history
   * @returns {number}
   */
  estimateTokens(history) {
    const totalChars = history.reduce(
      (sum, m) => sum + (m.content || '').length,
      0
    );
    return Math.ceil(totalChars / 4);
  }
}

module.exports = ClaudeService;
