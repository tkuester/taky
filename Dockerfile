FROM python:3.9-slim-buster as builder

# git and the .git dir are needed by pip to determine the package version
RUN apt-get -qq update && apt-get -qq install git
RUN mkdir /app
COPY taky /app/taky
COPY .git /app/.git
# README.md is read by setup.py to provide the long description
COPY setup.py README.md /app
# Running pip from inside the app directory causes it to install cot/dps as individual modules, rather than under taky
RUN python -m pip --use-feature=in-tree-build install /app

FROM python:3.9-slim-buster
RUN python -m pip install supervisor

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY entrypoint.sh .
# Grab the installed packages and entry point scripts from the builder container
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin/tak* /usr/local/bin

CMD ["./entrypoint.sh"]
