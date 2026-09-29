FROM debian:trixie-slim
WORKDIR /work
COPY . /work
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 apt-file curl ca-certificates coreutils \
 && rm -rf /var/lib/apt/lists/*
CMD ["/bin/sh", "/work/railway-heldout-002-carrier.sh"]
