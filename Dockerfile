FROM debian:trixie-slim
ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=C.UTF-8
RUN rm -f /etc/apt/apt.conf.d/docker-no-languages \
 && apt-get update -qq \
 && apt-get install -y -qq --no-install-recommends \
      python3 python3-xapian sudo apt-file zbar-tools ca-certificates \
 && apt-file update \
 && rm -rf /var/cache/apt/archives/*
WORKDIR /brain
COPY . /brain
CMD ["/bin/sh","-lc","echo H3_CARRIER_READY=1"]
