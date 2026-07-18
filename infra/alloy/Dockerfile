FROM grafana/alloy:v1.9.2

# Build context is the repo root (Railway default; buildContext is not a
# valid railway.toml field). Paths are relative to the repository root.
COPY infra/alloy/config.alloy /etc/alloy/config.alloy
COPY infra/alloy/docker-entrypoint.sh /docker-entrypoint.sh

USER root
RUN chmod +x /docker-entrypoint.sh \
  && mkdir -p /var/lib/alloy/data \
  && chown -R alloy:alloy /var/lib/alloy /etc/alloy/config.alloy
USER alloy

# OTLP gRPC / OTLP HTTP; Alloy UI + readiness on $PORT (default 12345)
EXPOSE 4317 4318 12345

# Override image ENTRYPOINT (/bin/alloy) so we can bind --server.http to $PORT.
ENTRYPOINT ["/docker-entrypoint.sh"]
