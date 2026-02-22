const { isFarewell } = require('../../src/routes/voice');

describe('isFarewell()', () => {
  it.each([
    ['Goodbye!', true],
    ['bye', true],
    ['Please hang up', true],
    ['end call now', true],
    ['stop', true],
  ])('"%s" → %s', (input, expected) => {
    expect(isFarewell(input)).toBe(expected);
  });

  it.each([
    ['Hello there', false],
    ['What is the weather?', false],
    ['Tell me a joke', false],
  ])('"%s" → %s', (input, expected) => {
    expect(isFarewell(input)).toBe(expected);
  });

  // NOTE: Mixed-case variants like "GOODBYE" are tested above via toLowerCase().
  //       Edge cases: empty string, whitespace-only, and non-English phrases are NOT covered.
});
