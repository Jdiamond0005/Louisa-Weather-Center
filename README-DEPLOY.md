# Louisa Weather Center — Railway deployment

This package contains the web dashboard and Python weather monitor. The server checks official National Weather Service forecasts and active alerts every 300 seconds while running. It is not a real-time radar service or a multi-model comparison engine.

## Upload to GitHub on iPhone

1. Open https://github.com/Jdiamond0005/Louisa-Weather-Center in Safari, sign in, and choose **Add file → Upload files** (request Desktop Website in Safari if necessary).
2. **Extract** the downloaded ZIP in the iPhone Files app first. Upload these four files from inside the extracted folder to the **repository root**, not into a subfolder: `server.py`, `index.html`, `railway.json`, and `README-DEPLOY.md`.
3. Commit the upload to the `main` branch. Keep the existing README.md.

## Deploy on Railway

1. In Railway, create a new project from GitHub repository `Jdiamond0005/Louisa-Weather-Center`, branch `main`.
2. Set environment variable `POLL_SECONDS=300`. Optionally set `NWS_USER_AGENT` to an application identifier containing a real contact address; NWS asks for an identifiable User-Agent.
3. Deploy, generate a public domain, and open `https://YOUR-DOMAIN/health` and `/api/status`.
4. Check that `last_success_at` is populated, `errors` is empty, and `checked_at` advances about every five minutes. A successful /health response alone does not prove the NWS feeds are working.

## Limitations and operations

- Railway must keep the service awake continuously; do not enable application sleeping.
- `weather-state.json` is saved to ephemeral local storage. Deployments/restarts may reset this history; attach a persistent volume or database if history matters.
- Browser display polls server status every minute. NWS forecast data and alert publications may be less frequent than five minutes.
- This does not yet implement live radar layers, ECMWF/GFS comparisons, or Facebook auto-publishing.
- Do not rely on this dashboard as the only emergency alert channel.
