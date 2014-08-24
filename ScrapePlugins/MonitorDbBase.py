

import logging
import psycopg2
import abc
import traceback
import time
import settings
import nameTools as nt

class MonitorDbBase(metaclass=abc.ABCMeta):

	# Abstract class (must be subclassed)
	__metaclass__ = abc.ABCMeta



	@abc.abstractmethod
	def pluginName(self):
		return None

	@abc.abstractmethod
	def loggerPath(self):
		return None

	@abc.abstractmethod
	def dbName(self):
		return None

	@abc.abstractmethod
	def tableName(self):
		return None

	@abc.abstractmethod
	def nameMapTableName(self):
		return None





	def __init__(self):
		self.log = logging.getLogger(self.loggerPath)
		self.log.info("Loading %s Monitor BaseClass", self.pluginName)
		self.openDB()
		self.checkInitPrimaryDb()

		self.validKwargs  = ["buName",
							"buId",
							"buTags",
							"buGenre",
							"buList",

							"buArtist",
							"buAuthor",
							"buOriginState",
							"buDescription",
							"buRelState",

							"readingProgress",
							"availProgress",
							"rating",
							"lastChanged",
							"lastChecked",
							"itemAdded"]

		self.validColName = ["dbId",
							"buName",
							"buId",
							"buTags",
							"buGenre",
							"buList",

							"buArtist",
							"buAuthor",
							"buOriginState",
							"buDescription",
							"buRelState",

							"readingProgress",
							"availProgress",
							"rating",
							"lastChanged",
							"lastChecked",
							"itemAdded"]

	def openDB(self):
		self.log.info("Opening DB...",)
		self.conn = psycopg2.connect(dbname=settings.DATABASE_DB_NAME, user=settings.DATABASE_USER,password=settings.DATABASE_PASS)

		self.log.info("DB opened.")

	def closeDB(self):
		self.log.info("Closing DB...",)
		self.conn.close()
		self.log.info("DB Closed")


	# ---------------------------------------------------------------------------------------------------------------------------------------------------------
	# DB Tools
	# ---------------------------------------------------------------------------------------------------------------------------------------------------------
	# Operations are MASSIVELY faster if you set commit=False (it doesn't flush the write to disk), but that can open a transaction which locks the DB.
	# Only pass commit=False if the calling code can gaurantee it'll call commit() itself within a reasonable timeframe.


	def buildInsertArgs(self, **kwargs):

		keys = []
		values = []
		queryAdditionalArgs = []
		for key in kwargs.keys():
			if key not in self.validKwargs:
				raise ValueError("Invalid keyword argument: %s" % key)
			keys.append("{key}".format(key=key))
			values.append("%s")
			queryAdditionalArgs.append("{s}".format(s=kwargs[key]))

		keysStr = ",".join(keys)
		valuesStr = ",".join(values)

		return keysStr, valuesStr, queryAdditionalArgs


	# Insert new item into DB.
	# MASSIVELY faster if you set commit=False (it doesn't flush the write to disk), but that can open a transaction which locks the DB.
	# Only pass commit=False if the calling code can gaurantee it'll call commit() itself within a reasonable timeframe.
	def insertIntoDb(self, commit=True, **kwargs):
		cur = self.conn.cursor()
		keysStr, valuesStr, queryAdditionalArgs = self.buildInsertArgs(**kwargs)

		query = '''INSERT INTO {tableName} ({keys}) VALUES ({values});'''.format(tableName=self.tableName, keys=keysStr, values=valuesStr)

		# print("Query = ", query, queryAdditionalArgs)

		cur.execute(query, queryAdditionalArgs)

		if commit:
			self.conn.commit()


	# Update entry with key sourceUrl with values **kwargs
	# kwarg names are checked for validity, and to prevent possiblity of sql injection.
	def updateDbEntry(self, dbId, commit=True, **kwargs):


		queries = []
		qArgs = []

		row = self.getRowByValue(dbId=dbId)
		if not row:
			raise ValueError("Trying to update a row that doesn't exist!")

		if len(kwargs) == 0:
			raise ValueError("You must pass something to update!")
		for key in kwargs.keys():
			if key not in self.validKwargs:
				raise ValueError("Invalid keyword argument: %s" % key)
			else:
				queries.append("{k}=%s".format(k=key))
				qArgs.append(kwargs[key])

		qArgs.append(dbId)
		column = ", ".join(queries)

		cur = self.conn.cursor()

		query = '''UPDATE {t} SET {v} WHERE dbId=%s;'''.format(t=self.tableName, v=column)
		cur.execute(query, qArgs)


		if commit:
			self.conn.commit()

	def deleteRowById(self, rowId, commit=True):

		cur = self.conn.cursor()


		query = ''' DELETE FROM {tableN} WHERE dbId=%s;'''.format(tableN=self.tableName)
		qArgs = (rowId, )
		cur.execute(query, qArgs)

		if commit:
			self.conn.commit()

	def getRowsByValue(self, **kwargs):
		if len(kwargs) != 1:
			raise ValueError("getRowsByValue only supports calling with a single kwarg", kwargs)
		validCols = ["dbId", "buName", "buId"]
		key, val = kwargs.popitem()
		if key not in validCols:
			raise ValueError("Invalid column query: %s" % key)

		cur = self.conn.cursor()

		# work around the auto-cast of numeric strings to integers
		typeSpecifier = ''
		if key == "buId":
			typeSpecifier = '::TEXT'


		query = '''SELECT {cols} FROM {tableN} WHERE {key}=%s{type};'''.format(cols=", ".join(self.validColName), tableN=self.tableName, key=key, type=typeSpecifier)
		# print("Query = ", query)
		cur.execute(query, (val, ))

		rets = cur.fetchall()
		retL = []
		if rets:
			keys = self.validColName
			for ret in rets:
				retL.append(dict(zip(keys, ret)))
		return retL

	def getRowByValue(self, **kwargs):
		rows = self.getRowsByValue(**kwargs)
		if len(rows) == 1:
			return rows.pop()
		if len(rows) == 0:
			return None
		else:
			raise ValueError("Got multiple rows for selection. Wat?")



	def getColumnItems(self, colName):
		cur = self.conn.cursor()
		if not colName in self.validColName:
			raise ValueError("getColumn must be called with a valid column name", colName)

		query = ''' SELECT ({colName}) FROM {tableN};'''.format(colName=colName, tableN=self.tableName)
		ret = cur.execute(query)

		rets = cur.fetchall()
		retL = []
		if rets:
			for item in rets:
				retL.append(item[0])
		return retL

	def mergeItems(self, fromDict, toDict):
		validMergeKeys = ["dbId", "buName", "buId"]
		for modeDict in [fromDict, toDict]:
			if len(modeDict) != 1:
				raise ValueError("Each selector item must only be a single item long!")
			for key in modeDict.keys():
				if key not in modeDict:
					raise ValueError("Invalid column name {name}. Column name must be one of {validNames}!".format(name=key, validNames=validMergeKeys))

		# At this point, we know we have theoretically valid DB keys. Now, to check the actual values are even valid.


		fromRow = self.getRowByValue(**fromDict)
		toRow   = self.getRowByValue(**toDict)

		if not fromRow:
			raise ValueError("FromRow has no corresponding value in the dictionary! FromRow={row1}".format(row1=fromRow, row2=toRow))
		if not toRow:
			raise ValueError("ToRow has no corresponding value in the dictionary! ToRow={row2}".format(row1=fromRow, row2=toRow))

		# self.printDict(fromRow)
		# self.printDict(toRow)
		if fromRow['dbId'] == toRow['dbId']:
			raise ValueError("Trying to merge row with itself? Error.")

		noCopyKeys = ["dbId"]
		takeLarger = ["rating", "lastChanged"]
		for key in fromRow.keys():
			if key in noCopyKeys:
				continue


			elif key in takeLarger:
				if toRow[key] and fromRow[key]:
					if fromRow[key] > toRow[key]:
						toRow[key] = fromRow[key]
				elif fromRow[key]:
					toRow[key] = fromRow[key]
			else:
				if fromRow[key] != None:
					toRow[key] = fromRow[key]

		# self.printDict(toRow)
		try:
			dbId = toRow["dbId"]
			toRow.pop("dbId")
			self.conn.commit()
			self.deleteRowById(fromRow["dbId"], commit=False)
			self.updateDbEntry(dbId, commit=False, **toRow)
			self.conn.commit()

		except (psycopg2.OperationalError, psycopg2.IntegrityError) as e:
			self.log.critical("Encountered error!")
			self.log.critical(e)
			traceback.print_exc()
			self.conn.rollback()
			self.log.critical("Rolled back")
			raise e

	def printDict(self, inDict):
		keys = list(inDict.keys())
		keys.sort()
		print("Dict ------")
		for key in keys:
			keyStr = "{key}".format(key=key)
			print("	", keyStr, " "*(20-len(keyStr)), inDict[key])

	def printDb(self):
		cur = self.conn.cursor()
		ret = cur.execute('SELECT * FROM {db};'.format(db=self.tableName))
		for line in cur.fetchall():
			print(line)


	def insertBareNameItems(self, items):

		cur = self.conn.cursor()
		print("Items", items)
		for name, mId in items:
			row = self.getRowByValue(buId=mId)
			if row:
				if name.lower() != row["buName"].lower():
					self.log.warning("Name disconnect!")
					self.log.warning("New name='%s', old name='%s'.", name, row["buName"])
					self.log.warning("Whole row=%s", row)
					self.updateDbEntry(row["dbId"], buName=name, commit=False)

			else:
				row = self.getRowByValue(buName=name)
				if row:
					self.log.error("Conflicting with existing series?")
					self.log.error("Existing row = %s, %s", row["buName"], row["buId"])
					self.log.error("Current item = %s, %s", name, mId)
					self.updateDbEntry(row["dbId"], buName=name, commit=False)
				else:
					self.insertIntoDb(buName=name,
									buId=mId,
									lastChanged=0,
									lastChecked=0,
									itemAdded=time.time(),
									commit=False)
				# cur.execute("""INSERT INTO %s (buId, name)VALUES (?, ?);""" % self.nameMapTableName, (buId, name))

		self.conn.commit()

	def insertNames(self, buId, names):

		cur = self.conn.cursor()
		for name in names:
			fsSafeName = nt.prepFilenameForMatching(name)
			cur.execute("""SELECT COUNT(*) FROM %s WHERE buId=%%s AND name=%%s;""" % self.nameMapTableName, (buId, name))
			ret = cur.fetchall()
			if not ret:
				cur.execute("""INSERT INTO %s (buId, name, fsSafeName) VALUES (%%s, %%s, %%s);""" % self.nameMapTableName, (buId, name, fsSafeName))


	def getIdFromName(self, name):

		cur = self.conn.cursor()
		ret = cur.execute("""SELECT buId FROM %s WHERE name=%%s;""" % self.nameMapTableName, (name, ))
		ret = cur.fetchall()
		if ret:
			if len(ret[0]) != 1:
				raise ValueError("Have ambiguous name. Cannot definitively link to manga series.")
			return ret[0][0]
		else:
			return None

	def getIdFromDirName(self, fsSafeName):

		cur = self.conn.cursor()
		ret = cur.execute("""SELECT buId FROM %s WHERE fsSafeName=%%s;""" % self.nameMapTableName, (fsSafeName, ))
		ret = cur.fetchall()
		if ret:
			if len(ret[0]) != 1:
				raise ValueError("Have ambiguous fsSafeName. Cannot definitively link to manga series.")
			return ret[0][0]
		else:
			return None

	def getNamesFromId(self, mId):

		cur = self.conn.cursor()
		ret = cur.execute("""SELECT name FROM %s WHERE buId=%%s::TEXT;""" % self.nameMapTableName, (mId, ))
		ret = cur.fetchall()
		if ret:
			return ret
		else:
			return None




	def getLastCheckedFromId(self, mId):

		cur = self.conn.cursor()
		ret = cur.execute("""SELECT lastChecked FROM %s WHERE buId=%%s::TEXT;""" % self.tableName, (mId, ))
		ret = cur.fetchall()
		if len(ret) > 1:
			raise ValueError("How did you get more then one buId?")
		if ret:
			# Return structure is [(time)]
			# we want to just return time
			return ret[0][0]
		else:
			return None


	def updateLastCheckedFromId(self, mId, changed):
		cur = self.conn.cursor()
		cur.execute("""UPDATE %s SET lastChecked=%%s WHERE buId=%%s::TEXT;""" % self.tableName, (changed, mId))
		self.conn.commit()




	# ---------------------------------------------------------------------------------------------------------------------------------------------------------
	# DB Management
	# ---------------------------------------------------------------------------------------------------------------------------------------------------------


	def checkInitPrimaryDb(self):

		self.log.info( "Content Retreiver Opening DB...",)
		cur = self.conn.cursor()
		## LastChanged is when the last scanlation release was released
		# Last checked is when the page was actually last scanned.
		cur.execute('''CREATE TABLE IF NOT EXISTS %s (
											dbId            SERIAL PRIMARY KEY,

											buName          text,
											buId            text,
											buTags          text,
											buGenre         text,
											buList          text,

											buArtist        text,
											buAuthor        text,
											buOriginState   text,
											buDescription   text,
											buRelState      text,

											readingProgress int,
											availProgress   int,

											rating          int,
											lastChanged     double precision,
											lastChecked     double precision,
											itemAdded       double precision NOT NULL
											);''' % self.tableName)

		cur.execute("SELECT relname FROM pg_class;")
		haveIndexes = cur.fetchall()
		haveIndexes = [index[0] for index in haveIndexes]



		indexes = [	("%s_lastChanged_index"  % self.tableName, self.tableName, '''CREATE INDEX %s ON %s (lastChanged)'''),
					("%s_lastChecked_index"  % self.tableName, self.tableName, '''CREATE INDEX %s ON %s (lastChecked)'''),
					("%s_itemAdded_index"    % self.tableName, self.tableName, '''CREATE INDEX %s ON %s (itemAdded)'''  ),
					("%s_rating_index"       % self.tableName, self.tableName, '''CREATE INDEX %s ON %s (rating)'''     ),
					("%s_buName_index"       % self.tableName, self.tableName, '''CREATE INDEX %s ON %s (buName)''' ),
					("%s_buId_index"         % self.tableName, self.tableName, '''CREATE INDEX %s ON %s (buId  )''' ),
					("%s_buTags_index"       % self.tableName, self.tableName, '''CREATE INDEX %s ON %s (buTags)''' ),
					("%s_buGenre_index"      % self.tableName, self.tableName, '''CREATE INDEX %s ON %s (buGenre)''')
		]
		for name, table, nameFormat in indexes:
			if not name.lower() in haveIndexes:
				cur.execute(nameFormat % (name, table))


		cur.execute('''CREATE TABLE IF NOT EXISTS %s (
											dbId            SERIAL PRIMARY KEY,
											buId            text,
											name            text,
											fsSafeName      text,
											FOREIGN KEY(buId) REFERENCES %s(buId),
											UNIQUE(buId, name)
											);''' % (self.nameMapTableName, self.tableName))



		indexes = [	("%s_nameTable_buId_index"      % self.nameMapTableName, self.tableName,'''CREATE INDEX %s ON %s (buId      )'''       ),
					("%s_nameTable_name_index"      % self.nameMapTableName, self.tableName,'''CREATE INDEX %s ON %s (name      )'''       ),
					("%s_fSafeName_name_index"      % self.nameMapTableName, self.tableName,'''CREATE INDEX %s ON %s (fsSafeName, name)''' ),
					("%s_fSafeName_name_index"      % self.nameMapTableName, self.tableName,'''CREATE INDEX %s ON %s (fsSafeName)'''       )
		]

		for name, table, nameFormat in indexes:
			if not name.lower() in haveIndexes:
				cur.execute(nameFormat % (name, table))


		self.conn.commit()
		self.log.info("Retreived page database created")

	@abc.abstractmethod
	def go(self):
		pass
