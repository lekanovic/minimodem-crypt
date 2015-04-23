import subprocess
import threading
import time
import select
import zlib, base64
from threading import Thread
from  crypt.reedsolo import RSCodec
from Queue import Queue

msg_queue = Queue()

class Transmitter:
    def __init__(self, compress=True, **kwargs):
        self.p = subprocess.Popen(['bin/minimodem', '-t', '-8',
            kwargs.get('baudmode', 'rtty')] + kwargs.get('extra_args', []),
            stdin=subprocess.PIPE)
        self.compress = compress

    def write(self, text):
        s = len(text)

        if self.compress:
            text = base64.b64encode(zlib.compress(text))
            print "Size before %d size after %d" % (s, len(text))

        rs = RSCodec(10)
        text = rs.encode(text)

        self.p.stdin.write(text)

    def close(self):
        self.p.stdin.close()
        self.p.wait()

class Consumer(threading.Thread):
    def __init__(self):
        pass

    def run(self):
        global msg_queue
        while True:
            msg = msg_queue.get()
            print "Consumed"
            print msg
            msg_queue.task_done()


class Receiver:
    class ReceiverReader(threading.Thread):
        def __init__(self, stdout, stderr, compress=True):
            threading.Thread.__init__(self)
            self.stdout = stdout
            self.stderr = stderr
            self.compress = compress

        def run(self):
            in_packet = False
            packet = ''
            global msg_queue
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
                        start = time.time()
                        in_packet = True
                        packet = ''
                    elif line.startswith('### NOCARRIER '):
                        in_packet = False
                        if len(packet) < 30:
                            continue
                        b = bytearray()
                        b.extend(packet)

                        rs = RSCodec(10)
                        packet = rs.decode(b)

                        if self.compress:
                            try:
                                packet = zlib.decompress(base64.b64decode(packet))
                            except:
                                pass

                        print 'Got packet: %s' % packet
                        msg_queue.put(packet)
                        end = time.time()
                        print "It took %s" % (end - start)

    def __init__(self, compress=True, **kwargs):
        self.p = subprocess.Popen(['bin/minimodem', '-r', '-8', '-A',
            kwargs.get('baudmode', 'rtty')] + kwargs.get('extra_args', []),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.compress = compress
        self.reader = Receiver.ReceiverReader(self.p.stdout, self.p.stderr, compress)
        self.reader.setDaemon(True)
        self.reader.start()


if __name__ == "__main__":
    use_compression = True
    baud = '3000'
    print "Start Receiver"
    receiver = Receiver(compress=use_compression, baudmode=baud)
    print "Start Consumer"
    consumer = Consumer()
    receiver.p.wait()





