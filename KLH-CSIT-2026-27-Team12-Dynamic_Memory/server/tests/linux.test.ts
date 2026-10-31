import { describe, expect, it } from 'vitest';
import { readSystemMemory } from '../src/linux.js';

describe('system memory reader', () => {
  it('returns live host memory readings', async () => {
    const result = await readSystemMemory();
    expect(result).toHaveProperty('available');
    expect(result).toHaveProperty('timestamp');
    expect(result.available).toBe(true);
    expect(result.totalBytes).toBeGreaterThan(0);
    expect(result.usedBytes).toBeGreaterThanOrEqual(0);
    expect(result.availableBytes).toBeGreaterThan(0);
  });
});
