#!/usr/bin/env python
#
# Author: Scott Sanders <scott@jssjr.com>
#
# Collect statistics from Varnish, format them, and send them to Graphite.

import argparse
import json
import signal
import socket
import string
import subprocess
import time


class GraphiteClient:
  sendbuf = ''

  def __init__(self, host='127.0.0.1', port=2003, prefix='varnish', buffer_size=1428):
    self.prefix = prefix
    self.host   = host
    self.port   = port
    self.buffer_size = buffer_size

    self.connect()

  def connect(self):
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.sock.connect((self.host, self.port))
    print("Connected to {}:{}".format(self.host, self.port))

  def send_metrics(self, metrics):
    for stat in metrics:
      if len(self.sendbuf) + len("{}.{}".format(self.prefix, stat)) > self.buffer_size:
        print("Sending {} bytes to {}".format(len(self.sendbuf), "{}:{}".format(self.host, self.port)))
        self.sock.send(self.sendbuf)
        self.sendbuf = ''
      self.sendbuf += "{}.{}\n".format(self.prefix, stat)

  def disconnect(self):
    self.sock.close()
    print("Disconnected from {}:{}".format(self.host, self.port))


def parse_varnishstat():
  return json.loads(subprocess.check_output(['varnishstat', '-1', '-j']))


def collect_metrics():
  stats  = parse_varnishstat()
  ts     = int(time.time())

  status = []
  fmt = lambda x, y: "{} {} {}".format(x, stats[y]['value'], ts)

  metrics = [('cache.hit', 'cache_hit'),
             ('cache.hitpass', 'cache_hitpass'),
             ('cache.miss', 'cache_miss'),
             ('backend.conn', 'backend_conn'),
             ('backend.unhealthy', 'backend_unhealthy'),
             ('backend.busy', 'backend_busy'),
             ('backend.fail', 'backend_fail'),
             ('backend.reuse', 'backend_reuse'),
             ('backend.toolate', 'backend_toolate'),
             ('backend.recycle', 'backend_recycle'),
             ('backend.retry', 'backend_retry'),
             ('backend.req', 'backend_req'),
             ('client.conn', 'client_conn'),
             ('client.drop', 'client_drop'),
             ('client.req', 'client_req'),
             ('client.hdrbytes', 's_hdrbytes'),
             ('client.bodybytes', 's_bodybytes')]

  for (name, metric) in metrics:
    status.append(fmt(name, metric))

  return status


def main():
  parser = argparse.ArgumentParser(description='Collect and stream Varnish statistics to Graphite.')
  parser.add_argument('-H', '--host', default='127.0.0.1')
  parser.add_argument('-p', '--port', default=2003)
  parser.add_argument('-P', '--prefix', default='varnish')
  # Ethernet - (IPv6 + TCP) = 1500 - (40 + 32) = 1428
  parser.add_argument('-b', '--buffer-size', dest='buffer_size', default=1428)
  args = parser.parse_args()

  c = GraphiteClient(args.host, args.port, args.prefix, args.buffer_size)

  try:
    while True:
      c.send_metrics(collect_metrics())
      time.sleep(10)
  except KeyboardInterrupt:
    c.disconnect();

if __name__ == "__main__":
  main()

