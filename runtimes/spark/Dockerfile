FROM python:3.11.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends openjdk-17-jre-headless procps && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pyspark==3.5.5
RUN useradd --uid 10001 --create-home academy && mkdir -p /work && chown -R academy:academy /work
COPY runtimes/spark/runner.py /opt/runner.py
USER academy
ENV SPARK_LOCAL_IP=127.0.0.1 SPARK_LOCAL_HOSTNAME=graphlab PYTHONUNBUFFERED=1 HOME=/home/academy
ENTRYPOINT ["python","/opt/runner.py"]
