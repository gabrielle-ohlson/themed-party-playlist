import redis
from rq import Worker, Queue, Connection

import os
from dotenv import load_dotenv

load_dotenv()

listen = ['high', 'default', 'low']

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:5000') #6379

conn = redis.from_url(redis_url)

if __name__ == '__main__':
	with Connection(conn):
		worker = Worker(map(Queue, listen))
		worker.work()