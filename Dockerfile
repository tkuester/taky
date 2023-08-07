# First stage: builder
FROM python:3.11 as builder

ENV TAKY_VERSION=0.9
ENV PUBLIC_IP=192.168.0.60

WORKDIR /build

RUN git clone --depth 1 https://github.com/tkuester/taky.git -b ${TAKY_VERSION}

WORKDIR /build/taky

RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install -r requirements.txt && \
    python3 setup.py install && \
    find /usr/local -name '*.pyc' -delete && \
    find /usr/local -name '__pycache__' -type d -exec rm -rf {} +

RUN takyctl setup --public-ip=${PUBLIC_IP} /etc/taky

# Second stage: runtime
FROM python:3.11-slim as runtime

WORKDIR /

RUN mkdir /var/taky

COPY --from=builder /usr/local /usr/local
COPY --from=builder /etc/taky /etc/taky

ENTRYPOINT [ "taky", "-c", "/etc/taky/taky.conf" ]
