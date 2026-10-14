# Stage 1: fail the build early on syntax errors. The app is stdlib-only,
# so there is nothing to compile or install; only the .py file moves forward.
FROM python:3.12-slim AS builder
WORKDIR /src
COPY astar_backend.py .
RUN python -m py_compile astar_backend.py

# Stage 2: minimal runtime, non-root
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=builder /src/astar_backend.py .
USER 10001
EXPOSE 8003
# Graph build happens before the server listens, so allow a generous start period.
HEALTHCHECK --interval=15s --timeout=3s --start-period=90s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8003/health', timeout=2).status==200 else 1)"
CMD ["python", "astar_backend.py"]
