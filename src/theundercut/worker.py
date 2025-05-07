"""
RQ worker entry‑point – compatible with RQ 2.x.
"""

from rq import Queue, Worker
from theundercut.adapters.redis_cache import redis_client

if __name__ == "__main__":
    queue = Queue("default", connection=redis_client)
    worker = Worker([queue], connection=redis_client)
    print("RQ worker ready ⛑️  (RQ", worker.version, ")")
    worker.work()
