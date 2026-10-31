import cors from 'cors';
import express from 'express';
import { MemoryEngine } from './engine.js';
import { readProcesses, readSystemMemory } from './linux.js';
const app = express();
const engine = new MemoryEngine();
const clients = new Set();
const history = [];
const events = [];
const maxHistory = 120;
app.use(cors());
app.use(express.json({ limit: '16kb' }));
function record(type, data) {
    const event = { type, timestamp: Date.now(), data };
    events.unshift(event);
    events.splice(100);
    for (const client of clients)
        client.write(`event: ${type}\ndata: ${JSON.stringify(event)}\n\n`);
}
engine.on('allocation', (allocation) => record('allocation', allocation));
engine.on('engine', (status) => record('engine', status));
app.get('/api/health', (_req, res) => res.json({ ok: true, platform: process.platform, engine: engine.available, timestamp: Date.now() }));
app.get('/api/system/memory', async (_req, res) => res.json(await readSystemMemory()));
app.get('/api/processes', async (_req, res) => res.json(await readProcesses()));
app.get('/api/allocations', async (_req, res) => res.json(await engine.snapshot()));
app.get('/api/allocations/history', (_req, res) => res.json({ events }));
app.get('/api/events', (req, res) => { res.setHeader('Content-Type', 'text/event-stream'); res.setHeader('Cache-Control', 'no-cache'); res.setHeader('Connection', 'keep-alive'); res.flushHeaders(); clients.add(res); res.write(`event: connected\ndata: ${JSON.stringify({ timestamp: Date.now(), engine: engine.available })}\n\n`); req.on('close', () => clients.delete(res)); });
app.post('/api/allocations', async (req, res) => {
    const { operation, size, count = 1 } = req.body ?? {};
    const maxBytes = 256 * 1024 * 1024;
    const invalidSize = !Number.isSafeInteger(size) || size < 1 || size > maxBytes;
    const invalidCount = !Number.isSafeInteger(count) || count < 1 || count > 1000000;
    if (!['malloc', 'calloc'].includes(operation) || invalidSize || (operation === 'calloc' && (invalidCount || count > maxBytes / size)))
        return res.status(400).json({ error: 'Invalid operation or size. Maximum allocation is 256 MiB.' });
    const result = await engine.command(operation === 'calloc' ? `calloc ${count} ${size}` : `malloc ${size}`);
    if (!result.ok)
        return res.status(409).json(result);
    record('allocation', result.allocation);
    res.status(201).json(result);
});
app.patch('/api/allocations/:id', async (req, res) => {
    const id = Number(req.params.id);
    const { size } = req.body ?? {};
    if (!Number.isSafeInteger(id) || !Number.isSafeInteger(size) || size < 1 || size > 256 * 1024 * 1024)
        return res.status(400).json({ error: 'Invalid allocation id or size' });
    const result = await engine.command(`realloc ${id} ${size}`);
    if (!result.ok)
        return res.status(404).json(result);
    record('allocation', result.allocation);
    res.json(result);
});
app.delete('/api/allocations/:id', async (req, res) => {
    const id = Number(req.params.id);
    if (!Number.isSafeInteger(id))
        return res.status(400).json({ error: 'Invalid allocation id' });
    const result = await engine.command(`free ${id}`);
    if (!result.ok)
        return res.status(404).json(result);
    record('allocation', result.allocation);
    res.json(result);
});
app.get('/api/metrics', async (_req, res) => { const [memory, allocation] = await Promise.all([readSystemMemory(), engine.snapshot()]); const point = { timestamp: Date.now(), memory, allocation: allocation.metrics }; history.push(point); history.splice(0, Math.max(0, history.length - maxHistory)); res.json(point); });
app.get('/api/analytics', (_req, res) => res.json({ history }));
app.get('/api/leaks', async (_req, res) => { const state = await engine.snapshot(); const threshold = Date.now() - 5 * 60 * 1000; const potential = state.allocations.filter((item) => item.status === 'active' && item.createdAt < threshold); res.json({ active: state.allocations.filter((item) => item.status === 'active'), potential, explanation: 'Potential leaks are active allocations older than five minutes. Active does not mean confirmed leak.' }); });
const port = Number(process.env.PORT ?? 4000);
const interval = setInterval(async () => { const [memory, allocation] = await Promise.all([readSystemMemory(), engine.snapshot()]); const point = { timestamp: Date.now(), memory, allocation: allocation.metrics }; history.push(point); history.splice(0, Math.max(0, history.length - maxHistory)); record('metrics', point); }, 1000);
const server = app.listen(port, () => console.log(`Memory monitor API listening on http://localhost:${port}`));
function shutdown() { clearInterval(interval); for (const client of clients)
    client.end(); engine.close(); server.close(() => process.exit(0)); }
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
export { app };
