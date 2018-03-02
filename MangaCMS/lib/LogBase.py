
import logging
import threading
import abc

class LoggerMixin(metaclass=abc.ABCMeta):

	@abc.abstractmethod
	def logger_path(self):
		return None


	def __init__(self):
		self.loggers = {}
		self.lastLoggerIndex = 1


	@property
	def log(self):

		threadName = threading.current_thread().name
		if "Thread-" in threadName:
			if threadName not in self.loggers:
				self.loggers[threadName] = logging.getLogger("%s.Thread-%d" % (self.logger_path, self.lastLoggerIndex))
				self.lastLoggerIndex += 1

		# If we're not called in the context of a thread, just return the base log-path
		else:
			self.loggers[threadName] = logging.getLogger("Main.%s" % (self.logger_path,))
		return self.loggers[threadName]


class TestClass(LoggerMixin):
	logger_path = 'Main.Wat'

	def test(self):
		self.log.info("Wat?")



if __name__ == "__main__":
	print("Test mode!")
	import MangaCMS.lib.logSetup
	MangaCMS.lib.logSetup.initLogging()


	scraper = TestClass()
	print(scraper)
	extr = scraper.test()
	# print(extr['fLinks'])

