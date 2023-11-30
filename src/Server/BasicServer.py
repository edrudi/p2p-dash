#!/usr/bin/python
import http.server
import socketserver
import os
import json
import requests
from mediaScanner import scan

#Default Configuration:
CS_IP = "localhost"
CS_PORT = 8080
IP = "localhost"  #<--- Monitor Threading is executed every TIME_UNIT seconds
PORT = 8091  #<--- Monitor Threading ping Servers every PING_UNIT seconds. PING_UNIT must be multiple of TIME_UNIT

#Override default configuration with user configuration (config.json)
f = open("config.json", "r")
config = json.load(f)
CS_IP = config["CS"].get("HOST", CS_IP)
CS_PORT = config["CS"].get("PORT", CS_PORT)
IP = config["NODE"].get("HOST", IP)
PORT = config["NODE"].get("PORT", PORT)

print("\nStarting Server with the following configuration parameters:")
print("CS_IP : " + CS_IP)
print("CS_PORT : " + str(CS_PORT))
print("IP : " + IP)
print("PORT : " + str(PORT))



# Estendo il comportamento di SimpleHTTPServerHandler per gestire le CORS
class CORSRequestsHandler(http.server.SimpleHTTPRequestHandler):
	
	def end_headers(self):
		
		self.send_header('Access-Control-Allow-Origin', '*')
		super().end_headers()
		
	def do_GET(self):
		if self.path.endswith("/PING"):
			self.send_response(200)
			self.end_headers()
		else:
			super().do_GET()


myaddr = IP + ":" + str(PORT)
handler = CORSRequestsHandler

#init - registration phase : register avialable media on the Main Server
CS_ADDRESS = CS_IP + ":" + str(CS_PORT)
CS_ADD = "http://" + CS_ADDRESS + "/ADD_MEDIA"
CS_REMOVE = "http://" + CS_ADDRESS + "/REMOVE_NODE"
DEFAULT_DIR = "MEDIA/"
SCRIPT_PATH = os.getcwd()
media = scan(DEFAULT_DIR, SCRIPT_PATH)
media["addr"] = myaddr

#Dict to JSON
jsonObj = json.dumps(media)
#print(jsonObj)
#HTTP post with json obj
r = requests.post(CS_ADD, data = jsonObj)
#print("status request: ")
#print(r.status_code)


#Serve media contents to redirected clients
try :
	
	with socketserver.TCPServer((IP, PORT), handler) as httpd:
		print("Server started at localhost:" + str(PORT))
		httpd.serve_forever()

except KeyboardInterrupt:
	
	print("\nEXCEPT : KeyboardInterrupt received")
	#Remove from CS
	jsonObj = json.dumps({"addr" : myaddr})
	print("Sending a REMOVE_NODE to CS with json body = " + jsonObj)
	r = requests.post( CS_REMOVE, data = jsonObj)
	print("Server terminated!")
