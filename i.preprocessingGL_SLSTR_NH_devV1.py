#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
import os,sys,glob,optparse
import numpy as np
from datetime import timedelta 
import ogr
import time
import osgeo.gdal as gdal,osr
import hashlib
import pyresample as pr
from decimal import *
import fcntl, struct
import pdb
import logging
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon
import shapely.geometry
import ConfigParser
import shutil


###-----------------------------------------------------------------------------------------------------------
###-----------------------------------------------------------------------------------------------------------
###-----------------------------------------------------------------------------------------------------------

def cmdexec(cmd):
	"""
	Execution of a shell command line, including handling of return values.
	"""

	print cmd
	try:
		retcode = os.system(cmd)
		if retcode != 0:
			print >>sys.stderr, "Child was terminated by signal", -retcode
		else:
			print >>sys.stderr, "Child returned", retcode
	except OSError, e:
		print >>sys.stderr, "Execution failed:\n<%s>", e, cmd
		sys.exit(1)

	return

def filelogging(_logfile,_wtype,_msg):
	'''
	is writing logs to output file
	'''
	f=open(_logfile, "a")
	tsn=( datetime.fromtimestamp(time.time()).strftime('%Y%m%dT%H%M%S'))
	entry="%s\t%s:%s" % (tsn,_wtype,_msg)
	f.write("%s\n"% (entry))
	f.close()


def layercheck(filename,dataset):
	
	control=True
	
	d = ConfigParser.ConfigParser()
	d.read(filename)
	nrlayers = d.get('general','nrlayers')
	
	if dataset == 'an':
		if nrlayers != '14':
			control = False
			print "Layer missing. File will be deleted for new processing."
			os.remove(filename)

			
	elif dataset == 'in':
		if nrlayers != '7':
			control = False
			print "Layer missing. File will be deleted for new processing."
			os.remove(filename)
			
	else:
		if nrlayers != '2':
			control = False
			print "Layer missing. File will be deleted for new processing."
			os.remove(filename)
		
		return control
	
	
def createPOLYoutput(_extent):
	'''
	creates polygon from GlobLand bounding coordinates
	'''
	ULC_lat=float(_extent.split(",")[3])
	ULC_lon=float(_extent.split(",")[0])
	LRC_lat=float(_extent.split(",")[1])
	LRC_lon=float(_extent.split(",")[2])

	poly_GLextwkt=("POLYGON((%f %f, %f %f, %f %f, %f %f, %f %f))" % (ULC_lon,ULC_lat,LRC_lon,ULC_lat,LRC_lon,LRC_lat,ULC_lon,LRC_lat,ULC_lon,ULC_lat))
	poly_GLext = ogr.CreateGeometryFromWkt(poly_GLextwkt)
	
	return poly_GLext

def filelocationcheck(s3file,_poly_GLext):
	'''
	checks if files are intersecting with GlobLand extent -180 to 180 deg East and 25 to 84 deg North
	'''
	stat=False
	xmin,xmax,ymin,ymax=_poly_GLext.ConvexHull().GetEnvelope()
	print xmin,xmax,ymin,ymax
	
	
	f = "%s/xfdumanifest.xml" % s3file
	tree = ET.parse(f)
	root = tree.getroot()
	coord = root[1][2][0][0][0][0][0].text.split()
	lats = coord[::2]
	lons = set(coord) - set(lats)
	
	Nbc=float(max(lats))
	Sbc=float(min(lats))
	Wbc=float(min(lons))
	Ebc=float(max(lons))
	
	print Nbc, Sbc,Wbc,Ebc
	polyS3txt = ("POLYGON((%f %f, %f %f, %f %f, %f %f, %f %f))" % (Wbc,Nbc,Ebc,Nbc,Ebc,Sbc,Wbc,Sbc,Wbc,Nbc))
	polyS3 = ogr.CreateGeometryFromWkt(polyS3txt)

	stattmp=_poly_GLext.Intersects(polyS3)
				
	if stattmp==True:
		stat=True
	print stattmp
				
	return stat,Nbc,Sbc,Wbc,Ebc
	
def create_basename(_Ncoo,_Scoo,_Wcoo,_Ecoo,_infile,orbit):
	'''
	creates base for output files
	'''
	sto=_infile.split("_")[7].split("T")[1]
	eto=_infile.split("_")[8].split("T")[1]

	if _Scoo<0:
		Sname="S"
		_Scoo=abs(_Scoo)
	else:
		Sname="N"
		
	if _Ncoo<0:
		Nname="S"
		_Ncoo=abs(_Ncoo)
	else:
		Nname="N"
		
	if _Wcoo<0:
		Wname="W"
		_Wcoo=abs(_Wcoo)
	else:
		Wname="E"
	
	if _Ecoo<0:
		Ename="W"
		_Ecoo=abs(_Ecoo)
	else:
		Ename="E"

	bname="SLSTR_%s_%s_T%s_E%s_%s%02d%s%03d_%s%02d%s%03d" % (orbit,dstr2,sto,eto,Nname,int(_Ncoo),Wname,int(_Wcoo),Sname,int(_Scoo),Ename,int(_Ecoo))
	print bname
	#bnamein=_infile.split("/")[-1].split("npp_")[1].split("_NRT")[0]
	
	return bname#,bnamein
	

def create_file_links(_orirdir,_rawdir,_datein):
	'''
	Creats links to all necessary VIIRS data
	'''
	zipfiles=glob.glob("%s/S*____%s*zip" % (_orirdir,_datein))

	for item in zipfiles:
		
		newitem="%s/%s_NRT.zip" % (_rawdir,item.split("/")[-1].split(".")[0])


		if not os.path.exists(newitem):
			os.symlink(item,newitem)
			
				
###-----------------------------------------------------------------------------------------------------------
###-----------------------------------------------------------------------------------------------------------
###-----------------------------------------------------------------------------------------------------------


if __name__=="__main__":

	parser = optparse.OptionParser()

	parser.add_option("--date ",
						action="store", type="string", dest="dat", default = None,
						help="Processing date.")
	parser.add_option("--conf ",
						action="store", type="string", dest="conf", default = None,
						help="Directory of configfile.")
	parser.add_option("--rawdatadir",
					action="store", type="string", dest="rawdatadir", default=None,
					help="Directory of raw data.")					
	parser.add_option("--outdir",
					action="store", type="string", dest="odir", default=None,
					help="Output directory.")
	parser.add_option("--extent",
					action="store", type="string", dest="extent", default=None,
					help="GlobLand bounding box: xmin,ymin,xmax,ymax (e.g. -180,25,180,84).")
	parser.add_option("-b","--bands",
					action="store", type="string", dest="bands", default=None,
					help="SLSTR bands to be imported (separator=','). E.g. s1,s2,s3.")
	
	
	#Abfragen der command line options
	(options, args) = parser.parse_args()

	options, args = parser.parse_args(sys.argv[1:])

	if options.dat==None:
		datin=datetime.now()
	else:
		datin=datetime.strptime(options.dat,"%Y%m%d")

	# RAWDIR
	if options.rawdatadir!=None:
		RAW = options.rawdatadir
		if os.path.exists(RAW)==False:
			raise IOError("SLSTR raw products directory <%s> does not exist!" % (RAW))
	else:
		parser.error("Raw data path is not specified! Try <%s --help>" % __file__.rsplit("/")[-1])
		
	# OutDIR
	if options.odir!=None:
		ORI = options.odir
		if os.path.exists(ORI)==False:
			raise IOError("SLSTR output products directory <%s> does not exist!" % (ORI))
	else:
		parser.error("Output directory is not specified! Try <%s --help>" % __file__.rsplit("/")[-1])

	#Upper left corner coordinates
	if options.extent!=None:
		extent=options.extent
	else:
		parser.error("Bounding box is not specified! Try <%s --help>" % __file__.rsplit("/")[-1])
		
	#Bands
	if options.bands!=None:
		bands=options.bands
	else:
		parser.error("SLSTR band/s is/are not specified! Try <%s --help>" % __file__.rsplit("/")[-1])

	
    #xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    # set parameters
    
	day=datin.day
	mon=datin.month
	year=datin.year
	md=datin.strftime("%m%d")
	dstr=datin.strftime("%Y-%m-%d")
	dstr2=datin.strftime("%Y%m%d")
	bands = options.bands.split(",")
	
	GLpoly=createPOLYoutput(extent)
	
	#logfile
	logdir = "/data/enveo/GL_SE/log"
	#logdir = "/mnt/ws25data/lisi/GLOBLAND/DEVELOPEMENT/NH_processing_line/data"
	logyearfile = "%s/GloblandNH_%s.log" % (logdir,year)
	logger = logging.getLogger(__name__)
	logger.setLevel(logging.INFO)
	handler = logging.FileHandler(logyearfile)
	handler.setLevel(logging.INFO)
	logger.addHandler(handler)
    
	now = datetime.now()
	nowSTR = now.strftime("%Y-%m-%d %H:%M")
	
	
	#orirdir="%s/%s" % (RAW,dstr2)
	orirdir="%s" % (RAW)
	if not os.path.exists(orirdir):
		SENDMAIL = "/usr/sbin/sendmail" # sendmail location
		p = os.popen("%s -t" % SENDMAIL, "w")
		p.write("To: globland@enveo.at\n")
		p.write("Subject: NO RAW DIR %s\n" % (orirdir))
		p.write("\n") # blank line separating headers from body
		sts = p.close()
		logger.info("%s : NO RAWDATA DIR FOR THE DATE %s" % (nowSTR,datin))
		sys.exit("Raw data directory < %s > does not exist!" % (orirdir))
	
	odir="%s/%s" % (ORI,dstr2)
	rdir="%s/%s/linkedrawdata" % (ORI,dstr2)
	F_ft_lock_link="%s/%s/linkedrawdata.flock" % (ORI,dstr2)
	
	lockdata = struct.pack('hhllhh', fcntl.F_WRLCK, 0, 0, 0, 0, 0)
	lockdatalink = struct.pack('hhllhh', fcntl.F_WRLCK, 0, 0, 0, 0, 0)
	
	# creats output directory
	if os.path.exists(odir) == False:
			os.makedirs(odir)
	if os.path.exists(rdir) == False:
			os.makedirs(rdir)
	
	
	with open(F_ft_lock_link, "a+") as lockdata1:
		try:
			fcntl.fcntl(lockdata1.fileno(), fcntl.F_SETLKW, lockdatalink)
		except IOError:
			pass
	create_file_links(orirdir,rdir,dstr2)

	#fetch list of zip raw data
	os.chdir(rdir)
	obt_list=[]
	zipfiles=glob.glob("S*RBT*zip" )
	for zzip in zipfiles:
		obt=zzip.split("_")[-7]
		if obt not in obt_list:
			obt_list.append(obt)

	os.chdir(odir)

	# orbitewise processing
	for orbit in sorted(obt_list):
		print "\nProcessing for orbit: %s" % (orbit)

		files=glob.glob("%s/S*____%s*_%s_*.zip" % (rdir,dstr2,orbit))
		
		for infile in sorted(files):
			
			sen3 = "%s.SEN3" % (os.path.basename(infile[:-8]))
			#unzip files
			if os.path.exists(sen3) != True:
				__cmdline = "unzip -q %s *an.nc *in.nc *tx.nc *tn.nc *.xml -x *time*.nc *met_tx.nc -d ." % (infile)
				cmdexec(__cmdline)
			
			## Checks if Geofile is intersecting with the GL extent
			ratestat=False
			ratestat,Ncoo,Scoo,Wcoo,Ecoo=filelocationcheck(sen3,GLpoly)
			print "*******************************************************************************"
			print "File: %s" % (infile)
			print "File intersecting with GL extent: %s" % (str(ratestat))
			if ratestat==True:
				#Output names
				base_name_out=create_basename(Ncoo,Scoo,Wcoo,Ecoo,sen3,orbit)
				an_output_name=sen3[:-5]+"_B00500m_data_an.mdi" 
				in_output_name=sen3[:-5]+"_B01000m_data_in.mdi"
				tn_output_name=sen3[:-5]+"_B16000m_aux_tn.mdi"
				
				F_ft_lock = sen3[:-5]+'.flock'
				logfilename=sen3[:-5]+".info"
				
				try :
					
					with open(F_ft_lock, "a+") as lockfile:
						try:
							fcntl.fcntl(lockfile.fileno(), fcntl.F_SETLK, lockdata)
						except IOError:
							filelogging(logfilename,"MESSAGE","File lock on < %s >" % sen3)
							continue
						
						# Controls if there was an attempt to import the file which contains empty layer
						#valid=checkemptyfilelist(sen3[:-4])
						#if valid==True:

						# Controls if all layers are stored in file
						if (os.path.exists(an_output_name)):
							val=layercheck(an_output_name,"an")
						if (os.path.exists(in_output_name)):
							val=layercheck(in_output_name,"in")
						if (os.path.exists(tn_output_name)):
							val=layercheck(tn_output_name,"tn")
							
						if ( (os.path.exists(an_output_name)==False) or (os.path.exists(in_output_name)==False) or (os.path.exists(tn_output_name)==False)):
							filelogging(logfilename,"MESSAGE","Start processing < %s >" % sen3)
							
							
							#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
							#import REFLECTANCE,BRIGHTNESS TEMPERATURE and SOLAR/SENSOR ZENITH ANGLE
									
							filelogging(logfilename,"MESSAGE","Start pre-processing < %s >" % sen3)

							try:
								#import with SENTINEL-3 importer
								print "Importing data ..."
								print "%s.SEN3" % infile[:-8]
								__cmdline = "i.in.opt.sentinel3 -i %s/%s -d . -v n -s a -s i --rad2ref --force" % (odir,sen3)
								cmdexec( __cmdline )
								filelogging(logfilename,"SUCCESS","Importing Reflectance/Brightness temperature of < %s >" % sen3)
							except:
								filelogging(logfilename,"ERROR","Problems importing Reflectance/Brightness temperature of < %s >" % sen3)
							
							##### export bands
							try:
								for band in bands:
									if band in ["s1","s2","s3","s4","s5","s6"]:
										__cmdline = "dexport -i %s,_toa_reflectance_%s -o %s_500m_%s.tif --format GTiff --force" % (an_output_name,band,base_name_out,band)
										cmdexec(__cmdline)
									else:
										__cmdline = "dexport -i %s,_toa_brightness_temperature_%s -o %s_1000m_%s.tif --format GTiff --force" % (in_output_name,band,base_name_out,band)
										cmdexec(__cmdline)
								filelogging(logfilename,"SUCCESS","Exporting Brightness Temperature/Brightness temperature of < %s >" % sen3)
							except:
								filelogging(logfilename,"ERROR","Exporting Brightness Temperature/Brightness temperature of < %s >" % sen3)
							print "Remove SEN3 folder "
							shutil.rmtree(sen3)
							
						else:
							print("Files already processed: \n \f %s\n \f %s " % (an_output_name,in_output_name)) 
						#else:
							#print("File package %s contains nodata - was excluded from processing!" % (base_in))
				except:
					##pass
					SENDMAIL = "/usr/sbin/sendmail" # sendmail location
					p = os.popen("%s -t" % SENDMAIL, "w")
					p.write("To: globland@enveo.at\n")
					p.write("Subject: Error in %s\n" % (base_in))
					p.write("\n") # blank line separating headers from body
					p.write("Problems importing file package: %s " % (sen3))
					logger.info("Problems importing file package: %s " % (sen3))
					sts = p.close()
			else:
				print "Remove the data that is not crossing the NH extent"
				shutil.rmtree(sen3)
