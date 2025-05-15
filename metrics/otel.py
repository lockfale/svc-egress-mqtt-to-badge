import logging
import logging.config
import os
import socket
import time
from typing import Callable

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

# from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

logging.config.fileConfig("log.ini")
logger = logging.getLogger("console")
logger.setLevel(logging.INFO)
# Get the host name of the machine
host_name = socket.gethostname()

# Setup OpenTelemetry
resource = Resource.create(
    {
        "service.name": "svc-world-clock",
    }
)

exporter = OTLPMetricExporter(endpoint=f"http://{os.getenv('OTEL_COLLECTOR_SVC')}:4317", insecure=True)
metric_reader = PeriodicExportingMetricReader(exporter)
provider = MeterProvider(metric_readers=[metric_reader], resource=resource)

# Sets the global default meter provider
metrics.set_meter_provider(provider)

# Creates a meter from the global meter provider
meter = metrics.get_meter("my.meter.name")


# A simple counter metric
request_counter = meter.create_counter(
    "dev-sql-query-test",
    description="Number of HTTP requests",
)


def add_one_request():
    logger.info({"host": host_name})
    request_counter.add(1, {"host": host_name})


# Histogram for processing time
processing_time_histogram = meter.create_histogram("processing_time_seconds", description="Processing time in seconds", unit="s")


def log_processing_time(duration_seconds: float):
    processing_time_histogram.record(duration_seconds, {"host": host_name})
    logger.info(f"Processing time: {duration_seconds} seconds")
