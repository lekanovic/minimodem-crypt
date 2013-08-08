#!/usr/bin/env python
# vim: ts=4 et

import subprocess
import threading
import time
import select

class Receiver:
    def __init__(self, **kwargs):
        pass

class Transmitter:
    def __init__(self, **kwargs):
        self.p = subprocess.Popen(['minimodem', '-t', '-8',
            kwargs.get('baudmode', 'rtty')] + kwargs.get('extra_args', []),
            stdin=subprocess.PIPE)

    def write(self, text):
        self.p.stdin.write(text)

    def close(self):
        self.p.stdin.close()
        self.p.wait()


class Receiver:
    class ReceiverReader(threading.Thread):
        def __init__(self, stdout, stderr):
            threading.Thread.__init__(self)
            self.stdout = stdout
            self.stderr = stderr
            self.packets = []

        def run(self):
            in_packet = False
            packet = ''
            while True:
                readers, _, _ = select.select([self.stdout, self.stderr], [], [])
                if in_packet:
                    if self.stdout in readers:
                        data = self.stdout.read(1)
                        if not data:
                            break
                        packet += data
                        continue
                if self.stderr in readers:
                    line = self.stderr.readline()
                    if not line:
                        break
                    if line.startswith('### CARRIER '):
                        in_packet = True
                        packet = ''
                    elif line.startswith('### NOCARRIER '):
                        in_packet = False
                        print 'Got packet: %s' % packet
                        self.packets.append(packet)

    def __init__(self, **kwargs):
        self.p = subprocess.Popen(['minimodem', '-r', '-8',
            kwargs.get('baudmode', 'rtty')] + kwargs.get('extra_args', []),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.reader = Receiver.ReceiverReader(self.p.stdout, self.p.stderr)
        self.reader.setDaemon(True)
        self.reader.start()


if __name__ == "__main__":
    receiver = Receiver()
    sender = Transmitter()
    sender.write('Hello world!')
    sender.close()
    receiver.p.wait()

