# Static site, no build step, so a single stage is the honest choice.
# nginx-unprivileged runs as uid 101 and listens on 8080 (non-root cannot bind 80).
FROM nginxinc/nginx-unprivileged:1.30-alpine
# Patch an OS package the upstream base image has not been rebuilt with yet (Trivy: CVE-2026-111497,
# brotli-libs 1.2.0-r1, fixed in 1.2.1-r0). Root is needed only for this one command.
# Remove once the base image ships the fix.
USER root
RUN apk upgrade --no-cache brotli-libs
USER 101
COPY index.html /usr/share/nginx/html/index.html
COPY config.js /usr/share/nginx/html/config.js
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q --spider http://127.0.0.1:8080/ || exit 1
