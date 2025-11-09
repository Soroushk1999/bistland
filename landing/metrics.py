from prometheus_client import Counter, Histogram

# Count requests by status
endpoint_requests = Counter(
    'endpoint_requests_total',
    'Total number of requests to the heavy endpoint',
    ['status']  # label to separate success/failure
)

# Measure response latency
endpoint_latency = Histogram(
    'endpoint_request_duration_seconds',
    'Request duration for the heavy endpoint'
)
