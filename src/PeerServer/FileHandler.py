#!/usr/bin/python
import pathlib
import os 




def storeSegment(name, raw_data) :
	createBinaryFile(name, raw_data)
	
def removeSegmentFromFileSystem(name) :
	return removeFile(name)

def createTextFile(name, text) :
	
	DIR_PATH = ""
	for s in name.split('/')[1:-1] :
		DIR_PATH += "/" + s
	FILE_NAME = name[1:]
	
	#recursively create directories if needed
	pathlib.Path(DIR_PATH[1:]).mkdir(parents=True, exist_ok=True)
	
	#create binary file
	with pathlib.Path(FILE_NAME).open(mode='w') as f :
		f.write(text)
		f.close()
	print("FILE CREATED :)")
	

# name = relative path (with respect to PeerServer position) of the file we want to create
#	    E.g.; /MEDIA/tears_of_steel/audio/en/seg-1.m4f
# bytes = bytes to be written inside the new binary file

def createBinaryFile(name, raw_data) :
	
	DIR_PATH = ""
	for s in name.split('/')[1:-1] :
		DIR_PATH += "/" + s
	FILE_NAME = name[1:]
	
	#recursively create directories if needed
	pathlib.Path(DIR_PATH[1:]).mkdir(parents=True, exist_ok=True)
	
	#create binary file
	with pathlib.Path(FILE_NAME).open(mode='wb') as f :
		f.write(raw_data)
		f.close()
	print("FILE CREATED :)")


#  This version remove file but does not remove empty folders
def removeFile(name) :
	
	#try to remove the file
	try :
		pathlib.Path(name[1:]).unlink()
	
	except FileNotFoundError :
		return False
	
	return True

# Remove both files and folders
def clearFileSystem(start_dir) :
	for root, dirs, files in os.walk(start_dir, topdown=False) :
		for name in files :
			os.remove(os.path.join(root, name))
		os.rmdir(root)



