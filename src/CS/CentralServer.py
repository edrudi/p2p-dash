#!/usr/bin/python
import http.server
import socketserver
import json
import threading
import requests
import time
from lookup import LookupDict
from mediaMapper import MediaMap

#Default Configuration:
CS_IP = "localhost"
CS_PORT = 8080
TIME_UNIT = 10  #<--- Monitor Thread is executed every TIME_UNIT seconds
PING_UNIT = 20  #<--- Monitor Thread ping Servers every PING_UNIT seconds. PING_UNIT must be multiple of TIME_UNIT

#Override default configuration with user configuration (config.json)
f = open("config.json", "r")
config = json.load(f)
CS_IP = config["NODE"].get("HOST", CS_IP)
CS_PORT = config["NODE"].get("PORT", CS_PORT)
TIME_UNIT = config["NODE"].get("TIME_UNIT", TIME_UNIT)
PING_UNIT = config["NODE"].get("PING_UNIT", PING_UNIT)

#PING UNIT must be multiple of TIME_UNIT
if PING_UNIT < TIME_UNIT :
	PING_UNIT = TIME_UNIT

if ((PING_UNIT % TIME_UNIT) != 0 ) :
	PING_UNIT = (PING_UNIT // TIME_UNIT)*TIME_UNIT   #<-- integer division not supported in python3, use floor division


print("\nStarting CS with the following configuration parameter:")
print("CS_IP : " + CS_IP)
print("CS_PORT : " + str(CS_PORT))
print("TIME_UNIT : " + str(TIME_UNIT))
print("PING_UNIT : " + str(PING_UNIT))

#Global variable
MY_ADDR = CS_IP + ":" + str(CS_PORT)
CS_REMOVE = "http://" + MY_ADDR + "/REMOVE_NODE"
#---> Lookup Dictionary
utils = LookupDict()
#---> Segment - Media Mapping
mmap = MediaMap()


#Closure to create a RequestHandler class with custom parameter (to
# overcome Subclassing limitation)
def RequestsHandlerFactory(tablelock) :
	
	class CORSRequestsHandler(http.server.SimpleHTTPRequestHandler):
		
		def __init__(self, *args, **kwargs):
			self.tablelock = tablelock
			super().__init__(*args, **kwargs)
		
		def end_headers(self):
			self.send_header('Access-Control-Allow-Origin', '*')
			super().end_headers()
		
		def do_GET(self):
			if self.path.endswith(".mpd"):
				print("serving the mpd :" + self.path)	
				super().do_GET()
			
			elif self.path.endswith("/GET_AVAILABLE_MEDIA"):
				movies = mmap.getMediaList()
				availables = mmap.getlistOfAvailableMedia()
				response = {}
				for m in movies :
					if m in availables :
						MPD_URL = "http://" + MY_ADDR + "/MEDIA/" + m + "/" + m + ".mpd"
						response[m] = MPD_URL
					else :
						response[m] = "NO"
				#Dict to JSON
				jsonObj = json.dumps(response)
				self.send_response(200)
				self.send_header('Content-Type', 'application/json')
				self.end_headers()
				self.wfile.write(jsonObj.encode(encoding='utf_8'))
				
			elif self.path.startswith("/MEDIA/"):
				#print(self.path[1:])
				#redirection
				searchKey = self.path[1:]  #remove first char from path as it is a '/' from uri adrr convention
				self.tablelock.acquire()
				NODE_ADDR = utils.getNode(searchKey)
				self.tablelock.release() 
				if NODE_ADDR == None :
					print("inside NONE addr found")
					#self.send_response(404)
					#self.end_headers()
					self.send_error(404, "Resource not available")
				else :
					redirTo = "http://" + NODE_ADDR + "/" + searchKey
					print(redirTo)
					self.send_response(302)
					self.send_header("Location", redirTo)
					self.end_headers()
			else:
				print("Received unsupported POST request : " + self.path)
				self.send_error(501, "Operation not implemented")
				self.end_headers()
				
		        	
		def do_POST(self):
			if self.path.endswith("/ADD_MEDIA"):
				content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
				post_data = self.rfile.read(content_length) # <--- Gets the data itself
				data = json.loads(post_data)
				
				self.tablelock.acquire()
				to_update = utils.fillLookupTable(data)
				self.tablelock.release()
				
				mmap.updateAvailabilityFromAddedSegments(to_update)
				mmap.printAvailability()
				self.send_response(200)
				self.end_headers()
			
			elif self.path.endswith("/REMOVE_NODE"):
				content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
				post_data = self.rfile.read(content_length) # <--- Gets the data itself
				data = json.loads(post_data)
				
				self.tablelock.acquire()
				to_update = utils.removeNode(data["addr"])
				self.tablelock.release()
				
				mmap.updateAvailabilityFromRemovedSegments(to_update)
				mmap.printAvailability()
				self.send_response(200)
				self.end_headers()
			
			elif self.path.endswith("/EXPIRED_LINKS"):
				content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
				post_data = self.rfile.read(content_length) # <--- Gets the data itself
				data = json.loads(post_data)
				
				self.tablelock.acquire()
				to_update = utils.removeLinks(data["addr"], data["segments"] )
				self.tablelock.release()
				
				mmap.updateAvailabilityFromRemovedSegments(to_update)
				mmap.printAvailability()
				self.send_response(200)
				self.end_headers()
			
			else :
				print("Received unsupported POST request : " + self.path)
				self.send_error(501, "Operation not implemented")
				self.end_headers()
        
	
	return CORSRequestsHandler

#Server Thread Code to execute			
def ServerCode(httpd) :
	#print media served by the system
	#movies = mmap.getMediaList()
	#print("list of movies served by the system : ")
	#print(movies)
	print("SERVER: started serving at " + str(httpd.server_address))
	httpd.serve_forever()

#Monitor Thread Code to execute		
def MonitorCode(tablelock, stopEvent) :
	
	#time_unit = TIME_UNIT
	#ping_unit = PING_UNIT
	current_time = 0
	
	while True :
		time.sleep(TIME_UNIT)
		current_time += TIME_UNIT
		
		if (stopEvent.is_set()) : return  # <--- Stop Monitor when program is terminating
		
		#print("MONITOR: Current time - " + str(current_time))
		if (current_time % PING_UNIT == 0) : # <--- time to ping nodes to check if they are still alive
			print("MONITORING: PING time!")
			tablelock.acquire()
			node_list = utils.getListOfNodes()
			tablelock.release()
			
			dead_node = []
			for n in node_list :
				url = "http://" + n + "/PING"
				try:
					r = requests.get(url)
					#print("MONITOR: symulating pinging to " + url)	
				except requests.exceptions.ConnectionError as e :
					#node is dead
					print("MONITORING: Node " + n + " is dead! CS has to remove it")
					jsonObj = json.dumps({"addr" : n})
					rr = requests.post( CS_REMOVE, data = jsonObj)
			current_time = 0

# Locks for shared resources in critical sections
tablelock = threading.Lock()

#Exit condition for Monitor Thread
stopEvent = threading.Event()

#Server thread preparation
#PORT = 8080
handler = RequestsHandlerFactory(tablelock)
httpd = socketserver.TCPServer((CS_IP, CS_PORT), handler)
t1 = threading.Thread(target=ServerCode, args=(httpd,))


#Monitor thread preparation
#IP = "localhost"
#myaddr = IP + ":" + str(PORT)
t2 = threading.Thread(target=MonitorCode, args=(tablelock, stopEvent))

# starting threads
t1.start()
t2.start()

try :
	t1.join()
	stopEvent.set()
	t2.join()

except KeyboardInterrupt:
	print("\nEXCEPT : KeyboardInterrupt in the Main Process")
	#shutdown the server
	httpd.shutdown()
	print("EXCEPT : Server shutdown complete")
	print("EXCEPT : Stopping Monitoring Thread... (may require some time)")
	#stop the Monitor
	stopEvent.set()
	t2.join()
	print("EXCEPT : Monitoring Thread stopped")

 


