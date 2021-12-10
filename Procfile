web: gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 app:app --timeout 0 --worker-class=gevent --preload
worker: python -u worker.py