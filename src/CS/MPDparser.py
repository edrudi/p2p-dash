#!/usr/bin/python
import xml.etree.ElementTree as ET
import re
import math

#Parse media duration format into seconds
#e.g, PT23M12.128S -> 1392.128
def parseMediaPresDuration(raw_media_duration) :
	REGEX_pattern = r'PT(?P<days>\d+D)?(?P<hours>\d+H)?(?P<mins>\d+M)?(?P<secs>\d+\.?\d*S)'
	pattern = re.compile(REGEX_pattern)
	match = pattern.match(raw_media_duration)
	
	#print(match[0]) #full string if matched
	#print(match[1]) # days
	#print(match[2]) # hours
	#print(match[3]) # minutes
	#print(match[4]) # seconds
	media_duration = 0.0

	if match[1] :
		media_duration += int(match[1][:-1]) * 24 *60 * 60
	if match[2] :
		media_duration += int(match[2][:-1]) * 60 * 60
	if match[3] :
		media_duration += int(match[3][:-1]) * 60
	if match[4] :
		media_duration += float(match[4][:-1])
	
	return media_duration
	
#Generate the full list of segments name given a string_format, the representation ID and Number
#Currently can recognised only $RepresentationID$ and $Number$
def generateName(string_format, representation_ID, number) :
	
	name = ""
	keyword = ""
	inside_keyword = False
	
	for i in range(0, len(string_format)):
		c = string_format[i]
		
		if c == '$' :
			if inside_keyword :
							
				#print("Keyword is " + keyword)
				if keyword == "RepresentationID" :
					name = name + representation_ID
				elif keyword == "Number" :
					name = name + str(number)
				else :
					print("ERROR: keyword not recognised!")
				keyword = ""
				inside_keyword = False
			else :
				inside_keyword = True
		
		else :
			if not inside_keyword :
				name = name + c
			else :
				keyword = keyword + c
				
	#print("Segment name is :" + name)
	return name

#Generate all segments name starting from a MPD file generated with Bento4 tool with the limitation of having only one period
#Can be extended to cover more use cases
def generateSegmentsFromBento4MPD(filename) :
	tree = ET.parse(filename)
	root = tree.getroot()  #MPD element

	#0) get namespace
	namespace = ""
	if '}' in root.tag :
		namespace = root.tag.split('}')[0] + "}"

	#1) get MediaPresentationDuration and parse its value
	raw_media_duration = root.attrib["mediaPresentationDuration"]
	#print("media duration is : " + raw_media_duration)
	media_duration = parseMediaPresDuration(raw_media_duration)

	#For each Representation generate the segments name
	listOfSegments = []
	for period in root.findall(namespace + 'Period'):
		for ad_set in period.findall(namespace + 'AdaptationSet') :
			tot_num = 0
			reps_ids = []
			seg_name_format = ""
			init_name_format = ""
		
			for child in ad_set :
				if child.tag == namespace + 'SegmentTemplate' :
					seg_duration = int(child.attrib["duration"])
					seg_timescale = int(child.attrib["timescale"])
					seg_name_format = child.attrib["media"]
					init_name_format = child.attrib["initialization"]
					
					test = seg_duration/seg_timescale
					tot_num = math.ceil(media_duration / (seg_duration/seg_timescale))
					
				if child.tag == namespace + 'Representation' :
					reps_ids.append(child.attrib["id"])
		
			#generate name for representations init segments
			for rep in reps_ids : 
				listOfSegments.append(generateName(init_name_format, rep, None))
			#generate name for representations media segments
			for num in range(tot_num) :
				for rep in reps_ids :
					listOfSegments.append(generateName(seg_name_format, rep, num + 1))

	return listOfSegments		


#For now only MPD made by BENTO4 (or MPD with the same structure) are supported
#which means -> single period MPD with SegmentTemplate xml element that use only $RepresentationID$ and $Number$ as keywords
#NOTE: NOT USED in Media_Mapper.py, was used for debug purpose
def generateListOfSegmentsFromMPD(filename) :
	return generateSegmentsFromBento4MPD(filename)
	
def getNumberOfSegmentFromMPD(filename) :
	tree = ET.parse(filename)
	root = tree.getroot()  #MPD element

	#0) get namespace
	namespace = ""
	if '}' in root.tag :
		namespace = root.tag.split('}')[0] + "}"

	#1) get MediaPresentationDuration and parse its value
	raw_media_duration = root.attrib["mediaPresentationDuration"]
	#print("media duration is : " + raw_media_duration)

	media_duration = parseMediaPresDuration(raw_media_duration)

	#Compute the number of segments
	totalNumOfSegments = 0
	for period in root.findall(namespace + 'Period'):
		for ad_set in period.findall(namespace + 'AdaptationSet') :
			tot_num = 0
			reps_ids = []
			rep_num = 0
		
			for child in ad_set :
				if child.tag == namespace + 'SegmentTemplate' :
					seg_duration = int(child.attrib["duration"])
					seg_timescale = int(child.attrib["timescale"])
					tot_num_per_rep = math.ceil(media_duration / (seg_duration/seg_timescale)) + 1 
					
				if child.tag == namespace + 'Representation' :
					rep_num += 1
		
			#Number of Segment in this Adaptation Set = Num_of_representation x num_of_segment_in_representation
			totalNumOfSegments += rep_num * tot_num_per_rep

	return totalNumOfSegments		


