#!/usr/bin/python
import os

#Scan file system looking for video and media segments
def scan(path_default, path_script) :
	
	DEFAULT_DIR = path_default  #--> looking for media segments starting from this directory (path relative to current path)
	SCRIPT_PATH = path_script
	START_DIR = os.path.join(SCRIPT_PATH, DEFAULT_DIR)
	CURRENT_DIR = START_DIR
	RELATIVE_PATH = DEFAULT_DIR
	
	media = {}
	folders = []
	movies = [ f for f in os.listdir(CURRENT_DIR) if os.path.isdir(os.path.join(CURRENT_DIR, f))]
	print("\nMultimedia Contents found: \n")
	for m in movies :
		segments = []
		CURRENT_DIR = os.path.join(START_DIR, m)
		RELATIVE_PATH = os.path.join(DEFAULT_DIR, m)
		print("\n*********** " + m + " *************\n")
		#print("cerco segmenti nel percorso: " + CURRENT_DIR)
		while True :
			for f in os.listdir(CURRENT_DIR) :
				if os.path.isdir(os.path.join(CURRENT_DIR, f)) :
					folders.append(os.path.join(CURRENT_DIR, f))
					#print("\n CARTELLA trovata: " + folders[-1])
				else :
					segments.append(os.path.join(RELATIVE_PATH, f))
					#print("segmento trovato: " + os.path.join(RELATIVE, f) + "\n")
			
			if not folders :
				break
			
			CURRENT_DIR = folders.pop(0)
			RELATIVE_PATH = os.path.relpath(CURRENT_DIR, SCRIPT_PATH)
			#print("\nNew relative path: " + RELATIVE_PATH + "\n")
		media[m] = segments
		#print("\n*********** fine *************\n")
	
	return media
