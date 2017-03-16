

from .FeedLoader import FeedLoader
from .ContentLoader import ContentLoader

import ScrapePlugins.RunBase

import time

import runStatus


class Runner(ScrapePlugins.RunBase.ScraperBase):
	loggerPath = "Main.Manga.Kw.Run"

	pluginName = "kawaii"


	def _go(self):

		self.log.info("Checking Kw feeds for updates")
		fl = FeedLoader()
		fl.go()

		time.sleep(3)
		#print "wat", cl

		if not runStatus.run:
			return

		cl = ContentLoader()

		if not runStatus.run:
			return

		todo = cl.retreiveTodoLinksFromDB()

		if not runStatus.run:
			return

		cl.processTodoLinks(todo)


if __name__ == "__main__":
	import utilities.testBase as tb

	with tb.testSetup():

		run = Runner()
		run.go()