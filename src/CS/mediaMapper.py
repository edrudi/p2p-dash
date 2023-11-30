#!/usr/bin/python
import os
#from MPD_parser import generateListOfSegmentsFromMPD
from MPDparser import getNumberOfSegmentFromMPD

# Media Map class
class MediaMap(object):
	
	# media -> {"segments" : listOfAllMediaSegments, "target": totalNumOfSegments, "available" : numOfAvailableSegments}
	#        ----> "segments" field was used during the debug, now its no more used since 
	#        ----> we are not interested in which segments are available, only if the numbers match
	MEDIA_MAP = {}
	
	def __init__(self):
		#for each mpd file /MEDIA/<media_name>/<media_name>.mpd, generate the name of the segments for <media_name>
		DEFAULT_DIR = "MEDIA/" #--> looking for media segments starting from this directory (path relative to current path)
		SCRIPT_PATH = os.getcwd()
		START_DIR = os.path.join(SCRIPT_PATH, DEFAULT_DIR)
		
		movies = [ f for f in os.listdir(START_DIR) if os.path.isdir(os.path.join(START_DIR, f))]
		print(movies)
		
		for m in movies :
			MPD_NAME = os.path.join(os.path.join(START_DIR, m), m + ".mpd")
			print(MPD_NAME)
			if os.path.isfile(MPD_NAME) :
				# Decomment follwing code lines to generate the segments name from the MPD
				# (usefull for debug purpose)
				# segments = generateListOfSegmentsFromMPD(MPD_NAME)
				# adjusted_segments = []
				# for s in segments :
				#	adjusted_segments.append("MEDIA/" + m + "/" + s);
				#
				# self.MEDIA_MAP[m] = {}
				# self.MEDIA_MAP[m]["segments"] = adjusted_segments
				# self.MEDIA_MAP[m]["target"] = len(segments)
				# self.MEDIA_MAP[m]["available"] = 0
				
				self.MEDIA_MAP[m] = {}
				self.MEDIA_MAP[m]["target"] = getNumberOfSegmentFromMPD(MPD_NAME)
				self.MEDIA_MAP[m]["available"] = 0					
		
		print(self.MEDIA_MAP)
	
	
	#--------------------------------------------GETTERS--------------------------------------------------------#
	
	
		
	#full list of all known media contents
	def getMediaList(self) :
		return self.MEDIA_MAP.keys()
	
	def getSegmentsFromMediaName(self, media) :
		return self.MEDIA_MAP.get(media)
	
	def getlistOfAvailableMedia(self) :
		availables = []
		for m in self.MEDIA_MAP.keys() :
			if self.MEDIA_MAP[m]["target"] == self.MEDIA_MAP[m]["available"] :
				availables.append(m)
		return availables
	
	
	#--------------------------------------------- UPDATE AVAILABILITY ------------------------------------------#
	
	#add "number" to the number of available segments for this media	
	def updateAvailabilityFromMediaNumber(self, media, number) :
		if self.MEDIA_MAP.get(media) != None :
			self.MEDIA_MAP[media]["available"] += number
	
	#correctly update availability in case of Removed Segments
	def updateAvailabilityFromRemovedSegments(self, removed_list) :
		media_number_map = {}
		for s in removed_list :
			#segment name convention: MEDIA/<media_name>/.../.m4f
			m = s.split('/')[1]
			#print("updateAvailability : seg media is " + m)
			if media_number_map.get(m) == None :
				media_number_map[m] = 1
			else :
				media_number_map[m] += 1
		
		for m in media_number_map.keys() :
			self.updateAvailabilityFromMediaNumber(m, media_number_map[m]*-1)
	
	#correctly update availability in case of newly Added Segments
	def updateAvailabilityFromAddedSegments(self, to_update) :
		for (m, num) in to_update :
			self.updateAvailabilityFromMediaNumber(m, num)
	
	
	#----------------------------------------------PRINT------------------------------------------------------#
	
	#print utility		
	def printAvailability(self) :
		availables = self.getlistOfAvailableMedia()
		print("/****/ AVAILABILITY RECORD /****/")
		print("\tmovie\t:\tavailable?")
		for k in self.getMediaList() :
			debug = str(self.MEDIA_MAP[k]["target"]) + " - " + str(self.MEDIA_MAP[k]["available"])
			if k in availables :
				print( "\t" + k + "\t\t:\tYES -> " + debug)
			else :
				print("\t" + k + "\t\t:\tNO ->" + debug)

