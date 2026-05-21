# Container image for swiss-cultural-heritage-mcp.
#
# Security posture (audit findings SEC-007 / SEC-021):
#   - non-root user (UID 10001)
#   - slim base, no compiler in the final layer
#   - default port 8000 for Streamable HTTP
#
# Recommended platform settings on Kubernetes / Cloud Run / Fly.io:
#   readOnlyRootFilesystem: true
#   allowPrivilegeEscalation: false
#   capabilities.drop: ["ALL"]
#   seccompProfile: RuntimeDefault

FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin app
USER 10001

EXPOSE 8000

CMD ["python", "-m", "swiss_cultural_heritage_mcp.server", "--http", "--port", "8000"]
