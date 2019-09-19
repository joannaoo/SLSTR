#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys
import optparse
import time, datetime
import ConfigParser
import pdb
import numpy
import glob
import ftplib
from datetime import timedelta
import osgeo.gdal as gdal
import logging
from PIL import Image
import shlex,subprocess
import signal
import shutil
#===================================================================================
#
# catch the kill signal
childproc = None
def killhandler(signum, frame):
	global childproc
	if childproc:
		childproc.send_signal(signum)
	else:
		raise CmdexecErr(-signum)

signal.signal(signal.SIGINT,  killhandler)
signal.signal(signal.SIGTERM, killhandler)


class CmdexecErr(Exception):
	def __init__(self, retval):
		self.retval = retval
	def __str__(self):
		return repr(self.retval)
	
def IYFlatten(items):
	"""return a list of unflatted elements"""
	ret = []
	if type(items) == list:
		for x in items:
			ret.extend(IYFlatten(x))
	else:
		ret = [items]
	return ret

def cmdexec(cmd, args=None, **kwargs):
	global childproc
	retcode = None
	try:
		if type(cmd) == list:
			cmdlist = IYFlatten(cmd)
		else:
			cmdlist = shlex.split(cmd)

		logger.info(" ".join(cmdlist))
		logger.debug("cmdexec kwargs: "+str(kwargs))
		childproc = subprocess.Popen(cmdlist, **kwargs)
		#logger.debug("Child pid: %d" % (childproc.pid))
		retcode = childproc.wait()
		logger.debug("Child (%d) exit: %d" % (childproc.pid, retcode))
		childproc = None
	except Exception as e:
		logger.error(e)
		raise e
	if retcode != 0:
		#logger.error("Child was terminated by signal %d" % retcode)
		raise CmdexecErr(retcode)
	return retcode




#XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

class INIfile:
	"""
	Class handling INI files.
	"""
	def __init__(self, inifilename):
		self.inifilename = inifilename
		# set up config parser instance
		self.__config = ConfigParser.ConfigParser()
		self.__config.read(inifilename)
		return

	def get_platform(self):
		"""
		Get platform name.
		"""
		__platform = self.__config.get("general", "platform")
		return __platform

	def get_sensor(self):
		"""
		Get sensor name.
		"""
		__sensor = self.__config.get("general", "sensor")
		return __sensor

	def get_aoi(self):
		"""
		Get area of interest.
		"""
		__aoi = self.__config.get("general", "aoi")
		return eval(__aoi)

	def get_ulc(self):
		"""
		Get upper left corner of AOI.
		"""
		__ulc = self.__config.get("general", "ulc")
		return eval(__ulc)

	def get_lrc(self):
		"""
		Get lower right corner of AOI.
		"""
		__lrc = self.__config.get("general", "lrc")
		return eval(__lrc)
	
	def get_res(self):
		"""
		Get resolution.
		"""
		__res = self.__config.get("general", "res")
		return eval(__res)
	
	def get_szathr(self):
		"""
		Get threshold for solar zenit angle regarding polar night.
		"""
		__szathr = self.__config.get("settings","szathr")
		return eval(__szathr)
	
	def get_vzathr(self):
		"""
		Get threshold for viewing zenit angle regarding polar night.
		"""
		__vzathr = self.__config.get("settings","vzathr")
		return eval(__vzathr)

	def get_outpath(self):
		"""
		Get area of interest for merging.
		"""
		__out = self.__config.get("directories", "outpath")
		return eval(__out)

	def get_binpath(self):
		"""
		Get area of interest for merging.
		"""
		__out = self.__config.get("directories", "binpath")
		return eval(__out)
	
	def get_palette(self):
		"""
		Get area of interest for merging.
		"""
		__pal = self.__config.get("GLdefinitions", "palette")
		return eval(__pal)
	
	def get_transpath(self):
		"""
		Get transmissivity map.
		"""
		__transpath = self.__config.get("auxiliary", "transpath")
		return eval(__transpath)

	def get_scmpath(self):
		"""
		Get transmissivity map.
		"""
		__scmpath = self.__config.get("auxiliary", "scmpath")
		return eval(__scmpath)
	
def MDIlayercheck(filename,layer):
	
	if len(glob.glob(filename[:-4]+"/*"))!=layer:
		try:
			os.remove(filename)
		except:
			pass
		try:
			os.removedirs(filename[:-4])
		except:
			pass
		return False
	else:
		return True

def addwatermasks(_mergedfiletif,_transpath,_scmpath,_mergedfiletiftmp):
	'''
	4 adding water pixes in polar night and nodata areas
	'''
	sfcdata,sfcgt,sfcsrs=read_geo(_mergedfiletif, 1)
	transdata,transgt,transsrs = read_geo(_transpath[:-4]+'.tif', 1)
	scmdata,scmgt,scmsrs = read_geo(_scmpath[:-4]+'.tif',1)

	sfcdata[numpy.where(( (sfcdata==255) | (sfcdata==251) ) & (transdata==-1))]=20
	sfcdata[numpy.where(( (sfcdata==255) | (sfcdata==251) ) & (scmdata==20))]=20

	make_geo(sfcdata, _mergedfiletiftmp, sfcgt, sfcsrs, 1)
	
	
def make_geo(data, output_name, gt, srs_wkt, layer):
	#make Geotiff of difference and quiklook png
	#rm old file_
	
	ds_save = None
	Ny, Nx = data.shape
	driver = gdal.GetDriverByName('GTiff')
	ds_save = driver.Create(output_name, Nx, Ny, int(layer),  gdal.GDT_Byte)#write range to tif
	ds_save.SetGeoTransform(gt)
	ds_save.SetProjection(srs_wkt)
	ds_save.GetRasterBand(1).WriteArray(data)
	ds_save.GetRasterBand(1).SetNoDataValue(255)
	ds_save = None

def read_geo(name, layer):
	ds=None
	ds = gdal.Open(name, gdal.GA_ReadOnly)
	data = ds.GetRasterBand(layer).ReadAsArray()
	gt = ds.GetGeoTransform()
	srs_wkt = ds.GetProjection()
	ds = None
	return data, gt, srs_wkt


	
#XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

if __name__=="__main__":

	#  populating command line parser with options
	parser = optparse.OptionParser()

	parser.add_option("-c", "--control",
						action="store", type="string", dest="controlfile", default=None,
						help="Control ini-file.")

	parser.add_option("--date",
						action="store", type="string", dest="dat", default = None,
						help="Processing date (format YYYYMMDD).")
						

	#Extract information from command line options
	(options, args) = parser.parse_args()

	options, args = parser.parse_args(sys.argv[1:])

	if len(args) !=0:
		parser.error("Incorrect number of arguments, see %prog -h for help!")
		parser.print_help()

	if options.dat!=None:
		dat=options.dat
	else:
		parser.error("No date specified!")
		
	if (options.controlfile!=None):
		controlinifile = options.controlfile
	else:
		parser.error("No controlfile (INI) specified!")

	#parse control INI file
	control = INIfile(controlinifile)
	aoi = control.get_aoi()
	ulc = control.get_ulc()
	lrc = control.get_lrc()
	res = control.get_res()
	vzathr = control.get_vzathr()
	szathr = control.get_szathr()
	outpath = control.get_outpath()
	palette = control.get_palette()
	platform = control.get_platform()
	sensor = control.get_sensor()
	binpath = control.get_binpath()
	transpath = control.get_transpath()
	scmpath = control.get_scmpath()

	#-------------------------------------------------------------------------
	#set parameters
	datin=datetime.datetime.strptime(dat,"%Y%m%d")
	datin2=(datetime.datetime.strptime(dat,"%Y%m%d")).strftime("%Y-%m-%d")
	
	#logging
	logdir = "/data/enveo/GL_SE/log"
	#logdir = "/mnt/ws25data/lisi/GLOBLAND/DEVELOPEMENT/NH_processing_line/data"
	year=datin.year
	logyearfile = "%s/GloblandNH_%s.log" % (logdir,year)
	logger = logging.getLogger(__name__)
	logger.setLevel(logging.INFO)
	handler = logging.FileHandler(logyearfile)
	handler.setLevel(logging.INFO)
	logger.addHandler(handler)
	
	outpth=os.path.join(outpath,dat)

	os.chdir(outpth)
	
	SCEfilelist=sorted(glob.glob("*sce.mdi"))

	print SCEfilelist[0], SCEfilelist[-1]
	starttime=SCEfilelist[0].split("____")[1].split("_")[0].split("T")[1]
	endtime=SCEfilelist[-1].split("____")[1].split("_")[0].split("T")[1]
	
	startstr="%sT%s:%s:%s.%sZ" % (datin2,starttime[0:2],starttime[2:4],starttime[4:6],starttime[6:7])
	if float(starttime)>float(endtime): #in case end date is on next day
		datin22=((datetime.datetime.strptime(dat,"%Y%m%d"))+timedelta(1)).strftime("%Y-%m-%d")
		endstr="%sT%s:%s:%s.%sZ" % (datin22,endtime[0:2],endtime[2:4],endtime[4:6],endtime[6:7])
	else:
		endstr="%sT%s:%s:%s.%sZ" % (datin2,endtime[0:2],endtime[2:4],endtime[4:6],endtime[6:7])
	
	mergedfile="SLSTR_%s_T%s_E%s_SCEcomposite.mdi" % (dat,starttime,endtime)
	mergedfiletif="SLSTR_%s_T%s_E%s_SCEcomposite.tif" % (dat,starttime,endtime)
	mergedfiletiftmp="SLSTR_%s_T%s_E%s_SCEcomposite_tmp.tif" % (dat,starttime,endtime)
	GLtiffnc="c_gls_SCE_%s0000_NHEMI_%s_V1.0.1.nc" % (dat,sensor) 
	GLtiffql="c_gls_SCE_QL_%s0000_NHEMI_%s_V1.0.1.tiff" % (dat,sensor)
	GLpngql="c_gls_SCE_QL_%s0000_NHEMI_%s_V1.0.1.png" % (dat,sensor)
	try:
		if not os.path.exists(mergedfile):
			#FSC string for input
			inputstr=""
			szalist=""
			vzalist=""
			for item in SCEfilelist:
				angfile=item.replace("B00500m_sce.mdi","B16000m_aux_tn.mdi")
				if not os.path.exists(angfile):
					print "%s file missing!" % (angfile)
					continue
				validang=MDIlayercheck(angfile,2)
				valid=MDIlayercheck(item,1)
				if ((valid==True) and (validang==True)):
					itex="-i %s,1 " % item
					szaf="--szafile %s,_solar_zenith_angle " % angfile
					vzaf="--vzafile %s,_satellite_zenith_angle " % angfile
					inputstr=inputstr+itex
					szalist=szalist+szaf
					vzalist=vzalist+vzaf

					
			cmd="i.opt.sca.merge %s %s %s --ul=%s,%s --lr=%s,%s --sza-thr=%s --vza-thr=%s -p %s,-%s -o %s,a -n SCEcomposite" % (inputstr, szalist, vzalist, ulc[0],ulc[1], lrc[0],lrc[1], szathr, vzathr, res,res, mergedfile)
			#print(cmd)
			cmdexec(cmd)
			
			print("Merging file < %s> successful!" % (mergedfile))

		if ((os.path.exists(mergedfile)) and (not os.path.exists(mergedfiletiftmp))):
			cmd="dexport -i %s,1 -o %s --format GTIFF --omitt 255" % (mergedfile,mergedfiletiftmp)
			#print cmd
			os.system(cmd)
			
		if ((os.path.exists(mergedfiletiftmp)) and (not os.path.exists(mergedfiletif))):
			
			addwatermasks(mergedfiletiftmp,transpath,scmpath,mergedfiletif)
		
		
		if os.path.exists(mergedfiletif):
			
			
			if os.path.exists(GLtiffnc)!=True:
				__cmdline="python %s/gtiff2nc4_V1.0.1_NH.pyc -i %s -d %s --sd %s --ed %s -o %s --platform %s --sensor %s" % (binpath,mergedfiletif,dat,startstr,endstr,GLtiffnc,platform, sensor)
				print __cmdline
				os.system( __cmdline)

			
			if os.path.exists(GLtiffql)!=True:
				__cmdline="gdalwarp -tr 0.01 0.01 -srcnodata 255 -dstnodata None %s %s" % (mergedfiletif,GLtiffql)
				#print __cmdline
				os.system(__cmdline)

				__cmdline="python %s/add_palette.pyc %s %s " % (binpath, palette,GLtiffql)
				#print __cmdline
				os.system( __cmdline)
				
			if os.path.exists(GLpngql)!=True:
				im = Image.open(GLtiffql)
				im.save(GLpngql,"PNG",quality=90)
		logger.info("SUCCESFUL MERGING FOR THE DATE : %s" % datin)
		
	except:
		SENDMAIL = "/usr/sbin/sendmail" # sendmail location
		p = os.popen("%s -t" % SENDMAIL, "w")
		p.write("To: globland@enveo.at\n")
		p.write("Subject: ERROR while creating GL NH composite: %s!\n" % (dat))
		p.write("\n") # blank line separating headers from body
		logger.info("%s : PROBLEMS CREATING GL COMPOSITE FOR THE DATE %s" % (dat,datin))
		sts = p.close()
				
	try:
		if ((os.path.exists(GLtiffnc)==True and os.path.exists(GLtiffql)==True)):
			print "Uploading files to GLOBSNOW ftp!"
			##upload to GlobLand ftp
			filetiffup = open(GLtiffql, 'rb')   
			filencup = open(GLtiffnc, 'rb')  
			remote = ftplib.FTP("litdb.fmi.fi", user="globsnow_admin", passwd="vX29si*wJ")   
			remote.cwd("/GlobLand/SLSTR_NH/")
			remote.storbinary('STOR ' + GLtiffql, filetiffup, 1024)
			remote.storbinary('STOR ' + GLtiffnc, filencup, 1024)
			remote.quit()
			filencup.close()
			filetiffup.close()
			logger.info("%s : FILES UPLOADED TO THE FTP" % dat)
	except:

		SENDMAIL = "/usr/sbin/sendmail" # sendmail location
		p = os.popen("%s -t" % SENDMAIL, "w")
		p.write("To: globland@enveo.at\n")
		p.write("Subject: ERROR uploading files to FMI GLOBSNOW FTP (temporary): %s!" % (dat))
		p.write("\n") # blank line separating headers from body
		p.write("Files for upload:\n%s\n%s " % (GLtiffnc,GLtiffql))
		sts = p.close()
		logger.info("%s : PROBLEM WITH UPLODING FILES" % dat)
		sys.exit("ERROR uploading files to FMI GLOBSNOW FTP: %s!" % (dat))
		
    liedir = '%s/%s_LIE_toa_br' % (outpth, dat)
    tardir = '%s/%s' % (outpth, dat)
    if not os.path.exists(tardir):
        os.mkdir(tardir)
    if not os.path.exists(liedir):
        os.mkdir(liedir)
    tif_files = glob.glob('%s/SLSTR*tif' % outpth)
    for tif_file in tif_files:
        if not os.path.join(liedir,tif_file):
            shutil.move(tif_file, liedir)

    if not os.path.exists('%s.tar.gz' % liedir):
        os.system('tar -zcf %s.tar.gz %s' % (liedir, liedir))
    if not os.path.exists('%s/%s_LIE_toa_br.tar.gz' % (tardir, dat)):
        shutil.move('%s.tar.gz' % liedir, tardir)
        cmd = 'upload2s3 %s' % tardir
        cmdexec(cmd)

	# this section is only for uploading to GlobLand server!
	#try:
		#if ((os.path.exists(GLtiffnc)==True and os.path.exists(GLtiffql)==True)):
			#print "Uploading files to FMI GlobLand FTP!"
			## upload to GlobLand ftp
			#filetiffup = open(GLtiffql, 'rb')   
			#filencup = open(GLtiffnc, 'rb')  
			#filepngup = open(GLpngql, 'rb') 
			#remote = ftplib.FTP("litdb.fmi.fi", user="globland_usr", passwd="w7O8dCCxsf8XM")   
			#remote.cwd("/SCE_NH_1km/")
			#remote.storbinary('STOR ' + GLtiffql, filetiffup, 1024)
			#remote.storbinary('STOR ' + GLtiffnc, filencup, 1024)
			#remote.storbinary('STOR ' + GLpngql, filepngup, 1024)
			#remote.quit()
			#filencup.close()
			#filetiffup.close()
			#logger.info("%s  : SUCCESSFUL UPLOAD OF GLOBLAND FILES FOR THE DATE %s" % (dat,datein))
	#except:

		#SENDMAIL = "/usr/sbin/sendmail" # sendmail location
		#p = os.popen("%s -t" % SENDMAIL, "w")
		#p.write("To: globland@enveo.at\n")
		#p.write("Subject: ERROR uploading files to FMI GlobLand FTP: %s!" % (dat))
		#p.write("\n") # blank line separating headers from body
		#p.write("Files for upload:\n%s\n%s " % (GLtiffnc,GLtiffql))
		#sts = p.close()
		#logger.info("%s  : ERROR UPLOADING FILES TO FMI GLOBLAND FTP FOR THE DATE %s" % (dat,datein))
		#sys.exit("ERROR uploading files to FMI GlobLand FTP: %s!" % (dat))
