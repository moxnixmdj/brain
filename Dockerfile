FROM debian:trixie-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=C.UTF-8

RUN rm -f /etc/apt/apt.conf.d/docker-no-languages \
 && apt-get update -qq \
 && apt-get install -y -qq --no-install-recommends \
      python3 \
      python3-xapian \
      apt-file \
      ca-certificates \
      sudo \
      zbar-tools \
      xz-utils \
 && apt-file update \
 && rm -rf /var/cache/apt/archives/*

WORKDIR /work
COPY . /work

CMD ["/bin/sh","-lc","echo HELDOUT003_CARRIER_READY; exec python3 -m http.server ${PORT:-10000} --bind 0.0.0.0"]
