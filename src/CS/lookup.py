#!/usr/bin/python

# Lookup Dictionary
class LookupDict(object):
	
	LOOKUP_TABLE = {}  # association SegmentName - listOfIPAddrs

	nodes = []   # <-- used for Load Balancing
	
	#fill table with new association SegmentName - IP_Addr
	#return the number of NEW segments added (before they were not available, now they are)
	#for each movie
	def fillLookupTable(self, data) :
		addr = data.pop("addr")
		newly_available = []
		
		for k in data.keys() :
			print("\n*** MEDIA :" + k + "\n")
			segments = data[k]
			number_of_new_segments = 0
			for s in segments :
				#print("segmento :" + s + "\n")
				addr_list = self.LOOKUP_TABLE.get(s)
				if addr_list == None :
					#print("@DENTRO NONE")
					self.LOOKUP_TABLE[s] = [addr]
					number_of_new_segments += 1
				else :
					#print("@DENTRO ELSE")
					if addr not in addr_list :
						addr_list.append(addr)
			
			if number_of_new_segments > 0 :
				newly_available.append((k,number_of_new_segments))
		
		print("\n TABLE UPDATED\n")
		#print(" Lookup table: ")
		#print(self.LOOKUP_TABLE)
		if addr not in self.nodes :
			self.nodes.append(addr)
		
		return newly_available
		
	#Select Server with Round Robin policy 
	def getNode(self, segment) :
		addrs = self.LOOKUP_TABLE.get(segment)
		if addrs == None :
			print("Error: no segment called " + segment + " registered")
			return None
		
		winner = next(n for n in self.nodes if n in addrs)
		self.nodes.remove(winner)
		self.nodes.append(winner)
		return winner
	
	#Select Server with no policy = no load balancing	
	def getNaiveNode(self, segment) :
		addrs = self.LOOKUP_TABLE.get(segment)
		if addrs == None :
			print("Error: no segment called " + segment + " registered")
			return None
		return addrs[0]
	
	#Return full list of registered Server
	def getListOfNodes(self) :
		nodes_copy = []
		for n in self.nodes :
			nodes_copy.append(n)
		return nodes_copy
	
	#Remove Server
	def removeNode(self, addr) :
		to_delete = []
		for s, a in self.LOOKUP_TABLE.items() :
			if addr in a :
				self.LOOKUP_TABLE[s].remove(addr)
				if not self.LOOKUP_TABLE[s] : # <-- not empty?
					to_delete.append(s)
		for s in to_delete :
			del self.LOOKUP_TABLE[s]
		
		if addr in self.nodes:
			self.nodes.remove(addr)
			print("Node " + addr + " removed!")
		#print(self.LOOKUP_TABLE)
		return to_delete
	
	
	#Remove association	
	def removeLinks(self, addr, segments) :
		no_more_available = []
		for s in segments :
			if (self.LOOKUP_TABLE.get(s) != None) and (addr in self.LOOKUP_TABLE[s]) :
				self.LOOKUP_TABLE[s].remove(addr)
				if not self.LOOKUP_TABLE[s] : # <-- not empty?
					no_more_available.append(s)
					del self.LOOKUP_TABLE[s]
		print("Removed some links related to addr " + addr)
		#print(self.LOOKUP_TABLE)
		return no_more_available
	
