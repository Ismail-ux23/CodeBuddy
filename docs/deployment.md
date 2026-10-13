# Deployment (not performed)

The repository includes deployment configuration but no infrastructure has been created and no website has been published.

1. Build reviewed images from committed lockfiles and run the integration and live-provider smoke checks in staging.
2. Set `APP_ENV=production`, a random `APP_SECRET_KEY`, provider key, strong database credentials, and the external `APP_BASE_URL`.
3. Terminate HTTPS at a trusted ingress. Keep PostgreSQL, Redis, Flask, and Next.js private; expose only Nginx/ingress.
4. Preserve Secure cookies. Configure forwarded headers only for your trusted ingress; Nginx currently overwrites them for its direct client. Do not enable unconditional ProxyFix behind untrusted clients. The limiter keys by the direct peer by default; configure a trusted client-IP function for multi-user production traffic.
5. Keep Nginx request size at least the API ZIP limit plus multipart overhead. Disable response buffering for SSE. API uses two Gunicorn workers, eight threads each, and a 90-second timeout; each SSE connection lasts at most 60 seconds.
6. Run one controlled migration job before the application rollout. The application never silently calls create_all at runtime. Back up PostgreSQL and the source volume together before migration; verify restore procedures.
7. Keep the worker at concurrency two on a 16 GB development machine. Monitor queue lag, job failures, disk volume growth, provider quotas, and `/api/v1/health/ready`.
8. Keep exactly one beat scheduler and ensure its cleanup task runs. Source volume and database backups need an explicit retention/deletion policy; this repository does not create a backup service.
9. Rollback: retain the previous image and compatible schema; restore coordinated backups if a schema rollback is necessary. Do not roll back embedding settings while reusing an incompatible index.

The Compose development password and HTTP port are unsuitable for public production. Redis persistence is enabled, but durable authoritative job state remains in PostgreSQL. The scheduler redispatches queued jobs after transport failures. Monitor jobs stuck running after infrastructure failure; Celery redelivery/visibility timeouts are not instantaneous.
