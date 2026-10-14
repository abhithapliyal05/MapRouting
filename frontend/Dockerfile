# Static site, no build step, so a single stage is the honest choice.
# nginx-unprivileged runs as uid 101 and listens on 8080 (non-root cannot bind 80).
FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY index.html /usr/share/nginx/html/index.html
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q --spider http://127.0.0.1:8080/ || exit 1
