import { describe, expect, it } from 'vitest';
import { readSystemMemory } from '../src/linux.js';
describe('system memory reader', () => {
    it('returns an explicit platform-aware result', async () => {
        const result = await readSystemMemory();
        expect(result).toHaveProperty('available');
        expect(result).toHaveProperty('timestamp');
        if (process.platform === 'linux')
            expect(result.totalBytes).toBeGreaterThan(0);
        else
            expect(result.available).toBe(false);
    });
});
