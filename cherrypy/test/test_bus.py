from cherrypy.test import test
test.prefer_parent_path()

import unittest

import cherrypy
from cherrypy.process import wspbus


msg = "Listener %d on channel %s: %s."


class PublishSubscribeTests(unittest.TestCase):

    def get_listener(self, channel, index):
        def listener(arg=None):
            self.responses.append(msg % (index, channel, arg))
        return listener
    
    def test_builtin_channels(self):
        b = wspbus.Bus()
        
        self.responses, expected = [], []
        
        for channel in b.listeners:
            for index, priority in enumerate([100, 50, 0, 51]):
                b.subscribe(channel, self.get_listener(channel, index), priority)
        
        for channel in b.listeners:
            b.publish(channel)
            expected.extend([msg % (i, channel, None) for i in (2, 1, 3, 0)])
            b.publish(channel, arg=79347)
            expected.extend([msg % (i, channel, 79347) for i in (2, 1, 3, 0)])
        
        self.assertEqual(self.responses, expected)
    
    def test_custom_channels(self):
        b = wspbus.Bus()
        
        self.responses, expected = [], []
        
        custom_listeners = ('hugh', 'louis', 'dewey')
        for channel in custom_listeners:
            for index, priority in enumerate([None, 10, 60, 40]):
                b.subscribe(channel, self.get_listener(channel, index), priority)
        
        for channel in custom_listeners:
            b.publish(channel, 'ah so')
            expected.extend([msg % (i, channel, 'ah so') for i in (1, 3, 0, 2)])
            b.publish(channel)
            expected.extend([msg % (i, channel, None) for i in (1, 3, 0, 2)])
        
        self.assertEqual(self.responses, expected)
    
    def test_listener_errors(self):
        b = wspbus.Bus()
        
        self.responses, expected = [], []
        channels = [c for c in b.listeners if c != 'log']
        
        for channel in channels:
            b.subscribe(channel, self.get_listener(channel, 1))
            # This will break since the lambda takes no args.
            b.subscribe(channel, lambda: None, priority=20)
        
        for channel in channels:
            self.assertRaises(TypeError, b.publish, channel, 123)
            expected.append(msg % (1, channel, 123))
        
        self.assertEqual(self.responses, expected)


class BusMethodTests(unittest.TestCase):
    
    def log(self, bus):
        self._log_entries = []
        def logit(msg, level):
            self._log_entries.append(msg)
        bus.subscribe('log', logit)
    
    def assertLog(self, entries):
        self.assertEqual(self._log_entries, entries)
    
    def get_listener(self, channel, index):
        def listener(arg=None):
            self.responses.append(msg % (index, channel, arg))
        return listener
    
    def test_start(self):
        b = wspbus.Bus()
        self.log(b)
        
        self.responses = []
        num = 3
        for index in range(num):
            b.subscribe('start', self.get_listener('start', index))
        
        b.start()
        try:
            # The start method MUST call all 'start' listeners.
            self.assertEqual(set(self.responses),
                             set([msg % (i, 'start', None) for i in range(num)]))
            # The start method MUST move the state to STARTED
            # (or EXITING, if errors occur)
            self.assertEqual(b.state, b.states.STARTED)
            # The start method MUST log its states.
            self.assertLog(['Bus STARTING', 'Bus STARTED'])
        finally:
            # Exit so the atexit handler doesn't complain.
            b.exit()
    
    def test_stop(self):
        b = wspbus.Bus()
        self.log(b)
        
        self.responses = []
        num = 3
        for index in range(num):
            b.subscribe('stop', self.get_listener('stop', index))
        
        b.stop()
        
        # The stop method MUST call all 'stop' listeners.
        self.assertEqual(set(self.responses),
                         set([msg % (i, 'stop', None) for i in range(num)]))
        # The stop method MUST move the state to STOPPED
        self.assertEqual(b.state, b.states.STOPPED)
        # The stop method MUST log its states.
        self.assertLog(['Bus STOPPING', 'Bus STOPPED'])
    
    def test_graceful(self):
        b = wspbus.Bus()
        self.log(b)
        
        self.responses = []
        num = 3
        for index in range(num):
            b.subscribe('graceful', self.get_listener('graceful', index))
        
        b.graceful()
        
        # The graceful method MUST call all 'graceful' listeners.
        self.assertEqual(set(self.responses),
                         set([msg % (i, 'graceful', None) for i in range(num)]))
        # The graceful method MUST log its states.
        self.assertLog(['Bus graceful'])
    
    def test_exit(self):
        b = wspbus.Bus()
        self.log(b)
        
        self.responses = []
        num = 3
        for index in range(num):
            b.subscribe('stop', self.get_listener('stop', index))
            b.subscribe('exit', self.get_listener('exit', index))
        
        b.exit()
        
        # The exit method MUST call all 'stop' listeners,
        # and then all 'exit' listeners.
        self.assertEqual(set(self.responses),
                         set([msg % (i, 'stop', None) for i in range(num)] +
                             [msg % (i, 'exit', None) for i in range(num)]))
        # The exit method MUST move the state to EXITING
        self.assertEqual(b.state, b.states.EXITING)
        # The exit method MUST log its states.
        self.assertLog(['Bus STOPPING', 'Bus STOPPED', 'Bus EXITING', 'Bus EXITED'])
    
    # TODO: restart, block, wait, start_with_callback, log


if __name__ == "__main__":
    setup_server()
    helper.testmain()
