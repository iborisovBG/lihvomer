# Deployment

How Лихвомер runs in production at [xbotics.ai](https://xbotics.ai). The setup
shares a server with other applications, so isolation was the main constraint.

## Layout

| Component | Port | Exposure |
|---|---|---|
| FastAPI | 8000 | localhost only |
| Next.js | 3001 | localhost only |
| PostgreSQL | 5432 | localhost only |
| Redis | 6379 | localhost, separate database number |
| nginx | 80/443 | public |

Everything runs as a dedicated unprivileged user. nginx is the only public
surface; the application never binds to a public interface.

## systemd

Three units — API, worker, web — each with `ProtectSystem=strict`,
`ProtectHome=true` and `NoNewPrivileges=true`, writing only to their own
directory.

```bash
systemctl enable --now lihvomer-api lihvomer-worker lihvomer-web
systemctl status lihvomer-api
journalctl -u lihvomer-worker -f
```

## nginx

Two rules matter more than the rest.

**HTML must not be cached.** Next.js sets `s-maxage=31536000` on the shell. That
is meant for a CDN, but browsers apply it heuristically and a visitor can be
stuck on a stale shell for up to a year — one that references bundles which no
longer exist after a deploy. Override it:

```nginx
location / {
    proxy_pass http://127.0.0.1:3001;
    proxy_hide_header Cache-Control;
    add_header Cache-Control "no-cache, must-revalidate" always;
}
```

**Do not let API routes shadow application pages.** The health check originally
lived at `/health`, which is also a page in the app; nginx won, and users saw raw
JSON instead of the interface. Keep API routes under their own prefix:

```nginx
location = /api/health { proxy_pass http://127.0.0.1:8000/health; }
```

Static assets are content-hashed and safe to cache for a year:

```nginx
location /_next/static/ {
    proxy_pass http://127.0.0.1:3001;
    expires 365d;
    add_header Cache-Control "public, immutable";
}
```

## Deploying an update

```bash
rsync -az --delete --exclude-from=.rsyncignore backend frontend user@server:/opt/lihvomer/app/
ssh user@server '
  cd /opt/lihvomer/app/backend && .venv/bin/pip install -q -r requirements.txt
  cd ../frontend && rm -rf .next && npm ci && npm run build
  systemctl restart lihvomer-api lihvomer-worker lihvomer-web'
```

`rm -rf .next` matters: old chunks survive an incremental build and can be served
alongside new ones.

Never deploy `.env.local` — Next.js reads it with the highest priority and will
bake a development API address into the public bundle.

## Recovering a stuck browser

Because static assets are served `immutable`, a browser that once received a
broken build cannot be fixed remotely. The app ships `/reset`, a page that
unregisters the service worker, clears all caches and reloads. It works because
its own URL was never cached.

## Verifying a deploy

```bash
curl -s https://xbotics.ai/api/health
for p in "" state news sources calculator health loans alerts login; do
  curl -s -o /dev/null -w "$p %{http_code}\n" "https://xbotics.ai/$p"
done
```

Then confirm no bundle carries a development address — including the `app/`
subdirectory, which holds per-page code and is easy to miss:

```bash
curl -s "https://xbotics.ai/?t=$(date +%s)" \
  | grep -oE '/_next/static/chunks/[a-zA-Z0-9/_-]+\.js' | sort -u \
  | while read u; do curl -s "https://xbotics.ai$u" | grep -q "127.0.0.1" && echo "STALE: $u"; done
```
