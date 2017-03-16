

from .DbLoader import PururinDbLoader
from .ContentLoader import PururinContentLoader

import settings

import runStatus

import ScrapePlugins.RunBase

class Runner(ScrapePlugins.RunBase.ScraperBase):


	loggerPath = "Main.Manga.Pururin.Run"
	pluginName = "Pururin"


	sourceName = "Pururin"
	feedLoader = PururinDbLoader
	contentLoader = PururinContentLoader





if __name__ == "__main__":
	import utilities.testBase as tb

	with tb.testSetup():
		mon = Runner()
		mon.go()
