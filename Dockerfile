FROM python:3.11-slim

LABEL Name=Butlarr Version=1.0

WORKDIR /app
ADD . /app

RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt


# Custom entrypoint script to run the interactive setup if BUTLARR_INTERACTIVE_SETUP=true
COPY scripts/docker_entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

CMD ["python3", "-m", "butlarr"]