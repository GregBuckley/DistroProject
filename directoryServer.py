from flask import Flask, jsonify
from flask import abort
from flask import make_response
from flask import request
from flask import g
from OpenSSL import SSL
import requests
import copy
from random import randint
import sqlite3
import os

DIRECTORY = "\DIRECTORY_Server\\"
dirServer = Flask(__name__)
fileServers = {}
FILE_DATABASE = "dirserdb.db"


context = SSL.Context(SSL.SSLv23_METHOD)
cer = os.path.join(os.path.dirname(__file__), os.getcwd()+os.path.sep+'HTTPS CERTS'+os.path.sep+'Directory_Server'+os.path.sep+'server.crt')
key = os.path.join(os.path.dirname(__file__), os.getcwd()+os.path.sep+'HTTPS CERTS'+os.path.sep+'Directory_Server'+os.path.sep+'server.key')


#Recieve File
#Check if file has been sent before
#Update Pre existing file or write as new
#Put into all available file servers and update Database
@dirServer.route('/dirServer/upload', methods = ['POST'])
def recieve_File():
	if not request.form:
		return make_response(jsonify({"ERROR" : "NOT FOUND"}), 404)
	cd = get_cd()
	nameOfFile = request.form['fileName']
	data = request.form['fileName']
	print ("CD = " + cd+ os.path.sep + DIRECTORY) 
	hashValue = request.form['hashvalue']
	print("Data = %d", hashValue)

	#FIND IF FILE ALREADY EXISTS		
	connectionMaster = sqlite3.connect(FILE_DATABASE)
	cursorMaster = connectionMaster.cursor()
	cursorMaster.execute("SELECT master_server FROM fileDirectory WHERE filename = ?;", (nameOfFile,))
	master_server = cursorMaster.fetchall()
	RepServer=0
	Master=0
	if not master_server:
		print("Uploading file for first time")
		Master = randint(1,len(fileServers))
		RepServer = randint(1,len(fileServers))
		while (RepServer==Master):
			RepServer= randint(1,len(fileServers))
		addRowToDB(FILE_DATABASE,nameOfFile,Master,RepServer,hashValue)
	else:
		print("Updating existing file")
		Master = int(master_server[0][0])
		cursorMaster.execute("SELECT replicate_server FROM fileDirectory WHERE filename = ?;", (nameOfFile,))
		replicate_server = cursorMaster.fetchall()
		RepServer = int(replicate_server[0][0])	
		com = "UPDATE fileDirectory SET hashValue = ? WHERE filename = ?;"
		params = (hashValue,nameOfFile)
		cursorMaster.execute(com,params)
		connectionMaster.commit()
	printDB("fileDirectory", "dirserdb.db")	
	servers = {'Master' : fileServers[Master], 'Replicate' : fileServers[RepServer]}
	return make_response(jsonify(servers), 200)

#Create a database to track all files on system, their master and replicate server urls and the current hash value of the files.
def createDatabase():
	if (not os.path.isfile(FILE_DATABASE)):
		print ("Create DataBase %s" % FILE_DATABASE)
		connectionMaster = sqlite3.connect(FILE_DATABASE)
		cursorMaster = connectionMaster.cursor()
		#Create columns in Data Base
		sql_command = """CREATE TABLE fileDirectory ( filename VARCHAR(30) PRIMARY KEY, master_server VARCHAR(100),replicate_server VARCHAR(100) , hashValue VARCHAR (200));"""
		cursorMaster.execute(sql_command)
		connectionMaster.commit()

		#Add first values into database
		sql_command = "INSERT INTO fileDirectory VALUES(?,?,?,?);"
		params = ("File name", "master server name", "replicate server name", "hash value of file")
		cursorMaster.execute(sql_command, params)
		connectionMaster.commit()		
	else: 
		print ("DB %s already exits:" % FILE_DATABASE)
		#print database
		printDB("fileDirectory", "dirserdb.db")


#Returns the address of the file server for the client to contact to recieve their file
@dirServer.route('/dirServer/read', methods = ['GET'])
def get_Location_Of_File():
	responseDictionary = request.json
	filenameToGet= responseDictionary['file']
	connectionMaster = sqlite3.connect(FILE_DATABASE)
	cursorMaster = connectionMaster.cursor()
	cursorMaster.execute("SELECT master_server FROM fileDirectory WHERE filename = ?;", (filenameToGet,))
	master_server = cursorMaster.fetchall()
	print("master server is equal to = ")
	print(master_server)
	if (not master_server):
		print("Not HEYRE")
		abort(400)
	else:
		print(master_server)
		print("Server = ", master_server[0][0])
		return fileServers[int(master_server[0][0])], 200

#Returns the hash value of a file in the directory
@dirServer.route('/dirServer/returnHash', methods = ['GET'])
def get_Hash_Of_File():
	#responseDictionary = request.json
	filenameToGet = request.form['fileName']
	connectionMaster = sqlite3.connect(FILE_DATABASE)
	cursorMaster = connectionMaster.cursor()
	cursorMaster.execute("SELECT hashValue FROM fileDirectory WHERE filename = ?;", (filenameToGet,))
	HashValue = cursorMaster.fetchall()
	print(HashValue)
	if (not HashValue):
		print("Could not find file in database")
		abort(400)
	else:
		print("HashValue = ", HashValue[0][0])
		return HashValue[0][0], 200

#Add a new server to the system
@dirServer.route('/dirServer/addServer', methods = ['POST'])
def add_Server():
	#responseDictionary = request.json
	serverURL = request.form['serverURL']
	updateDict ={len(fileServers) +1 : serverURL}
	
	if(not serverURL in fileServers):
		fileServers.update(updateDict)
	else:
		print("Server Already Exists")

	for x in fileServers:
		print(fileServers[x])

	return "Server succesfully added", 200

#Print the database.
def printDB(nameOfDB, DataBase_NAME):
	connection = sqlite3.connect(DataBase_NAME)
	cursor = connection.cursor()
	cursor.execute("SELECT * FROM {}".format(nameOfDB))
	db = cursor.fetchall()
	print ("-------------------------------")
	for x in db:
		print (x)
	print ("-------------------------------")

#Adds a new file to the databale, taking in all parameters of the fileDirectory
def addRowToDB(nameOfDB, fileName,master,rep,hash):
	connectionMaster = sqlite3.connect(FILE_DATABASE)
	cursorMaster = connectionMaster.cursor()
	sql_command = "INSERT INTO fileDirectory VALUES(?,?,?,?);"
	params = (fileName, master, rep, hash)
	cursorMaster.execute(sql_command, params)
	connectionMaster.commit()	
	printDB("fileDirectory", nameOfDB)

def get_cd():
	res = os.getcwd()
	return res

if __name__ == '__main__':
	context = (cer,key)
	cwd = os.getcwd()
	createDatabase()
	if not os.path.isdir(cwd + os.path.sep + DIRECTORY):
		os.mkdir(cwd + os.path.sep + DIRECTORY)
	dirServer.run(host = 'localhost', port=5030, debug = False, ssl_context=context)


