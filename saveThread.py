from threading import Thread, Event
import markovChaining

class saveThread (Thread):
    def __init__(self, time, callback, name):
        Thread.__init__(self)
        self.stop = Event()
        self.wait_time = time
        self.callback = callback
        self.daemon = True
        self.name = name
        print("Save thread starting")
        self.stop.set()

    def run(self):
        while not self.stop.wait(self.wait_time):
            self.callback()

def saveTable():
    print("dumping table...")
    markovChaining.dumpTable(markovChaining.TABLE_NAME)
    print("dumping complete.")

def stop():
    self.stop.clear()
