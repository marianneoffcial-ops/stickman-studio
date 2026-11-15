# Stickman Studio — free eight-step explainer workflow

A Docker-ready FastAPI application that follows the user's eight-step Stickman Explainer Engine flow. It uses a free Wikipedia API lookup for source-linked research, deterministic scene planning, a PIL-based 2D stick-figure renderer, Edge TTS with eSpeak fallback, and FFmpeg to produce an MP4 and a 16:9 thumbnail.

## Eight-step workflow

1. Show ten fresh story ideas, balanced across history, documentary, true crime and remarkable true events. Users may also enter a custom topic.
2. Lock the aspect ratio (16:9, 9:16, 1:1, or a supported custom ratio).
3. Choose 15–600 seconds. The renderer calculates ceil(duration / 4) scenes.
4. Retrieve public research, provide source links, and assemble narration beats. If retrieved source material is insufficient, the research endpoint refuses rather than inventing missing facts.
5. Produce the character-sheet prompt and a locked recurring-character block.
6. Produce one full animation prompt per scene, then queue the MP4 render.
7. Ask whether a thumbnail prompt is needed; render a matching 16:9 thumbnail.
8. Reset the workflow and offer ten unused ideas where available.

## API

- `GET /` — browser workflow
- `GET /health` — health, queue and renderer metadata; also reports whether both Cloudflare Workers AI credentials are configured (without exposing either secret)
- `GET /ready` — readiness checks for FFmpeg, TTS and writable project storage
- `GET /api/ideas` — curated real-story idea pool
- `POST /api/research` — source-linked research and timed narration
- `POST /api/prepare` — preview the character sheet and animation prompts
- `POST /api/projects` — queue an MP4 render
- `GET /api/jobs` — paginated render history
- `GET /api/jobs/{job_id}` — render status, scene progress and output verification metadata
- `GET /api/projects/{project_id}` — project and associated job status
- `GET /api/jobs/{job_id}/download` — finished MP4
- `GET /api/projects/{project_id}/thumbnail` — matching 16:9 thumbnail

## Free/open-source runtime

- Python 3.11, FastAPI, Pillow, FFmpeg, eSpeak NG
- Edge TTS is attempted for a more natural English voice; eSpeak NG is the offline fallback.
- Wikipedia's public API is used for research. Source URLs and CC BY-SA attribution guidance are returned with each research result.
- The standard video workflow needs no AI API key or paid media service.
- Optional Cloudflare FLUX background plates require the two credentials described below; without them the local illustrated renderer is used.

## Optional AI-generated scene backgrounds (Cloudflare Workers AI)

The renderer can optionally request one FLUX.1 schnell image per scene as an environment-only background plate. The recurring stickman, its poses and movement, camera animation, narration, and final MP4 assembly remain locally rendered with Pillow and FFmpeg. This is **AI-assisted background artwork**, not neural text-to-video generation.

To enable it without entering secrets in chat:

1. In the Cloudflare dashboard, open **Workers & Pages → Workers AI → Use REST API**.
2. Choose **Create a Workers AI API Token**. If creating a custom token, grant both **Workers AI – Read** and **Workers AI – Edit** permissions.
3. Copy the **Account ID** shown on the same page. Keep the API token private; Cloudflare may show the secret only at creation time.
4. In the Railway service's **Variables** settings, add `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN`. Save them as service variables, not in source code, commits, or chat messages.
5. Keep the Cloudflare account on the **Workers Free** plan. Workers AI currently includes 10,000 Neurons per day at no charge. The free-plan requests stop when that allowance is exhausted; do not upgrade to a paid Workers plan for this project.
6. Check `GET /health`. The field `cloudflare_ai_backgrounds_configured` should become `true`. Generate a short test video and inspect it before relying on the feature.

Cloudflare's FLUX.1 schnell API is documented at [the model page](https://developers.cloudflare.com/workers-ai/models/flux-1-schnell/); REST credentials and permission requirements are documented in [the REST API guide](https://developers.cloudflare.com/workers-ai/get-started/rest-api/), and daily free allowance details are on [Workers AI pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/). Neuron consumption depends on image size and steps. If the free quota is unavailable or the request fails, the worker falls back to procedural illustrated backgrounds and still attempts to finish the video. The application does not change your Cloudflare plan or enable billing.

## Important limitations

The renderer is deterministic PIL/FFmpeg vector animation, not a neural video-generation model. It creates a restrained motion-comic with camera movement and simple character/environment animation; it cannot guarantee the organic, frame-to-frame hand-inked animation quality of a modern generative video model. The free research text is assembled from retrieved encyclopedia material with citations, not a human-quality paraphrase or independent fact-check. Review source links and narration before publication.

Railway's current production service has no attached persistent volume. Rendered files and in-memory job state may be lost on a container restart. Adding persistent storage may incur cost, so this repository does not enable or provision a volume automatically.

## Production reliability improvements

- Render requests are validated before entering the queue; draft projects with missing scene narration cannot be exported as finished videos.
- A single bounded CPU render queue prevents simultaneous long renders from exhausting the free worker.
- Job metadata is atomically written beside each project, restored when the process starts with the same data directory, and interrupted jobs are clearly marked rather than reported as completed.
- The browser receives scene-by-scene progress, elapsed time, and a percentage for both single and dual-video production.
- Finished MP4 files are checked with FFprobe for readable video and audio streams, exact output dimensions, and duration before the download endpoint becomes available.
- Project and job identifiers are validated as UUIDs, output paths are constrained to their project directory, and supplied source links must use HTTP or HTTPS.
- The queue and job history are exposed through paginated API endpoints; /ready reports missing runtime dependencies separately from basic process health.

The Railway service currently has no persistent volume. These metadata improvements survive an application-process restart only when the configured data directory itself survives; they do not make generated MP4 files durable across Railway redeploys without persistent storage.

## Local run

```bash
pip install -r requirements.txt
# Install ffmpeg and espeak-ng using your OS package manager.
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`.

## Tests

```bash
python -m compileall -q app worker tests
python -m unittest discover -s tests -v
```

GitHub Actions runs these checks, including a one-scene MP4 smoke render with duration, frame-rate and aspect-ratio assertions.
