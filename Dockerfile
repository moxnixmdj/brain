FROM debian:trixie-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

RUN set -eux; \
    rm -f /etc/apt/apt.conf.d/docker-no-languages; \
    apt-get update -qq; \
    apt-get install -y -qq --no-install-recommends \
      python3 python3-xapian apt-file sudo zbar-tools ca-certificates; \
    apt-file update; \
    arch="$(dpkg --print-architecture)"; \
    tr_count="$(apt-get indextargets --format '$(FILENAME)' 'Identifier: Translations' 'Language: en' | sed '/^$/d' | wc -l | tr -d ' ')"; \
    arch_contents="$(find /var/lib/apt/lists -maxdepth 1 -type f -name "*Contents-${arch}*" | wc -l | tr -d ' ')"; \
    all_contents="$(find /var/lib/apt/lists -maxdepth 1 -type f -name '*Contents-all*' | wc -l | tr -d ' ')"; \
    tag_records="$(apt-cache dumpavail | awk '/^Tag:/{n++} END{print n+0}')"; \
    test "$tr_count" -gt 0; \
    test "$arch_contents" -gt 0; \
    test "$all_contents" -gt 0; \
    test "$tag_records" -gt 0; \
    python3 -c 'import xapian'; \
    command -v sudo; \
    command -v zbarimg

WORKDIR /brain
COPY . /brain

CMD ["/bin/sh", "/brain/carrier/heldout003_entrypoint.sh"]
