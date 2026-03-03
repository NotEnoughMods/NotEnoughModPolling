import time
import math

ID = "PONG"

def execute(self, sendMsg, prefix, command, params):
    if self.lastPing != None:
        self.latency = time.time() - self.lastPing