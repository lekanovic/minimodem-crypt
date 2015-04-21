#!/usr/bin/env python
# vim: ts=4 et

import subprocess
import threading
import time
import select
import zlib, base64


class Transmitter:
    def __init__(self, compress=True, **kwargs):
        self.p = subprocess.Popen(['bin/minimodem', '-t', '-8',
            kwargs.get('baudmode', 'rtty')] + kwargs.get('extra_args', []),
            stdin=subprocess.PIPE)
        self.compress = compress

    def write(self, text):
        s = len(text)
        print text
        if self.compress:
            text = base64.b64encode(zlib.compress(text))
            print "Size before %d size after %d" % (s, len(text))
        self.p.stdin.write(text)

    def close(self):
        self.p.stdin.close()
        self.p.wait()


class Receiver:
    class ReceiverReader(threading.Thread):
        def __init__(self, stdout, stderr, compress=True):
            threading.Thread.__init__(self)
            self.stdout = stdout
            self.stderr = stderr
            self.packets = []
            self.compress = compress

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
                        if self.compress:
                            packet = zlib.decompress(base64.b64decode(packet))
                        if len(packet) > 10:
                            print 'Got packet: %s' % packet
                            self.packets.append(packet)

    def __init__(self, compress=True, **kwargs):
        self.p = subprocess.Popen(['bin/minimodem', '-r', '-8', '-A',
            kwargs.get('baudmode', 'rtty')] + kwargs.get('extra_args', []),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.compress = compress
        self.reader = Receiver.ReceiverReader(self.p.stdout, self.p.stderr, compress)
        self.reader.setDaemon(True)
        self.reader.start()


if __name__ == "__main__":
    use_compression = False
    baud = '3000'
    receiver = Receiver(compress=use_compression, baudmode=baud)

    sender = Transmitter(compress=use_compression, baudmode=baud)
    sender.write('01000000015a06d623ff099d77dbba3cd6fd2eec42f250768c61d443584b53a827acaaad580100000000ffffffff0600000000000000002a6a284163636f7264696e6720746f2074686520456e6379636c6f7065646961204272697474616e69636100000000000000002a6a282c20746865204e617469766520416d65726963616e202671756f743b547261696c206f662054656100000000000000002a6a2872732671756f743b20686173206265656e207265646566696e656420617320616e7977686572652000000000000000001a6a187468617420436875636b204e6f727269732077616c6b732e10270000000000001976a914bd52402e41483cc632ced18ad798b1b8c59de7a688acd3dc0700000000001976a914aeb7b78c4e59a0613260b949b863e2a4dcdf3dc688ac00000000f32a0800000000001976a914aeb7b78c4e59a0613260b949b863e2a4dcdf3dc688ac')
    sender.close()
    time.sleep(3)

    receiver.p.wait()

