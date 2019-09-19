#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
import os,sys,glob,optparse
import time
import osgeo.gdal as gdal
import fcntl, struct
import pdb
import logging
import ConfigParser
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
    
    
def MDIlayercheck(filename,dataset):
    
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


###-----------------------------------------------------------------------------------------------------------
###-----------------------------------------------------------------------------------------------------------
###-----------------------------------------------------------------------------------------------------------


if __name__=="__main__":

    parser = optparse.OptionParser()

    parser.add_option("--date ",
                        action="store", type="string", dest="dat", default = None,
                        help="Processing date. Format: YYYYMMDD")
    #parser.add_option("--dem",
                    #action="store", type="string", dest="dempath", default = None,
                    #help="MDI file of DEM.")
    parser.add_option("--scm",
                    action="store", type="string", dest="scmpath", default = None,
                    help="MDI file of SCM.")
    parser.add_option("--tran",
                    action="store", type="string", dest="transpath", default = None,
                    help="MDI file of transmissivity map.")
    parser.add_option("--ndsi",
                    action="store", type="string", dest="ndsi", default=None,
                    help="MDI NDSI mask file")
    parser.add_option("-o","--outdir",
                    action="store", type="string", dest="odir", default=None,
                    help="Output directory.")

    
    #Abfragen der command line options
    (options, args) = parser.parse_args()

    options, args = parser.parse_args(sys.argv[1:])

    if options.dat==None:
        datin=datetime.now()
    else:
        datin=datetime.strptime(options.dat,"%Y%m%d")
    ## DEM
    #if options.dempath!=None:
        #demdir = options.dempath
        #if os.path.isfile(demdir)==False:
            #raise IOError("DEM file <%s> does not exist!" % (demdir))
    #else:
        #parser.error("DEM file is not specified! Try <%s --help>" % __file__.rsplit("/")[-1])

    # SCM
    if options.scmpath!=None:
        scmdir = options.scmpath
        if os.path.isfile(scmdir)==False:
            raise IOError("SCM file <%s> does not exist!" % (scmdir))
    else:
        parser.error("SCM file is not specified! Try <%s --help>" % __file__.rsplit("/")[-1])

    # NDSI
    if options.ndsi!=None:
        ndsi = options.ndsi
        if os.path.isfile(ndsi)==False:
            raise IOError("NDSI file <%s> does not exist!" % (ndsi))
    else:
        parser.error("NDSI file is not specified! Try <%s --help>" % __file__.rsplit("/")[-1])

    # Transmissivity map
    if options.transpath!=None:
        trandir = options.transpath
        if os.path.isfile(trandir)==False:
            raise IOError("Transmissivity map file <%s> does not exist!" % (trandir))
    else:
        parser.error("Transmissivity map is not specified! Try <%s --help>" % __file__.rsplit("/")[-1])
        
    # OutDIR
    if options.odir!=None:
        ODIR = options.odir
        if os.path.exists(ODIR)==False:
            raise IOError("VIIRS raw products directory <%s> does not exist!" % (ODIR))
    else:
        parser.error("Output directory is not specified! Try <%s --help>" % __file__.rsplit("/")[-1])

    
    #xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    # set parameters
    
    day=datin.day
    mon=datin.month
    year=datin.year
    md=datin.strftime("%m%d")
    dstr=datin.strftime("%Y-%m-%d")
    dstr2=datin.strftime("%Y%m%d")
    
    #logging
    #logdir = "/data/enveo/GL_SE/log"
    logdir = "/mnt/ws25data/lisi/GLOBLAND/DEVELOPEMENT/NH_processing_line/data"
    logyearfile = "%s/GloblandNH_%s.log" % (logdir,year)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(logyearfile)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)
    
    now = datetime.now()
    nowSTR = now.strftime("%Y-%m-%d %H:%M")
    

    outdir="%s/%s" % (ODIR,dstr2)
    lockdata = struct.pack('hhllhh', fcntl.F_WRLCK, 0, 0, 0, 0, 0)
    lockdatalink = struct.pack('hhllhh', fcntl.F_WRLCK, 0, 0, 0, 0, 0)

    # creats output directory
    if os.path.exists(outdir) == False:
        sys.exit("WARNING: NO output directory!")
            
    os.chdir(outdir)
    toa_list=[]
    anfiles=glob.glob("*data_an.mdi")
    print anfiles
    print len(anfiles)

    # processing of available toafiles
    for an_output_name in sorted(anfiles):
        
        base_name_out=an_output_name.split("B00500m_data_an.mdi")[0]
        in_output_name=base_name_out+"B01000m_data_in.mdi"
        msce_output_name=base_name_out+"B00500m_sce.mdi"
        
        F_ft_lock = base_name_out[:-1]+'.flock'
        logfilename=base_name_out+".info"
                
        #try:
        with open(F_ft_lock, "a+") as lockfile:
            try:
                fcntl.fcntl(lockfile.fileno(), fcntl.F_SETLK, lockdata)
            except IOError:
                filelogging(logfilename,"MESSAGE","File lock on < %s >" % base_in)
                continue
            
            # Controls if all layers are stored in file
            if (os.path.exists(an_output_name)):
                val=MDIlayercheck(an_output_name,"an")
                
            if (os.path.exists(in_output_name)):
                val=MDIlayercheck(in_output_name,"in")
                

                #xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

                #process SCE
                print os.path.exists(msce_output_name)
            if (os.path.exists(an_output_name)==True and os.path.exists(msce_output_name)==False):
                filelogging(logfilename,"MESSAGE","Start processing for SCE < %s >" % base_name_out)

                cmd=("crmdi -r %s,1 -o %s " % (an_output_name, msce_output_name))
                print cmd
                cmdexec(cmd)
                
                cmd =("i.opt.sceproc -g scamod -i %s -i %s -o %s,a --scda20 --coding cryoland --scm %s,1 --t2 %s,1 " % (an_output_name,in_output_name,msce_output_name,scmdir,trandir))
                print cmd
                cmdexec(cmd)

                filelogging(logfilename,"SUCCESS","SCE processing finished < %s >" % base_name_out)

        #except:
            #pass	  
            #SENDMAIL = "/usr/sbin/sendmail" # sendmail location
            #p = os.popen("%s -t" % SENDMAIL, "w")
            #p.write("To: globland@enveo.at\n")
            #p.write("Subject: Error processing SCE for %s\n" % (base_name_out))
            #p.write("\n") # blank line separating headers from body
            #p.write("Problems creating SCE: %s " % (base_name_out))
            #logger.info("%s : PROBLEMS CREATING SCE FOR THE DATE %s" % (nowSTR,dstr2))
            #sts = p.close()
                            
                    
            
