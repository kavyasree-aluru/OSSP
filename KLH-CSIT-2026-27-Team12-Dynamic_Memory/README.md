# Linux Dynamic Memory Allocation and Memory Monitoring System

A real-time systems programming project that exposes a Linux C allocation engine through an Express API and React dashboard.

## Architecture

- `native/`: C11 allocation tracker using `malloc`, `calloc`, `realloc`, and `free`. It communicates over a line-oriented stdin/stdout protocol and cleans all active allocations on exit.
- `server/`: Express API. On Linux it reads `/proc/meminfo` and `/proc/<pid>/status`; on other platforms it reports host RAM using Node.js OS metrics. It also owns the C engine process on Linux.
- `client/`: React + TypeScript dashboard with live metrics, allocation controls, process view, leak view, and analytics.

## Linux setup

```bash
cd native
make
cd ../server
npm install
npm run dev
```

In a second terminal:

```bash
cd client
npm install
npm run dev
```

Open the Vite URL shown by the client. The backend defaults to `http://localhost:4000`.

On Windows, the dashboard and API provide live host RAM and API-process memory telemetry. Use WSL2 or Linux to enable the native C allocation controls and detailed `/proc` process monitoring.

## API

- `GET /api/health`
- `GET /api/system/memory`
- `GET /api/processes`
- `GET /api/allocations`
- `GET /api/allocations/history`
- `POST /api/allocations` with `{ "operation": "malloc|calloc", "size": number, "count": number }`
- `PATCH /api/allocations/:id` with `{ "size": number }`
- `DELETE /api/allocations/:id`
- `GET /api/metrics`
- `GET /api/leaks`
- `GET /api/events`

The API emits `metrics`, `allocation`, and `engine` events over Server-Sent Events at `/api/events`. History is bounded in memory.

## Memory definitions

Linux `MemAvailable` is used as the best estimate of immediately available RAM. Used RAM is calculated as `MemTotal - MemAvailable`; cache and buffers remain visible as separate fields. An active allocation is reported as a potential leak only after the configurable age threshold (five minutes); it is never called a confirmed leak solely because it is still active.

## Tests

```bash
cd server
npm test
```

The C engine can be smoke-tested on Linux with:

```bash
printf 'malloc 64\ncalloc 4 16\nstate\nfree 1\nrealloc 2 128\nstate\n' | ./native/memory_engine
```
