FROM debian:trixie-slim
CMD ["/bin/sh","-c","eval \"$PB_SCRIPT\""]
