#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
import os,sys,glob,optparse
import time
import pdb

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

###-----------------------------------------------------------------------------------------------------------
###-----------------------------------------------------------------------------------------------------------
###-----------------------------------------------------------------------------------------------------------

if __name__=="__main__":

	parser = optparse.OptionParser()

	parser.add_option("--date ",
					action="store", type="string", dest="dat", default = None,
					help="Processing date. Format: YYYYMMDD")
	parser.add_option("-i","--inpdir",
				   action="store", type="string", dest="idir", default=None,
				   help="Rolling archive directory.")
	parser.add_option("-o","--outdir",
					action="store", type="string", dest="odir", default=None,
					help="Output directory.")



	#Abfragen der command line options
	(options, args) = parser.parse_args()

	options, args = parser.parse_args(sys.argv[1:])
	
	date=options.dat
	
	if date==None:
		parser.error("Date is not specified! Try <%s --help>" % __file__.rsplit("/")[-1])

	# InputDIR
	if options.idir!=None:
		IDIR = options.idir
		if os.path.exists(IDIR)==False:
			raise IOError("SLSTR rolling archive directory <%s> does not exist!" % (ODIR))
	else:
		parser.error("Input directory is not specified! Try <%s --help>" % __file__.rsplit("/")[-1])
		
	# OutDIR
	if options.odir!=None:
		ODIR = options.odir
		if os.path.exists(ODIR)==False:
			raise IOError("SLSTR raw products directory <%s> does not exist!" % (ODIR))
	else:
		parser.error("Output directory is not specified! Try <%s --help>" % __file__.rsplit("/")[-1])
		
	#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
	# set parameters
	tarfile = "%s_SLSTR_toa_ang.tar.gz" % date
	rollarch = "%s/%s" % (IDIR, tarfile)
	if os.path.isfile(rollarch)==False:
		raise IOError("Archive file %s doesn't exist!" % (rollarch))
	
	#output directory
	dateoutdir = "%s/%s" % (ODIR, date)
	
	if os.path.exists(dateoutdir) == False:
		cmd = "mkdir %s/%s" % (ODIR, date)
		cmdexec(cmd)
	
	#extract toa files
	cmd = "tar -xf %s -C %s" % (rollarch, dateoutdir)
	cmdexec(cmd)	
	
	tiffiles = glob.glob("%s/%s/*.tif" % (dateoutdir, tarfile[:-7]))
	tifflist = (" ").join(tiffiles)

	cmd = "mv %s %s" % (tifflist,dateoutdir)
	cmdexec(cmd)
	
