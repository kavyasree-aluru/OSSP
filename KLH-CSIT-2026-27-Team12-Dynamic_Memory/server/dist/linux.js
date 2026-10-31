import { readFile } from 'node:fs/promises';
import { freemem, totalmem } from 'node:os';
function fields(text) { return Object.fromEntries(text.split('\n').filter(Boolean).map((line) => { const [key, value] = line.split(':'); return [key, Number.parseInt(value.trim(), 10) * 1024]; })); }
export async function readSystemMemory() {
    if (process.platform !== 'linux') {
        const totalBytes = totalmem();
        const availableBytes = freemem();
        const usedBytes = Math.max(0, totalBytes - availableBytes);
        const processResidentBytes = process.memoryUsage().rss;
        return {
            platform: process.platform,
            available: true,
            timestamp: Date.now(),
            totalBytes,
            usedBytes,
            availableBytes,
            freeBytes: availableBytes,
            usedPercent: totalBytes ? usedBytes / totalBytes * 100 : 0,
            processResidentBytes,
        };
    }
    try {
        const info = fields(await readFile('/proc/meminfo', 'utf8'));
        const status = await readFile(`/proc/${process.pid}/status`, 'utf8');
        const processFields = Object.fromEntries(status.split('\n').filter((line) => line.startsWith('VmRSS:') || line.startsWith('VmSize:')).map((line) => { const [key, value] = line.split(':'); return [key, Number.parseInt(value, 10) * 1024]; }));
        const totalBytes = info.MemTotal ?? 0;
        const availableBytes = info.MemAvailable ?? info.MemFree ?? 0;
        const usedBytes = Math.max(0, totalBytes - availableBytes);
        return { platform: 'linux', available: true, timestamp: Date.now(), totalBytes, usedBytes, availableBytes, freeBytes: info.MemFree, cachedBytes: (info.Cached ?? 0) + (info.Buffers ?? 0), swapTotalBytes: info.SwapTotal, swapFreeBytes: info.SwapFree, usedPercent: totalBytes ? usedBytes / totalBytes * 100 : 0, processResidentBytes: processFields.VmRSS, processVirtualBytes: processFields.VmSize };
    }
    catch (error) {
        return { platform: 'linux', available: false, timestamp: Date.now(), error: error instanceof Error ? error.message : 'Unable to read /proc' };
    }
}
export async function readProcesses() {
    if (process.platform !== 'linux')
        return { available: false, processes: [], error: 'Linux process monitoring is unavailable on this host' };
    const { readdir } = await import('node:fs/promises');
    const entries = await readdir('/proc');
    const processes = await Promise.all(entries.filter((entry) => /^\d+$/.test(entry)).map(async (pid) => {
        try {
            const status = await readFile(`/proc/${pid}/status`, 'utf8');
            const get = (key) => status.match(new RegExp(`^${key}:\\s+(.+)$`, 'm'))?.[1] ?? '';
            return { pid: Number(pid), name: get('Name'), status: get('State'), residentBytes: Number.parseInt(get('VmRSS')) * 1024 || 0, virtualBytes: Number.parseInt(get('VmSize')) * 1024 || 0 };
        }
        catch {
            return null;
        }
    }));
    return { available: true, processes: processes.filter(Boolean).sort((a, b) => (b?.residentBytes ?? 0) - (a?.residentBytes ?? 0)) };
}
