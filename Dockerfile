# Same base image as local devcontainer docker-compose.yml
FROM ghcr.io/frepple/frepple-community:9.13.0

USER root

# Copy the local codebase into /app (same as: volumes: - ..:/app)
COPY --chown=frepple:frepple . /app

# Copy our custom entrypoint and make it executable
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

USER frepple

# Override the official image's entrypoint with ours
# Ours runs: createdatabase → migrate → runserver (not Apache)
ENTRYPOINT ["/docker-entrypoint.sh"]
