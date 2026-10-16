FROM python:3.12-slim

WORKDIR /app
COPY . .

# Keep the image runnable for both the CLI and the repository's one test command.
RUN apt-get update \
    && apt-get install -y --no-install-recommends make \
    && rm -rf /var/lib/apt/lists/*

CMD ["python", "-m", "repro_doctor", "--help"]
