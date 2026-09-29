FROM debian:trixie-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=C.UTF-8

RUN rm -f /etc/apt/apt.conf.d/docker-no-languages \
 && apt-get update -qq \
 && apt-get install -y -qq --no-install-recommends \
      python3 python3-xapian sudo apt-file zbar-tools ca-certificates xz-utils \
 && apt-file update >/tmp/pb003-aptfile-update.log 2>&1

WORKDIR /work
COPY . /work

CMD ["/bin/sh", "/work/.carrier/heldout003-one-shot.sh"]
