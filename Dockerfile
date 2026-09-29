FROM debian:trixie-slim
ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=C.UTF-8
WORKDIR /brain
COPY . /brain
CMD ["/bin/sh","-lc","echo H3_CARRIER_READY=1"]
