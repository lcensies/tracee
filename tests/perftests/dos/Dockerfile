# TODO: change to alpine
FROM debian:12.5-slim as builder

RUN apt-get update \
  && apt-get -y install build-essential wget \
  && rm -rf /var/lib/apt/lists/* \
  && wget https://github.com/Kitware/CMake/releases/download/v3.24.1/cmake-3.24.1-Linux-x86_64.sh \
  -q -O /tmp/cmake-install.sh \
  && chmod u+x /tmp/cmake-install.sh \
  && mkdir /opt/cmake-3.24.1 \
  && /tmp/cmake-install.sh --skip-license --prefix=/opt/cmake-3.24.1 \
  && rm /tmp/cmake-install.sh \
  && ln -s /opt/cmake-3.24.1/bin/* /usr/local/bin


WORKDIR app
COPY . .

RUN cmake -S . -B build && cmake --build build

FROM debian:stable-slim AS dos

WORKDIR app

COPY --from=builder /app/build/dos dos

ENTRYPOINT ["/app/dos"]

