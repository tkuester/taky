# First stage: builder
FROM python:3.11 as builder

ENV TAKY_VERSION=0.9

WORKDIR /build

RUN git clone --depth 1 https://github.com/tkuester/taky.git -b ${TAKY_VERSION}

WORKDIR /build/taky

RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install -r requirements.txt && \
    python3 setup.py install && \
    find /usr/local -name '*.pyc' -delete && \
    find /usr/local -name '__pycache__' -type d -exec rm -rf {} +

# Second stage: runtime
FROM python:3.11-slim as runtime

WORKDIR /

COPY --from=builder /usr/local /usr/local

RUN mkdir -p /var/taky

ENTRYPOINT [ "taky", "-c", "/taky/taky.conf" ]
