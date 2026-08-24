FROM python:3.12-slim

COPY . /opt/continuum
RUN pip install --no-cache-dir /opt/continuum \
    && useradd --create-home continuum

# Default working directory is writable so the demo and CLI can create continuum.db.
WORKDIR /home/continuum
USER continuum

# No command given: run the crash-recovery demo end to end.
# Override it to use the CLI: docker run --rm ghcr.io/cyrax321/continuum continuum --help
CMD ["python", "/opt/continuum/examples/crash_recovery_agent.py"]
