"""
    DenssUtils.py

    Copyright (c) 2019-2025, SAXS Team, KEK-PF

    Note that the original DENSS by T. Grant is licensed under GPL3.

    DENSS is available open source under the GPL 3.0 license.
    This means that anyone is free to download, utilize and develop the code,
    provided that any derivative code developed based on DENSS
    or its underlying algorithm is also distributed under the GPL 3.0 license
    and retains the original copyright.
"""
import numpy as np
import sys, argparse, os
import logging
import time
import molass.SAXS.denss as denss
import molass.SAXS.denss.options as dopts
from molass_legacy.KekLib.BasicUtils import Struct

MAXNUM_STEPS = 20000

def fit_data_impl(q, a, e, file=None, D=None, alpha=None, max_alpha=None, nes=2, extrapolate=True, gui=False, use_memory_data=False):
    """ fit_data_impl(q, a, e, file=None, D=None, alpha=None, max_alpha=None, nes=2, extrapolate=True, gui=False, use_memory_data=False)
    Fit the provided SAXS data using DENSS's fit_data logic.
    This function processes the input data and prepares it for DENSS reconstruction.

    Parameters
    ----------
    q : np.ndarray
        The q values of the SAXS data.
    a : np.ndarray
        The intensity values of the SAXS data.
    e : np.ndarray
        The error values of the SAXS data.
    file : str, optional
        The path to the data file. If None, data is taken from memory.
    D : float, optional
        The maximum dimension (Dmax) of the particle. If None, it will be estimated
        from the data.
    alpha : float, optional
        The regularization parameter. If None, it will be optimized.
    max_alpha : float, optional
        The maximum value for alpha during optimization.
    nes : int, optional
        The number of electrons per voxel.
    extrapolate : bool, optional
        If True, extrapolate the data to higher q values.
    gui : bool, optional
        If True, enable GUI mode for optimization.
    use_memory_data : bool, optional
        If True, use the provided q, a, e arrays instead of reading from file.

    Returns
    -------
    sasrec : denss.Sasrec
        The fitted Sasrec object containing the processed data.
    work_info : Struct
        A structure containing additional information about the fitting process.
    """
    Iq = np.vstack( [q, a, e] ).T

    # task: update this construction automatically from bin\denss.fit_data.py
    args = Struct(
        alpha = alpha,
        units = "a",
        max_alpha = max_alpha,
        output = "data_name",
        file = file,    # 
        dmax = D,
        nes = nes,
        n1 = None,
        n2 = None,
        ignore_errors = True,
        q = None,
        qmax = None,
        nq = None,
        r = None,
        max_dmax = None,
        qfile = None,
        rfile = None,
        extrapolate = extrapolate,
        nr = None,
        plot = True,
        log = True,
        write_shannon = True,
        )

    """
    DENSS strongly recommends to include I(q=0).
    To conform, we are using denss.fit_data.py here processing logic
    to modify the input data

    below is the extracted default processing from denss.fit_data.py
    lines[73:194] as of ver. 1.8.6
    """
### DENSS.bin.denss.fit_data.py copy & modify BEIGN ###
    alpha = args.alpha

    if args.output is None:
        fname_nopath = os.path.basename(args.file)
        basename, ext = os.path.splitext(fname_nopath)
        output = basename
    else:
        output = args.output

    if use_memory_data:
        # as invoked from LRF preview 
        Iq = np.array([q, a, e]).T
    else:
        if args.ignore_errors:
            Iq = np.genfromtxt(args.file, invalid_raise=False, usecols=(0, 1))
        else:
            Iq = np.genfromtxt(args.file, invalid_raise=False, usecols=(0, 1, 2))
    if len(Iq.shape) < 2:
        print("Invalid data format. Data file must have 3 columns: q, I, errors. Alternatively, disable errors with --ignore_errors option (sets errors to 1.0).")
        exit()
    if Iq.shape[1] < 3 or args.ignore_errors:
        print("WARNING: Only 2 columns given. Data should have 3 columns: q, I, errors.")
        print("WARNING: Setting error bars to 1.0 (i.e., ignoring error bars)")
        Iq2 = np.zeros((Iq.shape[0], 3))
        Iq2[:,:2] = Iq[:,:2]
        Iq2[:,2] += 1.0 #set error bars to 1.0
        Iq = Iq2
    Iq = Iq[~np.isnan(Iq).any(axis = 1)]
    #get rid of any data points equal to zero in the intensities or errors columns
    idx = np.where((Iq[:,1]!=0)&(Iq[:,2]!=0))
    Iq = Iq[idx]

    nes = args.nes

    if args.units == "nm":
        Iq[:,0] *= 0.1

    if args.n1 is None:
        n1 = 0
    else:
        n1 = args.n1
    if args.n2 is None:
        n2 = len(Iq[:,0])
    else:
        n2 = args.n2

    Iq_orig = np.copy(Iq)

    if args.dmax is None:
        #estimate dmax directly from data
        #note that denss.estimate_dmax does NOT extrapolate
        #the high q data, even though by default
        #denss.Sasrec does extrapolate.
        D, sasrec = denss.estimate_dmax(Iq, clean_up=True)
    else:
        D = args.dmax

    if args.max_dmax is None:
        args.max_dmax = 2.*D

    if args.rfile is not None:
        r = np.loadtxt(args.rfile,usecols=(0,))
    else:
        r = None

    if args.qfile is not None:
        qc = np.loadtxt(args.qfile,usecols=(0,))
    else:
        qc = None

    # print("Dmax = %.2f"%D)
    qmax = Iq[n1:n2,0].max()
    if (qc is None) and (args.extrapolate):
        qmaxc = qmax*3.0
    elif (qc is None):
        qmaxc = qmax
    else:
        qmaxc = qc.max()

    #let a user set a desired set of q values to be calculated
    #based on a given qmax and nq
    if (args.qmax is not None) or (args.nq is not None):
        if args.qmax is not None:
            qmaxc = args.qmax
        else:
            qmaxc = qmaxc
        if args.nq is not None:
            nqc = args.nq
        else:
            nqc = 501
        qc = np.linspace(0,qmaxc,nqc)
        #assume if they are giving args.qmax or args.nq, that they want to
        #disable extrapolation
        args.extrapolate = False

    nsh = qmax/(np.pi/D)
    nshc = qmaxc/(np.pi/D)
    # print("Number of experimental Shannon channels: %d"%(nsh))
    # print("Number of calculated Shannon channels: %d"%(nshc))
    if (nsh > 500) or (nshc>500):
        print("WARNING: Nsh > 500. Calculation may take a while. Please double check Dmax is accurate.")
        #give the user a few seconds to cancel with CTRL-C
        waittime = 10
        try:
            for i in range(waittime+1):
                sys.stdout.write("\rTo cancel, press CTRL-C in the next %d seconds. "%(waittime-i))
                sys.stdout.flush()
                time.sleep(1)
            print()
        except KeyboardInterrupt:
            print("Canceling...")
            exit()


    #calculate chi2 when alpha=0, to get the best possible chi2 for reference
    sasrec = denss.Sasrec(Iq[n1:n2], D, qc=qc, r=r, nr=args.nr, ne=nes, alpha=0.0, extrapolate=args.extrapolate)
    ideal_chi2 = sasrec.calc_chi2()

    if args.alpha is None:
        alpha = sasrec.optimize_alpha(gui=gui)
    else:
        alpha = args.alpha
    sasrec = denss.Sasrec(Iq[n1:n2], D, qc=qc, r=r, nr=args.nr, alpha=alpha, ne=nes, extrapolate=args.extrapolate)

    #implement method of estimating Vp, Vc, etc using oversmoothing
    sasrec.estimate_Vp_etal()

### DENSS.bin.denss.fit_data.py copy  & modify  END ###

    work_info = Struct(Iq=Iq, args=args, alpha=alpha, n1=n1, n2=n2, Iq_orig=Iq_orig)
    return sasrec, work_info

def fit_data(q, a, e, D=None, extrapolate=False, return_sasrec=False):
    """ fit_data(q, a, e, D=None, extrapolate=False, return_sasrec=False)
    Fit the provided SAXS data using DENSS's fit_data logic.
    This function processes the input data and prepares it for DENSS reconstruction.
    This is a simplified wrapper around fit_data_impl().

    Parameters
    ----------
    q : np.ndarray
        The q values of the SAXS data.
    a : np.ndarray
        The intensity values of the SAXS data.
    e : np.ndarray
        The error values of the SAXS data.
    D : float, optional
        The maximum dimension (Dmax) of the particle. If None, it will be estimated
        from the data.
    extrapolate : bool, optional
        If True, extrapolate the data to higher q values.
    return_sasrec : bool, optional
        If True, return the Sasrec object. If False, return qc, Ic, Icerr, D.

    Returns
    -------
    If return_sasrec is True:
        sasrec : denss.Sasrec
            The fitted Sasrec object containing the processed data.
    Else:
        qc : np.ndarray
            The q values used in the fitted data.
        Ic : np.ndarray
            The fitted intensity values.
        Icerr : np.ndarray
            The fitted error values.
        D : float
            The estimated maximum dimension (Dmax) of the particle.
    """
    sasrec, work_info = fit_data_impl(q, a, e,
                                        D=D,
                                        alpha=0,        # backward compatibility
                                        max_alpha=None,
                                        extrapolate=extrapolate,
                                        use_memory_data=True)
    if return_sasrec:
        return sasrec 
    else:
        return sasrec.qc, sasrec.Ic, sasrec.Icerr, sasrec.D

def fit_data_bc(q, a, e, extrapolate=False):    # backward compatible
    """ fit_data_bc(q, a, e, extrapolate=False)
    Fit the provided SAXS data using DENSS's fit_data logic.
    This function processes the input data and prepares it for DENSS reconstruction.
    This is a simplified wrapper around fit_data_impl().
    This function is for backward compatibility.
    It always sets alpha=0 and does not return the sasrec object.
    This function is for backward compatibility with older versions of molass.
    It is recommended to use fit_data() instead.

    Parameters
    ----------
    q : np.ndarray
        The q values of the SAXS data.
    a : np.ndarray
        The intensity values of the SAXS data.
    e : np.ndarray
        The error values of the SAXS data.
    extrapolate : bool, optional
        If True, extrapolate the data to higher q values.

    Returns
    -------
    qc : np.ndarray
        The q values used in the fitted data.
    Ic : np.ndarray
        The fitted intensity values.
    Icerr : np.ndarray
        The fitted error values.
    D : float
        The estimated maximum dimension (Dmax) of the particle.
    """
    sasrec, work_info = fit_data_impl(q, a, e,
                                        D=100,
                                        alpha=0,
                                        max_alpha=10,
                                        extrapolate=extrapolate,
                                        use_memory_data=True)
    return sasrec.qc, sasrec.Ic, sasrec.Icerr, sasrec.D

def get_dmax_with_datgnom(file_path):
    """ get_dmax_with_datgnom(file_path)
    Estimate Dmax from a DATGNOM file using AtsasDatGnomDdf.
    This function reads the DATGNOM file and estimates the best Dmax value.

    Parameters
    ----------
    file_path : str
        The path to the DATGNOM file.

    Returns
    -------
    dmax : float
        The estimated Dmax value.
    """
    from molass_legacy.Saxs.Rdf import AtsasDatGnomDdf
    ddf = AtsasDatGnomDdf(file_path)
    dmax = ddf.guess_best_dmax()
    return dmax

def get_argparser(return_args=False):
    """ get_argparser(return_args=False)
    Get the argument parser for DENSS.
    This function returns the argument parser for DENSS.
    If return_args is True, it returns the parsed arguments instead.
    This function is used to parse command line arguments for DENSS.

    Parameters
    ----------
    return_args : bool, optional
        If True, return the parsed arguments instead of the parser.

    Returns
    -------
    argparse.ArgumentParser or argparse.Namespace
        The argument parser or the parsed arguments.
    """
    parser = argparse.ArgumentParser(description="DENSS: DENsity from Solution Scattering.\n A tool for calculating an electron density map from solution scattering data",
                                     formatter_class=argparse.RawTextHelpFormatter)
    if return_args:
        args = dopts.parse_arguments(parser, return_args=True)
        return args
    else:
        return parser

def run_denss_impl(qc, ac, ec, dmax, data_name, steps=MAXNUM_STEPS, progress_cb=None, use_gpu=False, gui=False):
    """ run_denss_impl(qc, ac, ec, dmax, data_name, steps=MAXNUM_STEPS, progress_cb=None, use_gpu=False, gui=False)
    Run the DENSS reconstruction using the provided SAXS data.
    This function sets up and runs the DENSS reconstruction process.

    Parameters
    ----------
    qc : np.ndarray
        The q values of the SAXS data.
    ac : np.ndarray
        The intensity values of the SAXS data.
    ec : np.ndarray
        The error values of the SAXS data.
    dmax : float
        The maximum dimension (Dmax) of the particle.
    data_name : str
        The name of the data set.
    steps : int, optional
        The maximum number of steps for the reconstruction.
    progress_cb : callable, optional
        A callback function to report progress.
    use_gpu : bool, optional
        If True, use GPU acceleration for the reconstruction.
    gui : bool, optional
        If True, enable GUI mode for the reconstruction.

    Returns
    -------
    None
    """
    q = qc
    I = ac
    sigq = ec
    isfit = True    # it is assumed that the data is already fitted with fit_data_impl()

    sys.argv = ['dummy-script', '-f', data_name]
    if use_gpu:
        sys.argv += ['-gpu']
    parser = get_argparser()
    data_proxy = [q, I, sigq, I, dmax, isfit]
    args = dopts.parse_arguments(parser, data_proxy=data_proxy)

    qdata, Idata, sigqdata, qbinsc, Imean, chis, rg, supportV, rho, side, fit, final_chi2 = denss.reconstruct_abinitio_from_scattering_profile(
        # copied from denss/scripts/denss_abintio.py BEGIN
        q=args.q,
        I=args.I,
        sigq=args.sigq,
        dmax=args.dmax,
        qraw=args.qraw,
        Iraw=args.Iraw,
        sigqraw=args.sigqraw,
        ne=args.ne,
        voxel=args.voxel,
        oversampling=args.oversampling,
        recenter=args.recenter,
        recenter_steps=args.recenter_steps,
        recenter_mode=args.recenter_mode,
        positivity=args.positivity,
        positivity_steps=args.positivity_steps,
        extrapolate=args.extrapolate,
        output=args.output,
        steps=args.steps,
        ncs=args.ncs,
        ncs_steps=args.ncs_steps,
        ncs_axis=args.ncs_axis,
        ncs_type=args.ncs_type,
        seed=args.seed,
        support_start=args.support_start,
        shrinkwrap=args.shrinkwrap,
        shrinkwrap_old_method=args.shrinkwrap_old_method,
        shrinkwrap_sigma_start=args.shrinkwrap_sigma_start,
        shrinkwrap_sigma_end=args.shrinkwrap_sigma_end,
        shrinkwrap_sigma_decay=args.shrinkwrap_sigma_decay,
        shrinkwrap_threshold_fraction=args.shrinkwrap_threshold_fraction,
        shrinkwrap_iter=args.shrinkwrap_iter,
        shrinkwrap_minstep=args.shrinkwrap_minstep,
        chi_end_fraction=args.chi_end_fraction,
        write_xplor_format=args.write_xplor_format,
        write_freq=args.write_freq,
        enforce_connectivity=args.enforce_connectivity,
        enforce_connectivity_steps=args.enforce_connectivity_steps,
        enforce_connectivity_max_features=args.enforce_connectivity_max_features,
        cutout=args.cutout,
        quiet=args.quiet,
        # copied from denss/scripts/denss_abintio.py END
        gui=gui,
        DENSS_GPU=args.DENSS_GPU,
        progress_cb=progress_cb)

def run_denss_impl_dummy(qc, ac, ec, dmax, infile_name):
    """ run_denss_impl_dummy(qc, ac, ec, dmax, infile_name)
    A dummy implementation of run_denss_impl() for testing purposes.
    This function simulates the DENSS reconstruction process without performing any actual computation.
    It prints progress messages to the console.

    Parameters
    ----------
    qc : np.ndarray
        The q values of the SAXS data.
    ac : np.ndarray
        The intensity values of the SAXS data.
    ec : np.ndarray
        The error values of the SAXS data.
    dmax : float
        The maximum dimension (Dmax) of the particle.
    infile_name : str
        The name of the input data file.

    Returns
    -------

    """
    import time
    print("\n Step     Chi2     Rg    Support Volume")
    print(" ----- --------- ------- --------------")

    for j in range(100):
        time.sleep(0.1)
        sys.stdout.write("\r% 5i " % (j))
        sys.stdout.flush()

def get_denssfolder(parent=None):
    """ get_denssfolder(parent=None)
    Get the DENSS output folder.
    This function retrieves the DENSS output folder from the settings.
    If the folder does not exist, it creates it.

    Parameters
    ----------
    parent : object, optional
        The parent object to retrieve settings from. If None, uses global settings.

    Returns
    -------
    str or None
        The path to the DENSS output folder, or None if not set.
    """
    from molass_legacy._MOLASS.SerialSettings import get_setting
    from molass_legacy.KekLib.BasicUtils import mkdirs_with_retry

    analysis_folder = get_setting('analysis_folder')
    if analysis_folder is None or analysis_folder == "":
        return None

    denss_folder = (analysis_folder + '/DENSS').replace('\\', '/')
    if not os.path.exists(denss_folder):
        mkdirs_with_retry(denss_folder)

    return denss_folder

def get_outfolder(job_id=None, parent=None):
    """ get_outfolder(job_id=None, parent=None)
    Get the DENSS output folder for a specific job ID.
    This function retrieves the DENSS output folder and appends a job ID to it.
    If the folder does not exist, it creates it.

    Parameters
    ----------
    job_id : int, optional
        The job ID to append to the folder name. If None, uses '000' and increments if the folder exists.
    parent : object, optional
        The parent object to retrieve settings from. If None, uses global settings.

    Returns
    -------
    str or None
        The path to the DENSS output folder for the job, or None if the base folder
        is not set.
    """
    denss_folder = get_denssfolder(parent=parent)
    if denss_folder is None:
        return None

    import re
    if job_id is None:
        out_folder = denss_folder + '/000'
        while True:
            if os.path.exists(out_folder):
                out_folder = re.sub(r'/(\d+)$', lambda m: '/%03d' % (int(m.group(1)) + 1), out_folder)
            else:
                break
    else:
        out_folder_init = denss_folder + '/%03d' % job_id
        out_folder = out_folder_init
        i = 0
        while True:
            if os.path.exists(out_folder):
                i += 1
                out_folder =  out_folder_init + '_%d' % i
            else:
                break

    return out_folder

def get_denss_log_items(path):
    """ get_denss_log_items(path)
    Extract key-value pairs from a DENSS log file.
    This function reads a DENSS log file and extracts lines containing key-value pairs
    in the format "Final <key>: <value>".

    Parameters
    ----------
    path : str
        The path to the DENSS log file.

    Returns
    -------
    dict
        A dictionary containing the extracted key-value pairs.
    """
    import re
    item_re = re.compile(r'^\d+:\d+:\d+\s+Final\s+(.+):\s+(.+)$')
    ret_dict = {}
    with open(path) as log:
        for line in log:
            m = item_re.match(line)
            if m:
                ret_dict[m.group(1)] = float(m.group(2))
    return ret_dict

def run_pdb2mrc(in_file, queue=None):
    """ run_pdb2mrc(in_file, queue=None)
    Run the DENSS pdb2mrc script to convert a PDB file to an MRC file.
    This function invokes the DENSS pdb2mrc script as a subprocess to convert
    a PDB file to an MRC file. It can report progress through a queue.

    Parameters
    ----------
    in_file : str
        The path to the input PDB file.
    queue : multiprocessing.Queue, optional
        A queue to report progress. If None, no progress is reported.
        
    Returns
    -------
    str or None
        The path to the generated MRC file, or None if the conversion failed.
    """
    import time
    from molass_legacy.KekLib.SubProcess import Popen   # suppresses the child process window.
    from molass_legacy.KekLib.BasicUtils import get_home_folder
    print("Generating an mrc file.")
    script_path = os.path.join(get_home_folder(), r'molass\SAXS\denss\scripts\denss_pdb2mrc.py')
    python  = sys.executable.replace('pythonw.exe', 'python.exe')       # running with pythonw.exe seems inappropriate
    out_file = in_file.replace('.pdb', '')
    cmd = [python, script_path, '-f', in_file, '-o', out_file]
    # print(cmd)

    """
        currently not receiving the stdout of the child process.
        TODO: better print the progress.
    """
    p = Popen(cmd)
    while p.poll() is None:
        time.sleep(1)
        if queue is not None:
            queue.put((1, '.'))
    returncode = p.poll()

    if queue is not None:
        queue.put((1, '\n'))

    if returncode == 0:
        out_file = out_file + ".mrc"
        print("Generated %s" %  out_file)
    else:
        if queue is not None:
            queue.put((1, p.stderr.decode() ))
        out_file = None
        print("Failed with returncode: %d" % returncode)

    return out_file
