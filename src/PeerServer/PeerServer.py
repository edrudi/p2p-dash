#!/usr/bin/python
import http.server
import socketserver
import json
import os
import time
import base64
import pathlib
import re
import requests
import threading
from FileHandler import storeSegment, removeSegmentFromFileSystem, clearFileSystem

class SegmentDict(object) :
	
	SEGMENT_TABLE = {}  # segment_name : metadata
	
	#TODO: check expiration date and use it to do something clever?
	def exists(self, name) :
		if (self.SEGMENT_TABLE.get(name) == None ) :
			#print("Segment named " + name + " does NOT exists :(\n")
			return False
		return True 
	
	
	#Return:  True if the segment is new, False if the segment was already registered in the table 
	def update(self, data) :
		name = data["segmentName"]
		if (self.exists(name)) :   # -> segment already registered in table
			print("Segment named " + name + " already exists so NO NEED to create a file on the File System\n")
			#TODO
			return False 
		else :
			metadata = {"time" : time.monotonic(), "isRegistered" : False }
			self.SEGMENT_TABLE[name] = metadata
			#print(self.SEGMENT_TABLE)
			return True
	
	
	def getRegistrationList(self) :
		segments = []
		for key, metadata in self.SEGMENT_TABLE.items() :
			if not metadata["isRegistered"] :
				segments.append(key)
				
		return segments
	
	def setRegistrationFlag(self, segments) :
		for s in segments :
			self.SEGMENT_TABLE[s]["isRegistered"] = True
	
	
	def getExpiredSegments(self, max_time) :
		segments = []
		for key, metadata in self.SEGMENT_TABLE.items() :
			elapsed_time = time.monotonic() - metadata["time"] 
			if elapsed_time >=  max_time :
				segments.append(key)
		return segments
		
	def removeSegment(self, s) :
		if self.SEGMENT_TABLE.get(s) != None :
			del self.SEGMENT_TABLE[s]
			return True
		return False

#Default Configuration:
CS_IP = "localhost"
CS_PORT = 8080
IP = "localhost"
PORT = 8060
TIME_UNIT = 10          #<--- Controller Thread is executed every TIME_UNIT seconds
REGISTRATION_UNIT = 60  #<--- Controller Thread register new segments to CS every REGISTRATION_UNIT seconds.
REMOVE_UNIT = 120       #<--- Controller Thread remove segments from file system every REMOVE_UNIT seconds.


#Override default configuration with user configuration (config.json)
f = open("config.json", "r")
config = json.load(f)
CS_IP = config["CS"].get("HOST", CS_IP)
CS_PORT = config["CS"].get("PORT", CS_PORT)
IP = config["NODE"].get("HOST", IP)
PORT = config["NODE"].get("PORT", PORT)
TIME_UNIT = config["NODE"].get("TIME_UNIT", TIME_UNIT)
REGISTRATION_UNIT = config["NODE"].get("REGISTRATION_UNIT", REGISTRATION_UNIT)
REMOVE_UNIT = config["NODE"].get("REMOVE_UNIT", REMOVE_UNIT)

#REGISTRATION_UNIT and REMOVE_UNIT must be multiple of TIME_UNIT
if REGISTRATION_UNIT < TIME_UNIT :
	REGISTRATION_UNIT = TIME_UNIT
if REMOVE_UNIT < TIME_UNIT :
	REMOVE_UNIT = TIME_UNIT
	
if ((REGISTRATION_UNIT % TIME_UNIT) != 0 ) :
	REGISTRATION_UNIT = (REGISTRATION_UNIT // TIME_UNIT)*TIME_UNIT   #<-- floor division
if ((REMOVE_UNIT % TIME_UNIT) != 0 ) :
	REMOVE_UNIT = (REMOVE_UNIT // TIME_UNIT)*TIME_UNIT   #<-- floor division

print("\nStarting PeerServer with the following configuration parameter:")
print("CS_IP : " + CS_IP)
print("CS_PORT : " + str(CS_PORT))
print("IP : " + IP)
print("PORT : " + str(PORT))
print("TIME_UNIT : " + str(TIME_UNIT))
print("REGISTRATION_UNIT : " + str(REGISTRATION_UNIT))
print("REMOVE_UNIT : " + str(REMOVE_UNIT))

#Shared resources
SEGMENT_TABLE = SegmentDict()

#Global variable
PEER_ADDRESS = IP + ":" + str(PORT)
CS_ADDRESS = CS_IP + ":" + str(CS_PORT)
CS_ADD = "http://" + CS_ADDRESS + "/ADD_MEDIA"
CS_REMOVE = "http://" + CS_ADDRESS + "/REMOVE_NODE"
CS_EXPIRED = "http://" + CS_ADDRESS +  "/EXPIRED_LINKS"


#Create MEDIA folder if it does not exists
if not os.path.isdir("MEDIA") :
    os.mkdir("MEDIA")



#Closure to create a RequestHandler class with custom parameter (to
# overcome Subclassing limitation)
def RequestsHandlerFactory(tablelock, fslock) :
	
	class CORSRequestsHandler(http.server.SimpleHTTPRequestHandler):
        	
        	def __init__(self, *args, **kwargs):
        		self.tablelock = tablelock
        		self.fslock = fslock
        		super().__init__(*args, **kwargs)
        		
        	def do_GET(self):
        		if self.path.endswith("/PING"):
        			self.send_response(200)
        			self.end_headers()
        		else:
        			self.send_response(200)
        			self.send_header('Access-Control-Allow-Origin', '*')
        			# @TODO critical section : access to the File System
        			self.fslock.acquire()
        			super().do_GET()
        			self.fslock.release()
        			# end of critical section
        	
        	def do_POST(self):
        		if self.path.endswith("/ADD_SEGMENT"):
        			content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
        			post_data = self.rfile.read(content_length) # <--- Gets the data itself
        			data = json.loads(post_data) # <--- Gets Dict from Json Obj
        			
        			self.tablelock.acquire()
        			isNew = SEGMENT_TABLE.update(data)
        			self.tablelock.release()
        			
        			if (isNew) :   # <--- Received NEW segment ?
        				
        				raw_data = base64.urlsafe_b64decode(data["segment"]) # <--- decode from Base64url
        				name = data["segmentName"]
        				print("New segment received : " + name)
        				# @TODO critical section : access to the File System
        				self.fslock.acquire()
        				storeSegment(name, raw_data) # <--- save segment on the File System
        				self.fslock.release()
        				# end of critical section
        			self.send_response(200)
        			self.end_headers()
        		else :
        			print("Received unsupported POST request : " + self.path)
        			self.send_error(501, "Operation not implemented")
        			self.end_headers()
        
	
	return CORSRequestsHandler

#Server Thread Code to execute			
def ServerCode(httpd) :
	
	print("PEERSERVER: started serving at " + str(httpd.server_address))
	httpd.serve_forever()



def buildRegistrationBody(myaddr, segments) :
	body = {"addr" : myaddr}
	for s in segments :
		movie = s[1:].split("/")[1]
		if body.get(movie) == None :
			body[movie] = [s[1:]]
		else :
			body[movie].append(s[1:])
	
	return body

def buildExpiredBody(myaddr, segments) :
	body = {"addr" : myaddr}
	expired_s = []
	for s in segments :
		expired_s.append(s[1:])
	body["segments"] = expired_s
	
	return body

#Controller Thread Code to execute
def ControllerCode(tablelock, fslock, myaddr, stopEvent) :
	
	#time_unit = TIME_UNIT
	#registration_unit = REGISTRATION_UNIT
	#remove_segment_unit = REMOVE_UNIT
	current_time = 0
	
	while True :
		time.sleep(TIME_UNIT)
		current_time += TIME_UNIT
		
		if (stopEvent.is_set()) : return  # <--- Stop controller when program is terminating
		
		print("CONTROLLER: Current time - " + str(current_time))
		if (current_time % REGISTRATION_UNIT == 0) : # <--- time to register newly acquired segments on the CS
			print("CONTROLLER: Registration time!")
			tablelock.acquire()
			seg_list = SEGMENT_TABLE.getRegistrationList()
			tablelock.release()
			
			if not seg_list :
				print("CONTROLLER: No unregistered segments found :)")
			else :
				body = buildRegistrationBody(myaddr, seg_list)
				jsonObj = json.dumps(body)
				print("CONTROLLER: registration of the following segments on the CS ")
				print(jsonObj)
				#HTTP post with json obj
				r = requests.post(CS_ADD, data = jsonObj)
				print("status request: ")
				print(r.status_code)
				#Update TABLE
				tablelock.acquire()
				SEGMENT_TABLE.setRegistrationFlag(seg_list)
				tablelock.release()
		
		if (current_time % REMOVE_UNIT == 0) :
			print("CONTROLLER: It's time to remove old segments!")
			#which segment to remove?
			tablelock.acquire()
			exp_list = SEGMENT_TABLE.getExpiredSegments(REMOVE_UNIT)
			tablelock.release()
			print("expired segments to remove: ")
			print(exp_list)
			for e in exp_list :
				#to avoid deadlock always acquire in the same order
				tablelock.acquire()
				fslock.acquire()
				removeSegmentFromFileSystem(e)
				SEGMENT_TABLE.removeSegment(e)
				fslock.release()
				tablelock.release()
			
			print("CONTROLLER: removed " + str(len(exp_list)) + " segments!")
			if exp_list :      #<- if not empty
				print("CONTROLLER: notify the CS about segments no more available")
				body = buildExpiredBody(myaddr, exp_list)
				jsonObj = json.dumps(body)
				r = requests.post(CS_EXPIRED, data = jsonObj)
				print("status request: ")
				print(r.status_code)
			#reset counter
			current_time = 0
		print("CONTROLLER: ALL DONE :)")
	


# Locks for shared resources in critical sections
# NOTE to avoid deadlock: in case you need both locks ALWAYS acquire in the same order
#    e.g, first the tablelock and then the fslock
tablelock = threading.Lock()
fslock = threading.Lock()

#Exit condition for Controller Thread
stopEvent = threading.Event()

#Server thread preparation
handler = RequestsHandlerFactory(tablelock, fslock)
httpd = socketserver.TCPServer((IP, PORT), handler)
t1 = threading.Thread(target=ServerCode, args=(httpd,))

#Controller thread preparation
t2 = threading.Thread(target=ControllerCode, args=(tablelock, fslock, PEER_ADDRESS, stopEvent))

# starting threads
t1.start()
t2.start()


try :
	t1.join()
	stopEvent.set()
	t2.join()

except KeyboardInterrupt:
	print("\nEXCEPT : KeyboardInterrupt in the Main Process")
	#Remove from CS
	jsonObj = json.dumps({"addr" : PEER_ADDRESS})
	print("Sending a REMOVE_NODE to CS with json body = " + jsonObj)
	r = requests.post( CS_REMOVE, data = jsonObj)
	#shutdown the server
	httpd.shutdown()
	print("EXCEPT : Server shutdown complete")
	print("EXCEPT : Stopping Controller... (may require some time)")
	#stop the controller
	stopEvent.set()
	t2.join()
	print("EXCEPT : Controller stopped")
	#clearing File System from residual segments before terminating
	print("EXCEPT : Clearing File System from residual segments...")
	clearFileSystem("MEDIA/")

print("All done :)")
