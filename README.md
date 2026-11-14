# Stickman Studio AI — cloud-first agent

A Docker-ready, CPU-based stickman video production service. It does not use the viewer's PC or GPU. Submit a topic in the browser; the server creates an English script, scene manifest, vector animation, narration with espeak-ng, and MP4 via FFmpeg.

## Included
- FastAPI web UI and API
- Story/scene planner and character continuity preset
- Cloud-side rendering worker, narration, MP4 output verification
- Dockerfile and docker-compose
- Demo canon: THE SHADOWS OF SEVEN SEALS — Episode 1: THE BLACK NIGHT

## Important limitations
This is deployable source, not a live hosted service. A cloud host must build and run it. Hosting may cost money. No paid infrastructure is activated. The built-in planner is deterministic; an LLM can be integrated later. CPU vector rendering requires no GPU.

## Deploy
Push this repository to GitHub, create a Railway service from the repo, add a persistent volume at `/data`, and open its generated domain. See DEPLOY_RAILWAY.md.
