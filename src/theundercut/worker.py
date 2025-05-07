"""
RQ worker entry‑point.

It listens to the default queue (same Redis used by the scheduler) and
runs any jobs enqueued by `theundercut.scheduler`.
"""

from rq import Worker, Queue, Connection
from theundercut.adapters.redis_cache import redis_client

if __name__ == "__main__":
    with Connection(redis_client):
        worker = Worker(queues=[Queue("default")])
        print("RQ worker ready ⛑️")
        worker.work()
