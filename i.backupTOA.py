#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os,sys,glob,optparse
import shutil
import pdb

#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
if __name__=="__main__":

	parser = optparse.OptionParser()

	parser.add_option("--date ",
						action="store", type="string", dest="dat", default = None,
						help="Processing date. Format: YYYYMMDD")

	parser.add_option("-o","--outdir",
					action="store", type="string", dest="odir", default=None,
					help="Output directory.")
	
	parser.add_option("-i","--inputdir",
					action="store", type="string", dest="idir", default=None,
					help="Input directory.")
	
	#Abfragen der command line options
	(options, args) = parser.parse_args()

	options, args = parser.parse_args(sys.argv[1:])

	if options.dat!=None:
		datin=options.dat
	else:
		parser.error("Date is not specified! Try <%s --help>" % __file__.rsplit("/")[-1])
	
	# OutDIR
	if options.odir!=None:
		ODIR = options.odir
		if os.path.exists(ODIR)==False:
			raise IOError("Output directory <%s> does not exist!" % (ODIR))
	else:
		parser.error("Output directory is not specified! Try <%s --help>" % __file__.rsplit("/")[-1])

	# INPUTDIR
	if options.idir!=None:
		IDIR = options.idir
		if os.path.exists(IDIR)==False:
			raise IOError("Input directory <%s> does not exist!" % (IDIR))
	else:
		parser.error("Input directory is not specified! Try <%s --help>" % __file__.rsplit("/")[-1])
		
	
    #xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

	indir="%s/%s" % (IDIR,datin)
	ndir="%s_SLSTR_toa_ang" % (datin)
	tarfile="%s/%s.tar.gz" % (ODIR,ndir)
	
	if not os.path.exists(tarfile):
		os.chdir(indir)
		try:
			if not os.path.exists(ndir):
				os.mkdir(ndir)
			files = glob.glob("*data_??*")
			auxfiles=glob.glob("*aux_tn*")
			
			if len(auxfiles)!=0:
				infofiles.sort()
				for ifile in auxfiles:
					shutil.move(ifile,ndir)
			
			if len(files)!=0:
				files.sort()
				for f in files:
					shutil.move(f,ndir)
					
			else:
				SENDMAIL = "/usr/sbin/sendmail" # sendmail location
				p = os.popen("%s -t" % SENDMAIL, "w")
				p.write("To: globland@enveo.at\n")
				p.write("Subject: GlobLand: No files available for compressing - day %s\n" % (datin))
				p.write("\n") # blank line separating headers from body
				p.write("Problems creating compressed directory: %s_SLSTR_toa_ang" % (datin))
				sts = p.close()
				
			if not os.path.exists("%s.tar.gz"):
				os.system("tar -zcf %s.tar.gz %s" % (ndir,ndir))
			
			if not os.path.exists(tarfile):
				shutil.move(ndir+".tar.gz",ODIR)
			os.chmod(tarfile, 0777)	
		except:
			SENDMAIL = "/usr/sbin/sendmail" # sendmail location
			p = os.popen("%s -t" % SENDMAIL, "w")
			p.write("To: globland@enveo.at\n")
			p.write("Subject: GlobLand: Problems creating tar file - day %s\n" % (datin))
			p.write("\n") # blank line separating headers from body
			p.write("Problems creating compressed directory: %s_SLSTR_toa_ang" % (datin))
			sts = p.close()
	else:
		print "File < %s.tar.gz > exists already!" % (ndir)
	os.chdir("%s" % IDIR)
	if os.path.exists(tarfile):
		try:
			cmd="rm %s -r" % (indir)
			print cmd
			os.system(cmd)
		except:
			pass
