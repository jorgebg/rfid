import serial, argparse, sys, Queue, collections, threading, signal, time

class Application(object):

    PORT = None
    BUFFER = 0
    CACHE = 5
    OUTDATE = 5*60
    WORD = 3
    DEBUG = False

    @classmethod
    def run(cls):
        cls = Application()
        args = cls.parse_args()

        cls.DEBUG = args.debug

        if args.scan:
            cls.action_scan()
        else:
            cls.PORT = args.port
            cls.BUFFER = args.buffer
            cls.CACHE = args.cache
            cls.WORD = args.word
            cls.action_run()


class Buffer(Queue.Queue):
    pass

class Cache(object):
    def __init__(self, size=0, outdate=0):
        self.items = collections.OrderedDict()
        self.size = size
        self.outdate = outdate

    def set(self, code, timestamp):
        old_timestamp = self.items.get(code)
        if not old_timestamp:
            if self.size is not 0 and len(self.items)>=self.size:
                self.items.popitem()
            self.items[code]=timestamp
            return True
        elif self.outdate is not 0 and old_timestamp+self.outdate < timestamp:
            del self.items[code]
            self.items[code]=timestamp
            return True
        else:
            return False


class RFIDConsumer(object):
    pass

class RFIDListener(argparse.ArgumentParser):

    def __init__(self):
        super(RFIDListener, self).__init__('Evolufarm RFID Listener')

        self.add_argument('-p', '--port',
            default=self.PORT, type=int,
            help='Serial port number, defaults to the first serial port available')
        self.add_argument('-b', '--buffer',
            default=self.BUFFER, type=int,
            help='Size of the buffer that queues the readed IDs, defaults to %s' % self.BUFFER)
        self.add_argument('-c', '--cache',
            default=self.CACHE, type=int,
            help='Size of the cache that stores the IDs timestamps, defaults to %s' % self.CACHE)
        self.add_argument('-o', '--outdate',
            default=self.CACHE, type=int,
            help='Time that the codes remain in the cache %s' % self.CACHE)
        self.add_argument('-w', '--word',
            default=self.WORD,  type=int,
            help='Number of bytes to read each iteration, defaults to %s' % self.WORD)
        self.add_argument('-d', '--debug',
            action='store_true',
            help='Enables debug')
        self.add_argument('-v', '--version',
            action='version', version='%(prog)s 2.0',
            help='Check program version')

        self.add_argument('-s', '--scan',
            action='store_true',
            help='Prints available serial ports (ignores the other arguments)')


    def action_scan(self):
        print 'Available ports: %s' % self._scan_available_ports()

    def _scan_available_ports(self, first=False):
        available = dict()
        for i in range(256):
            try:
                if self.DEBUG:
                    print 'Scanning %i' % i
                s = serial.Serial(i)
                available[i] = s.portstr
                if first:
                    break
                s.close()
            except serial.SerialException:
                pass
        return available


    def start(self, handler):
        # Get first available port if it hasn't been defined
        if self.PORT is None:
            ports = self._scan_available_ports(True)
            if len(ports) > 0:
                self.PORT = ports.keys()[0]
            else:
                sys.stderr.write('There are no available ports')
                sys.exit()

        # Handle Ctrl+C if debugging
        # if self.DEBUG:
            # def signal_handler(signal, frame):
                # print 'Ctrl+C Interrupt'
                # sys.exit(0)
            # signal.signal(signal.SIGINT, signal_handler)

        # Initialize queue & cache
        self.buffer = Buffer(self.BUFFER)
        self.cache = Cache(self.CACHE, self.OUTDATE)

        # Start queque consumer
        self.consumer = threading.Thread(target=self._worker)
        self.consumer.daemon = True
        self.consumer.start()

        # Connect and listen
        self.connection = serial.Serial(self.PORT)
        while True:
            try:
                data = self.connection.read(self.WORD)
            except serial.SerialException:
                data = None
            if len(data) > 0:
                timestamp = time.time()
                if self.DEBUG:
                    print 'Put ', data.encode('hex'), timestamp
                try:
                    self.buffer.put((data, timestamp))
                except Queue.Full:
                    pass

        self.connection.close()
        self.consuming = False
        self.consumer.join()


    def _consumer(self):
        while self.consuming:
            try:
                code, timestamp = self.buffer.get()
            except Queue.Empty:
                code = None
            if code:
                if self.DEBUG:
                    print 'Got ', code.encode('hex'), timestamp
                if self.cache.set(code, timestamp):
                    # TODO notify {{{
                    pass
                    # }}}
                self.buffer.task_done()



if __name__ == '__main__':
    Application.run()
