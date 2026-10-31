import { spawn } from 'node:child_process';
import { EventEmitter } from 'node:events';
import { existsSync } from 'node:fs';
import path from 'node:path';
export class MemoryEngine extends EventEmitter {
    child;
    pending = [];
    buffer = '';
    state = { metrics: { totalAllocations: 0, totalDeallocations: 0, activeAllocations: 0, totalAllocatedBytes: 0, totalFreedBytes: 0, activeBytes: 0 }, allocations: [] };
    available;
    constructor() {
        super();
        const binary = path.resolve(process.cwd(), '..', 'native', 'memory_engine');
        this.available = process.platform === 'linux' && existsSync(binary);
        if (this.available) {
            this.child = spawn(binary);
            this.child.stdout.on('data', (chunk) => this.consume(chunk.toString()));
            this.child.on('close', () => this.emit('engine', { available: false, message: 'Native engine stopped' }));
        }
    }
    consume(chunk) {
        this.buffer += chunk;
        const lines = this.buffer.split('\n');
        this.buffer = lines.pop() ?? '';
        for (const line of lines) {
            if (!line.trim())
                continue;
            const result = JSON.parse(line);
            const resolve = this.pending.shift();
            if (result.ok && result.metrics && result.allocation) {
                const existing = this.state.allocations.findIndex((item) => item.id === result.allocation.id);
                if (existing >= 0)
                    this.state.allocations[existing] = result.allocation;
                else
                    this.state.allocations.unshift(result.allocation);
                this.state.metrics = { ...this.state.metrics, ...result.metrics };
                this.emit('allocation', result.allocation);
            }
            if (result.ok && result.allocations)
                this.state = { metrics: result.metrics, allocations: result.allocations };
            resolve?.(result);
        }
    }
    command(command) {
        if (!this.child)
            return Promise.resolve({ ok: false, error: 'Linux native engine is unavailable on this host' });
        return new Promise((resolve) => { this.pending.push(resolve); this.child.stdin.write(`${command}\n`); });
    }
    async snapshot() {
        if (this.child)
            await this.command('state');
        return this.state;
    }
    close() { this.child?.stdin.end(); }
}
