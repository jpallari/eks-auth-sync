FROM debian:stable-slim as base
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false && \
    rm -rf /var/lib/apt/lists/*

FROM base as builder
RUN mkdir /install && \
    apt-get update && \
    apt-get install -y build-essential python3-setuptools python3-wheel
WORKDIR /workspace
COPY . .
RUN pip3 wheel --wheel-dir=/pywheels -e . && \
    python3 setup.py bdist_wheel -d /pywheels

FROM base
COPY --from=builder /pywheels /pywheels
RUN python3 -m pip install --no-index --find-links=/pywheels eks-auth-sync
RUN groupadd -g 10101 app && \
    useradd -r -u 10101 -g app app
USER app
ENTRYPOINT [ "eks-auth-sync" ]
