#!/usr/bin/env python
# This python environment line will need to be changed for ACI-b
# For ACI-b, replace crunchbang patch with the path below
#  /usr/bin/env python  --- Use this for aci-b and local
#! /usr/global/python/2.7.3/bin/python ---- Use this for LionX
import sys, os
from textwrap import dedent

# NOTE: This script deliberately does not contain calls to
# non-standard library modules, and should remain one file long

"""
NOTE: This is written in an object-oriented way.  There are two
main classes, Host and Submittable.

Host controls everything having to do with the environment that
the job will be submitted on.  It is subclassed by two classes,
Queue and Interactive, each used for hosts with a PBS queueing
system and ones that are interactive, respectively.  Then, each
host (i.e. LionXF, Cyberstar, Local, etc.) are derived from
Queue or Interactive.  Thus each class shares as much in common
with the parent class which cuts down on programming-by exception.
Each class may override the parent class's methods, allowing for
greater flexability.

The same approach is taken with Submittable. Submittable controls
the input file and how it will be submitted.  Submittable is
subclassed by Scratch and Noscratch, which are for programs that
require explicit handling of the scratch directory and those that
don't, respectively.  Each program is then a subclass of these
(i.e. Dalton and POVRay of Noscratch, ADF, NWChem, etc. of Scratch).

Although this file is twice as long as the old procedural approach,
it is twice as easy to maintain.  For example, in the old method,
the submit_interactive_scratch routine was very long, but mostly
because of multiple if statements required for each program type.
In this new method, each class implements its own versions of
methods when necessary, making it easier to maintain a specific
program's submit properties.
"""

def main():
    '''\
    Submit a job.  The program automatically determines what program type
    and how to submit based on the extention, the contents of the input file,
    and the name of the host you are submitting on.  The input filenames may
    be given explicitly or piped in from the standard input.

    If list_limits is given on the command line, the job limits on the current
    host will be given, and the program will terminate.

    See man page for more info.
    '''

   ## Determine the host file system and it's properties
   #host = determine_host(os.uname()[1])
    # get the fully qualified domain name and use that to determine host
    import socket
    host = determine_host(socket.getfqdn())

    # Check arguments
    from argparse import ArgumentParser, RawDescriptionHelpFormatter
    parser = ArgumentParser(description=dedent(main.__doc__),
                            formatter_class=RawDescriptionHelpFormatter,
                            prefix_chars='-+')
    parser.add_argument('--version', action='version', version='%(prog)s 1.5')
    parser.add_argument('input_files', nargs='*', default=sys.stdin,
                        help='The input files to submit.')
    parser.add_argument('-o', '--out', help='Specifies a non-default output '
                        'file to use.  You must include the extention you '
                        'want.', metavar='LOGFILE')
    parser.add_argument('-s', '--scratch', help='Change the scratch directory '
                        "from the default '%(default)s' to %(metavar)s.",
                        default=host.scratch)
    # Options for Abinit only
    abinit = parser.add_argument_group('opts for ABINIT')
    abinit.add_argument('--psp', help='Define the paths for the '
                       'psuedopotentials to add to the .files file', nargs='+')
    # Options for Dalton only
    dalton = parser.add_argument_group('opts for Dalton')
    dalton.add_argument('-r', '--restart', help='Restart file to use.  Do not '
                        'include the .tar.gz extention.')
    dalton.add_argument('-R', '--restartdir', help='Directory of restart files.  '
                        'This option is most useful for globbing to generate Raman '
                        'spectra.  Use the exact path!')
    # Options for POV-Ray only
    povray = parser.add_argument_group('opts for POV-Ray')
    povray.add_argument('--vmd', help='Use a multiple of the default height '
                        'and width for VMD.', type=float)
    # Options for jobs submitted on a queueing system
    queue = parser.add_argument_group('opts for hosts with queueing systems',
                             'These have no effect on an interactive system')
    queue.add_argument('-n', '--nodes', help='The number of nodes to run on.',
                      type=int)
    queue.add_argument('-p', '--ppn', help='The processors per node to use. '
                       'To explicitly not use this (an option on LionXF and '
                       'LionXG) then use -1', type=int)
    queue.add_argument('-w', '--wall', help='The wall time to request in '
                       'any of: sec, min:sec, hour:min:sec, day:hour:min:sec.',
                       metavar='WALLTIME')
    queue.add_argument('-m', '--mem', help='Request a particular amount of'
                       'memory per processor.  Not required. Given in MB.',
                       type=int)
    queue.add_argument('-a', '--all', help='Specify nodes, ppn, wall and mem '
                       'with one option, in that order.  i.e., '
                       '--all 8 1 48:00:00 2000 to specify 8 nodes, 1 ppn,'
                       '48:00:00 walltime and 2000 MB. ',
                       nargs=4, metavar=('NODES', 'PPN', 'WALLTIME', 'MEM'))
    queue.add_argument('-e', '--exclusive', help='Specify nodes and wall'
                       'with one option, in that order.  i.e., '
                       '--all 1 48:00:00 to specify all resources from 2 nodes'
                       'and 48:00:00 walltime. ',
                       nargs=2, metavar=('NODES', 'WALLTIME'))
    queue.add_argument('-d', '--default', help='Chooses the default values '
                       'for nodes, ppn, wall and mem for this host.  You '
                       'may override the hard-coded defaults with a .submitrc '
                       'file in your home directory', action='store_true',
                       default=False)
    queue.add_argument('--nolimit', default=True, dest='check_limits',
                       action='store_false', help='By default, this program '
                       'will check your job parameters to make sure they are '
                       'within the limits of the computer.  This switch will '
                       'disable that check.')
    queue.add_argument('-S', '--script', help='Creates the script file '
                       'without submitting.  Useful if you want to edit the '
                       'job.', action='store_true', default=False)
    queue.add_argument('-ex', '--exact', help='Use exact node arrangement'
                       'on LionXF or LionXG.', action='store_true', default=False)
    queue.add_argument('-O', '--open', help='Use the open queue on ACI-b',
                        action='store_true', default=False)
    queue.add_argument('-A', '--allocation', help="Select allocation to submit to, "
                       "'a', 'e', or 'c'. Default is 'o', open queue;"
                       "'a' is our standard, paid allocation; "
                       "'e' is basic computing nodes, lxj18_e_g_bc_default; " 
                       "'c' is another allocation of standard computing nodes, lxj18_c_t_sc_default;",
                        type=str, default='o' )
    # Options for jobs submitted on an interactive system
    inter = parser.add_argument_group('opts for interactive hosts',
                             'These have no effect on a queueing system')
    inter.add_argument('-D', '--debug', action='store_true', default=False,
                       help='Open output file with less upon completion.')
    inter.add_argument('--pid', action='store_true', default=False,
                       help='Adds the process ID number to the output file '
                       'name.')
    inter.add_argument('--nice', help='The niceness (0 to 20), '
                       '%(default)i is default.', default=19, type=int,
                       choices=range(21), metavar='NICE')
    inter.add_argument('-q', '--quiet', action='store_true', default=False,
                       help='Do not print anything to screen.')
    args, subopts = parser.parse_known_args()

    # store input arguments as integers for possible manipulation later
    if args.all:
        args.all[0] = int(args.all[0])
        args.all[1] = int(args.all[1])
        args.all[3] = int(args.all[3])

    args.lexclusive = False
    if args.exclusive:
        args.exclusive[0] = int(args.exclusive[0])
        args.lexclusive = True

    # Verify the options based on the host
    opts, input_files = host.verify_options(args)

    # Select the designated allocation on ACI/HPC
    import json
    try: 
        with open(os.getenv('ALLOCATIONS')) as f:
            data = f.read()
        allocations = json.loads(data)
        args.allocation = args.allocation.lower()
        try:
            host.queue = allocations[args.allocation]
        except KeyError:
            sys.exit("Unrecognized allocation. Current allocations available: " + ', '.join(list(allocations.keys())))
    except TypeError:
        if not host.local:
            sys.exit("You need to set the environment variable ALLOCATIONS and point it to the correct file")
    except IOError:
        if not host.local:
            sys.exit("You need to set the environment variable ALLOCATIONS and point it to the correct file")

    # Loop over files, submitting each one
    for f in input_files:

        # Make sure the file exists
        try:
            with open(f) as dummy:
                pass
        except IOError as i:
            print(str(i), file=sys.stderr)
            print('Skipping...', file=sys.stderr)

        # Determine the file type
        input_file = determine_file_type(f, host, opts, subopts)

        # Submit this file
        try:
           input_file.submit()
        except AttributeError:
           # Skip if an unrecognized extention was given
           pass


def abs_file_path(filename, env=None):
    '''This function takes a filename with a path and returns the
    absolute path.
    '''
    from os.path import expanduser, expandvars, abspath

    absfile = abspath(expandvars(expanduser(filename)))
    # Now replace front with $HOME if requested
    if env:
        if os.environ['HOME'] in absfile:
            i = len(os.environ['HOME']) + 1
            # Assemble absolute path, using the $HOME variable
            absfile = os.path.join('$HOME', absfile[i:])

    return absfile


def determine_file_type(input_file, host, opts, subopts):
    '''Determine the program based on it's extention.
    Returns the class associated witt this program.'''

    # Determine what job type this is.  Use the extension
    try:
        program = { 'pov' : 'povray', 'ini': 'povray',
                    'inp' : 'adf',    'run': 'adf',
                    'nw'  : 'nwchem', 'dal': 'dalton',
                    'g09' : 'gaussian', 'qchem' : 'qchem',
                    'in'  : 'abinit', 'dim': 'dim',
                    'script' : None,
                  }[os.path.splitext(input_file)[1][1:]]
    except KeyError:
        print('Unrecognized extention:',
              os.path.splitext(input_file)[1][1:]+'.', 'Skipping...',
              file=sys.stderr)
        return
    else:
        # BAND could be mistaken as ADF.  Check and change as necessary.
        # Do this by looking in file to find the band executable command.
        if program == 'adf':
            # Read in file as a single string and search string as a whole.
            try:
                fs = open(input_file).read()
            except IOError:
                print('File', input_file, 'does not exist. Skipping...',
                      file=sys.stderr)
                return
            if '$ADFBIN/band' in fs:
                program = 'band'
            elif "$ADFBIN/reaxff" in fs:
                program = 'reaxff'

    # Now make a submittable object out of this file
    if program == 'adf':
        return ADF(input_file, host, opts, subopts)
    elif program == 'nwchem':
        return NWChem(input_file, host, opts, subopts)
    elif program == 'band':
        return BAND(input_file, host, opts, subopts)
    elif program == 'reaxff':
        return ReaxFF(input_file, host, opts, subopts)
    elif program == 'povray':
        return POVRay(input_file, host, opts, subopts)
    elif program == 'abinit':
        return ABINIT(input_file, host, opts, subopts)
    elif program == 'dalton':
        return Dalton(input_file, host, opts, subopts)
    elif program == 'qchem':
        return QChem(input_file, host, opts, subopts)
    elif program == 'gaussian':
        return Gaussian(input_file, host, opts, subopts)
    elif program == 'dim':
        return DIM(input_file, host, opts, subopts)
    elif program is None:
        return PBSScript(input_file, host, opts, subopts)


def determine_host(hostname):
    '''Return the correct host class based on the name'''
    if 'chem.psu.edu' in hostname:
        return Local(hostname)
    elif 'science.psu.edu' in hostname:
        return Local(hostname)
    elif 'stampede.tacc.utexas.edu' in hostname:
        return Stampede('stampede.tacc.utexas.edu')
    elif 'acib.production.int.aci.ics.psu.edu' in hostname:
        return ACIb(hostname)
    elif 'hpc.psu.edu' in hostname:
        return Hpc(hostname)
    else:
        sys.exit('Unknown host!  Speak to your sysadmin.')



class Submittable(object):
    '''Base class that implemets basic functionality for objects
    that are submittable.  This is intended to be subclassed and many
    of the methods may be overwritten.'''

    def __init__(self, filename, host, opts, subopts):
        '''Initiallizes the Submittable class, accepting the
        command-line arguments.'''
        from os.path import relpath, split, splitext, basename

        # Store the options
        self.out          = opts.out
        self.psp          = opts.psp
        self.restart      = opts.restart
        self.restartdir   = opts.restartdir
        self.nodes        = opts.nodes
        self.ppn          = opts.ppn
        self.wall         = opts.wall
        self.mem          = opts.mem
        self.check_limits = opts.check_limits
        self.debug        = opts.debug
        self.pid          = opts.pid
        self.nice         = opts.nice
        self.quiet        = opts.quiet
        self.script       = opts.script
        self.exact        = opts.exact
        self.open         = opts.open
        self.lexclusive   = opts.lexclusive

        # Keep the suboptions
        self.subopts = subopts

        # Store the host information
        self.host = host

        # Grab the filename and extention separetely
        self.noext, self.ext = splitext(filename)
        self.ext = self.ext[1:]

        # Find the base file name (no path, no ext) and the path
        self.path, base = split(self.noext)

        # Store both noextension names under one heading
        self.noext = { 'full' : self.noext, 'base' : base }

        # Full input filename and base of the input filename
        self.input = { 'full' : filename, 'base' : basename(filename) }

        # Make output filename and the base of the input filename
        if self.out:
            self.output = abs_file_path(self.out)
            # Make sure all names match the output.
            self.noext['full'] = splitext(self.output)[0]
            self.noext['base'] = basename(self.noext['full'])
        else:
            self.output = self.output_name()

        # Define output base and store both full and base name in one
        self.output = { 'full' : self.output, 'base' : basename(self.output) }

        # Add pid to output extention if appropriate
        if self.pid:
            self.output['full'] = '.'.join([self.noext['full'],
                                            str(os.getpid()), 'out'])
            self.output['base'] = basename(self.output['full'])
            self.noext['full']  = splitext(self.output['full'])[0]
            self.noext['base']  = basename(self.noext['full'])

    def output_name(self):
        '''Creates the full output file name. Should be overridden
        in the sub class if the program does not use .out files.'''
        return '.'.join([self.noext['full'], 'out'])

    def edit_input(self):
        '''Edits the input file, changing location-specific things.'''
        # Read in file as a single string
        fs = open(self.input['full']).read()

        rewrite = False
        # See if we need to replace references to gpfs with amp or vice versa
        if self.host.local and 'gpfs/work' in fs:
            fs = fs.replace('gpfs/work', 'amphome')
            rewrite = True
        elif not self.host.local and 'amphome' in fs:
            fs = fs.replace('amphome', 'gpfs/work')
            rewrite = True

        # Re-write to file if something changed
        if rewrite:
            with open(self.input['full'], 'w') as f:
                print(fs, file=f)

    def submit(self):
        '''Submits the job'''

        # See if the input file must be edited, and do so if necessary
        self.edit_input()

        # Submit interactively
        if self.host.submit_type == 'interactive':
            self.submit_interactive()
            # Pull up output file if debugging
            if self.debug:
                from subprocess import call
                call([self.display_prog(), self.output['full']])

        # Submit by queue
        else:
            if self.host.queue_type == 'PBS':
                self.submit_PBS_queue()
            else:
                self.submit_SBATCH_queue()


    def submit_PBS_queue(self):
        '''Submits the file on the PBS queueing system.'''
        from subprocess import call
        from os import chmod, environ

        # If a required argument is missing, request it from the user now
        n = 'How many nodes do you want assigned? [{0}] '
        n = n.format(self.host.defaultnodes)
        p = 'How many processors per node? [{0}] '.format(self.host.defaultppn)
        w = 'Requested wall clock time? [{0}] '.format(self.host.defaultwall)
        m = 'How much memory per processor do you want (MB) [{0}] '
        m = m.format(self.host.defaultmem)
        print('File', self.input['full'])
        nodes = self.nodes if self.nodes else raw_input(n)
        ppn   = self.ppn   if self.ppn   else raw_input(p)
        wall  = self.wall  if self.wall  else raw_input(w)
        mem   = self.mem   if self.mem   else raw_input(m)

        # Default the values if none are still given
        nodes = nodes if nodes else self.host.defaultnodes
        ppn   = ppn   if ppn   else self.host.defaultppn
        wall  = wall  if wall  else self.host.defaultwall
        mem   = mem   if mem   else self.host.defaultmem

        # Make sure that the options are the correct type
        nodes, ppn, wall, mem = self.host.type_check(nodes, ppn, wall, mem)
        # Check that the values are OK and format them
        if self.check_limits: self.host.check_limits(nodes, ppn, wall, mem)

        # Open the submit script and create it
        script = '.'.join([self.noext['full'], 'script'])
        with open(script, 'w') as sc:
            # Q-Chem is a little more particular
            if self.ext == 'qchem':
                print('#!/bin/csh', file=sc)
            print('#', file=sc)
            if self.exact: print('#PBS -W x=nmatchpolicy:exactnode', file=sc)
            if ppn == -1:
                procs = '#PBS -l nodes={0[0]:d}'
            else:
                procs = '#PBS -l nodes={0[0]:d}:ppn={0[1]:d}'
            print(procs.format([nodes, ppn]), file=sc)
            print('#PBS -l walltime={0}'.format(self.host.td2hms(wall)),
                                                file=sc)
            # Add memory request if necessary
            if mem is not None:
                print('#PBS -l pmem={0:d}mb'.format(mem), file=sc)
            # Direct output to correct files
            print('#PBS -j eo', file=sc)

            print('#PBS -e {name}.err'.format(name=self.noext['full']), file=sc)
            # Add email options
           #print('#PBS -m ae', file=sc)
           #print('#PBS -M {user}@psu.edu'.format(user=environ['USER']),
           #                                file=sc)
            # Create the remainder of the script
            print(self.create_script(pp=abs(nodes*ppn)), file=sc)

        # Make the script executable
        chmod(script, 0o755)

        # The job name can only be 15 bytes and must begin with a letter
        jobname = self.noext['base'][0:15]
        if jobname[0].isdigit(): jobname = 'q'+jobname[1:]

        # Submit the script unless otherwise directed
        if not self.script:
            print('Submitting {0} job {1}...'.format(type(self).__name__,
                                                     self.noext['base']))
            if self.open:
                call(['qsub', '-N', jobname, script])
            else:
                call(['qsub', '-A','%s'%(self.host.queue),'-N',jobname, script])
            print()
        else:
            from os.path import relpath
            script = relpath(script)
            print('Wrote {0} job script {1}...'.format(type(self).__name__,
                                                       script))
            print('Submit with "qsub -N {0} {1}"'.format(jobname, script))
            print()

    def create_script(self, **kwargs):
        '''Creates the .script file used for submitting on queueing hosts.
        Must be overridden in the subclass.'''
        pass

    def executable(self):
        '''The executable to use to submit this script interactively.
        Must be overridden in the subclass.'''
        pass

    def copy_input(self, tmpdir):
        '''Copies input to the temp directory.
        May be overwritten by the subclass'''
        from shutil import copy
        import os.path
        from os.path import join
        # hack to get TAPE21 and TAPE16 files into scratch for densf calculations
        bases = os.path.splitext(self.input['full'])[0]
        if (os.path.isfile(bases+".t21")):
             copy(bases+".t21", join(tmpdir, "TAPE21"))
        if (os.path.isfile(bases+".t16")):
             copy(bases+".t16", join(tmpdir, "TAPE16"))

        copy(self.input['full'], join(tmpdir, self.input['base']))

    def add_input(self, arguments):
        '''Appends the input files to the executable statement
        in the appropriate way.  May be overwritten by the subclass'''
        return arguments + [self.input['full']]

    def stdstreams(self, **kwargs):
        '''Returns the proper standard in, out and error.
        May be overwritten by the subclass'''
        if self.quiet:
            return None, open(self.output['full'], 'w'), open('logfile', 'w')
        else:
            return None, open(self.output['full'], 'w'), sys.stderr

    def clean(self, **kwargs):
        '''Used to clean up after a job.   Returns the sources and destinations
        of files to copy.  May be overwritten by the subclass'''
        return None, None

    def display_prog(self):
        '''The program to display the results of execution (for debugging).
        May be overwritten by the subclass'''
        return 'less'


    def submit_SBATCH_queue(self):
        '''Submits the file on the SBATCH queueing system.'''
        from subprocess import call
        from os import chmod, environ

        # If a required argument is missing, request it from the user now
        n = 'How many nodes do you want assigned? [{0}] '
        n = n.format(self.host.defaultnodes)
        p = 'How many processors per node? [{0}] '.format(self.host.defaultppn)
        w = 'Requested wall clock time? [{0}] '.format(self.host.defaultwall)
        m = 'How much memory per processor do you want (MB) [{0}] '
        m = m.format(self.host.defaultmem)
        print('File', self.input['full'])
        print(self.lexclusive)
        if self.lexclusive:
            nodes = self.nodes if self.nodes else raw_input(n)
            wall  = self.wall  if self.wall  else raw_input(w)
            # ppn   = self.ppn   if self.ppn   else raw_input(p)
            # mem   = self.mem   if self.mem   else raw_input(m)
            ppn = 0
            mem = 0
        else:
            nodes = self.nodes if self.nodes else raw_input(n)
            ppn   = self.ppn   if self.ppn   else raw_input(p)
            wall  = self.wall  if self.wall  else raw_input(w)
            mem   = self.mem   if self.mem   else raw_input(m)

        # Default the values if none are still given
        nodes = nodes if nodes else self.host.defaultnodes
        ppn   = ppn   if ppn   else self.host.defaultppn
        wall  = wall  if wall  else self.host.defaultwall
        mem   = mem   if mem   else self.host.defaultmem

        # Make sure that the options are the correct type
        nodes, ppn, wall, mem = self.host.type_check(nodes, ppn, wall, mem)
        # Check that the values are OK and format them
        if self.check_limits: self.host.check_limits(nodes, ppn, wall, mem)

        # Open the submit script and create it
        script = '.'.join([self.noext['full'], 'script'])
        with open(script, 'w') as sc:
            # Q-Chem is a little more particular
            if self.ext == 'qchem':
                print('#!/bin/csh', file=sc)
            else:
                print('#!/bin/bash', file=sc)
            print('#', file=sc)
            # print(self.lexclusive)

            print('#SBATCH --time={0}'.format(self.host.td2hms(wall)),
                                                file=sc)
            print("#SBATCH --nodes={0:}".format(nodes), file=sc)
        

            if self.lexclusive:
                print("#SBATCH --exclusive", file=sc)
            #else:
            if ppn != -1:
                print("#SBATCH --ntasks-per-node={0:}".format(ppn), file=sc)
            # Add memory request if necessary
            if mem is not None:
                print('#SBATCH --mem-per-cpu={0:d}mb'.format(mem), file=sc)


            if self.host.queue != 'open':
                print('#SBATCH --account={}'.format(self.host.queue), file=sc)
                print('#SBATCH --partition={}'.format('sla-prio'), file=sc)
            else :
                print('#SBATCH --account={}'.format(self.host.queue), file=sc)
                print('#SBATCH --partition={}'.format('open'), file=sc)
                
            # Create the remainder of the script
            print('#SBATCH --error {name}.err'.format(name=self.noext['full']), file=sc)
            print(self.create_script(pp=abs(nodes*ppn)), file=sc)

        # Make the script executable
        chmod(script, 0o755)

        # The job name can only be 15 bytes and must begin with a letter
        jobname = self.noext['base'][0:15]
        if jobname[0].isdigit(): jobname = 'q'+jobname[1:]

        # Submit the script unless otherwise directed
        if not self.script:
            print('Submitting {0} job {1}...'.format(type(self).__name__,
                                                     self.noext['base']))
            call(['sbatch', '--job-name',jobname, script])
        else:
            from os.path import relpath
            script = relpath(script)
            print('Wrote {0} job script {1}...'.format(type(self).__name__,
                                                       script))
            print('Submit with "sbatch --job-name {0} {1}"'.format(jobname, script))
            print()


class PBSScript(Submittable):
    '''Class to submit a PBS job script directly'''

    def __init__(self, host, filename, opts, subopts):
        '''Initiallizes the PBSScript class'''
        Submittable.__init__(self, host, filename, opts, subopts)
        self.debug = False

    def submit_interactive(self):
        '''It is not possible to submit a PBS job interactively'''
        string = 'File {0} is a PBS job file.'.format(self.input['base'])
        print(string, 'Submitting interactively makes no sense.',
              file=sys.stderr)
        print('Skipping...', file=sys.stderr)

    def submit_PBS_queue(self):
        '''Submit to the PBS queueing system'''
        from subprocess import call

        # The job name can only be 15 bytes and must begin with a letter
        jobname = self.noext['base'][0:15]
        if jobname[0].isdigit(): jobname = 'q'+jobname[1:]

        # Submit the script
        print('Submitting {0} job {1}...'.format(type(self).__name__,
                                                     self.noext['base']))
        call(['qsub', '-N', jobname, self.input['full']])
        print()



class Scratch(Submittable):
    '''This provides the submit_interactive class for programs
    that required explicit scratch handling.'''

    def __init__(self, host, filename, opts, subopts):
        '''Initiallizes the Scratch class'''
        Submittable.__init__(self, host, filename, opts, subopts)

    def submit_interactive(self):
        '''Submits a job interactively
        with an excplicit scratch directory'''
        from shutil import rmtree, copy, Error
        from subprocess import call
        from os.path import join
        from os import getpid, mkdir, remove

        # Make a temp dir in the scratch directory
        tmpdir = '.'.join([type(self).__name__, str(getpid())])
        tmpdir = join(self.host.scratch, tmpdir)

        # Print head if not quiet
        if not self.quiet:
            from time import strftime
            head = '''\
***********************************************************************
******************  OUTPUT FROM SUBMIT SHELL SCRIPT  ******************
***********************************************************************

   Invocation : {submit} {params}

   Job submitted at : {date}

   Input file  : {file}
   Output file : {output}
   PID         : {pid:d}
   Nice        : {nice:d}
   Input dir   : {input}
   Scratch dir : {scratch}
   Program     : {progexe}
'''
            print(head.format(
              submit=sys.argv[0],  params=' '.join(sys.argv[1:]),
              date=strftime('%c'), file=self.input['full'],
              output=self.output['full'], pid=getpid(), nice=self.nice,
              input=self.path, scratch=tmpdir, progexe=self.executable()),
              file=sys.stderr)

        # Make the temp directory
        mkdir(tmpdir)
        # if TAPE16 or TAPE21 files exist move them into temp dir
        import os.path
        if (os.path.isfile("TAPE21")):
             copy("TAPE21", tmpdir)
        if (os.path.isfile("TAPE16")):
             copy("TAPE16", tmpdir)
        # Copy input file into that directory
        self.copy_input(tmpdir)
        # Return where the output is going (in input is coming from)
        stdin, stdout, stderr = self.stdstreams(tmpdir=tmpdir)
        # Make a soft link of the logfile if appropriate
        self.link_log(tmpdir)
        # Make the submittable argument list
        arguments = self.add_input(['nice', '-n', str(self.nice)])
        # Submit
        call(arguments, stdout=stdout, stderr=stderr, stdin=stdin, cwd=tmpdir)
        # Clean up
        sources, dests = self.clean(tmpdir=tmpdir)
        # Copy the sources to the dest
        for source, dest in zip(sources, dests):
            try:
                copy(source, dest)
            except (IOError, OSError):
                pass
            except Error:
                # If there is a link, remove the link before continuing
                remove(dest)
                try:
                    copy(source, dest)
                except (IOError, OSError):
                    pass
        # Remove the temporary directory
        rmtree(tmpdir, True)

        # Print tail
        if not self.quiet:
            print('''\

   Job finish at : {date}

***********************************************************************
***********************************************************************
***********************************************************************
'''.format(date=strftime('%c')))

    def link_log(self, tmpdir):
        '''Make a soft link to the logfile in the submitted directory.
        Does nothing by default'''
        pass


class ABINIT(Scratch):
    '''Class that handles the submission of ABINIT files.
    It is a subclass of Submittable and overrides some methods.'''

    def __init__(self, host, filename, opts, subopts):
        '''Initiallizes the ABINIT submission class'''

        # Initiallize the parent
        Scratch.__init__(self, host, filename, opts, subopts)

        # Format the psuedopotential files
        if self.psp:
            for i in xrange(len(self.psp)):
                self.psp[i] = abs_file_path(self.psp[i])
        else:
            sys.exit('ABINIT requires psuedopotential files with --psp')

    def output_name(self):
        '''Creates the full output file name. Overrides the base
        class's method.'''
        return '.'.join([self.noext['full'], 'logfile'])

    def executable(self):
        '''The executable to use for interactive jobs.
        Overrides the base class'''
        return 'abinis' if 'hammer' in self.host.name else 'abinit'

    def copy_input(self, tmpdir):
        '''Copies input files to the temp directory.'''
        from glob import glob
        from shutil import copy
        from os.path import join, splitext

        # Construct a .files file
        self.files = '.'.join([self.noext['base'], 'files'])
        self.files = { 'full' : join(self.path, self.files),
                       'base' : self.files }
        with open(self.files['full'], 'w') as f:
            print(self.input['full'], file=f)
            print('.'.join([self.noext['base'], 'out']), file=f)
            print(splitext(self.input['base'])[0]+'i', file=f)
            print(self.noext['base']+'0', file=f)
            print('tmp', file=f)
            for p in self.psp:
                print(p, file=f)

        # Copy auxillary files
        for x in glob(splitext(self.input['full'])[0]+'i*'):
            x = x.strip()
            copy(x, tmpdir)

        # Copy the .files file
        copy(self.files['full'], join(tmpdir, self.files['base']))

    def stdstreams(self, **kwargs):
        '''Returns the proper standard in, out and error.'''
        from os.path import join
        try:
            tmpdir = kwargs['tmpdir']
        except KeyError:
            sys.exit('Missing key "tmpdir" from stdstreams')
        return (open(join(tmpdir, self.files['base'])),
                open(self.output['full'], 'w'),
                open('.'.join([self.noext['full'], 'err']), 'w'))

    def add_input(self, arguments):
        '''Appends the input files to the executable statement
        in the appropriate way.  This overrides the base class.'''
        return arguments + [self.executable()]

    def clean(self, **kwargs):
        '''Cleans up after a job.  Returns the sources and destinations
        of files to copy.'''
        from os.path import join
        from os import chdir
        from glob import glob
        import tarfile
        try:
            tmpdir = kwargs['tmpdir']
        except KeyError:
            sys.exit('Missing key "tmpdir" in clean')
        # Change to temp and tar all files together
        chdir(tmpdir)
        tarname = '.'.join([self.noext['base'], 'tar.gz'])
        tar = tarfile.open(tarname, 'w:gz')
        for f in glob(self.noext['base']+'o*'): tar.add(f)
        tar.close()
        # Go back to the input dir
        chdir(self.path)
        # Create a list of the sources and the dest files
        sources = [join(tmpdir, tarname),
                   join(tmpdir, '.'.join([self.noext['base'], 'out']))]
        dests   = [join(self.path, tarname),
                   '.'.join([self.noext['full'], 'out'])]
        return sources, dests

    def create_script(self, **kwargs):
        '''Write the ABINIT script to file.'''
        from os.path import splitext
        try:
            prog = 'mpirun abinip' if kwargs['pp'] > 1 else 'abinis'
        except KeyError:
            sys.exit('Missing key "pp" in create_script')
        return dedent('''\
          #PBS -e {noext}.err

          module load abinit

          cd $TMPDIR

          # Create the .files file
          touch {name}.files
          echo "{inp}"      >> {name}.files
          echo "{name}.out" >> {name}.files
          echo "{inpname}i" >> {name}.files
          echo "{name}o"    >> {name}.files
          echo "tmp"        >> {name}.files
          echo "{psp}"      >> {name}.files

          # Copy possible in files here
          if [ -e {inpnoext}i* ]; then
            cp {inpnoext}i* .
          fi

          {prog} < {name}.files > {out}
          tar -czf {name}.tar.gz {name}o*
          cp {name}.tar.gz {name}.out {name}.files {dir}\
          ''').format(name=self.noext['base'], out=self.output['full'],
                      inp=self.input['full'], noext=self.noext['full'],
                      psp='\n'.join(self.psp), dir=self.path, prog=prog,
                      inpname=splitext(self.input['base'])[0],
                      inpnoext=splitext(self.input['full'])[0])



class ADF(Scratch):
    '''Class that handles the submission of ADF files.
    It is a subclass of Submittable and overrides some methods.'''

    def __init__(self, host, filename, opts, subopts):
        '''Initiallizes the ADF submission class'''

        # Initiallize the parent
        Scratch.__init__(self, host, filename, opts, subopts)

        # Files to save
        self.save_files = {'logfile' : 'logfile', 'TAPE21'  : 't21',
                           'TAPE13'  : 't13',     'TAPE41'  : 't41',
                           'dftb.chk': 'chk',     'dftb.rkf': 'rkf',
                           'TAPE15'  : 't15',     'TAPE10'  : 't10',
                           'TAPE16'  : 't16'}

        # The raw logfile name
        self.rawlog = 'logfile'

        # Issue a simple warning for .inp files.
        if self.ext == 'inp':
            print('Warning: .inp extention for ADF is being '
                  'depreciated for .run.', file=sys.stderr)

    def edit_input(self):
        '''Examines the input file and checks if it needs to be edited.
        This overrides the base class's method.'''
        # Read in file as a single string
        fs = open(self.input['full']).read()

        rewrite = False
        # See if we need to replace references to gpfs with amp or vice versa
        if self.host.local and 'gpfs/work' in fs:
            fs = fs.replace('gpfs/work', 'amphome')
            rewrite = True
        elif not self.host.local and 'amphome' in fs:
            fs = fs.replace('amphome', 'gpfs/work')
            rewrite = True

        # Remove $SCM_OUTPUT as it is a relic of old
        if r'>>$SCM_OUTPUT' in fs:
            fs = fs.replace(r'>>$SCM_OUTPUT', '')
            rewrite = True
        elif r'>$SCM_OUTPUT' in fs:
            fs = fs.replace(r'>$SCM_OUTPUT', '')
            rewrite = True

        # Get rid of a pesky touch call in ReaxFF
        if 'touch "$SCM_LINK_SUMMARY_TXT"' in fs:
            s = 'touch "$SCM_LINK_SUMMARY_TXT"'
            n = s+' 2>/dev/null'
            # Don't change anything if we have already edited this
            if n in fs:
                pass
            else:
                fs = fs.replace(s, n)
                rewrite = True

        # Re-write to file if something changed
        if rewrite:
            with open(self.input['full'], 'w') as f:
                print(fs, file=f)

    def link_log(self, tmpdir):
        '''Makes a soft link to the logfile'''
        from subprocess import call
        logname = '.'.join([self.noext['base'], 'logfile'])
        call(['ln', '-sfT', os.path.join(tmpdir, self.rawlog),
                            os.path.join(self.path, logname)])

    def executable(self):
        '''The executable to use for interactive jobs.
        Overrides the base class'''
        try:
            return os.environ['ADFHOME']
        except KeyError:
            sys.exit('$ADFHOME environment variable is not defined!')

    def add_input(self,  arguments):
        '''Appends the input files to the executable statement
        in the appropriate way.  This overrides the base class.'''
        return arguments + ['bash', self.input['base']]

    def clean(self, **kwargs):
        '''Cleans up after a job.  Returns the sources and destinations
        of files to copy.'''
        from os.path import join, basename
        from glob import glob
        try:
            tmpdir = kwargs['tmpdir']
        except KeyError:
            sys.exit('Missing key "tmpdir" in clean')
        # Grab all files in the temp directory
        sources = glob(join(tmpdir, '*'))
        # Grab all cub files in temp directory
        sourcescub = glob(join(tmpdir,'*.cub'))
        # Filter only the files we want
        sources = [s for s in sources if basename(s) in self.save_files]

        # Add extention for dest based on name
        dests = ['.'.join([self.noext['full'], self.save_files[basename(s)]])
                                                              for s in sources]
       #for s in sourcescub:
       #    sources.append(s)
       #    dests.append('.'.join([self.noext['full'], basename(s)]))
        return sources, dests

    def redirect_output(self, inputfile):
        '''Defines how to edit the input file to best redirect output.'''
        # Redirect all output to the output file using the append operator
        from re import sub
        #inputfile = inputfile.replace('<<eor', '<<eor>>'+self.output['full'])
        inputfile = sub(r'<<\s?eor', '<<eor>>'+self.output['full'], inputfile)
        # Replace the first append with a create/overwrite and return.
        return inputfile.replace('<<eor>>', '<<eor>', 1)

    def create_script(self, **kwargs):
        '''Write the ADF script to file.'''
        from os import environ, getpid
        import random, string
        # NOTE: Deprecated  -- Gaohe 20241026
        # Use a default OPAL_PREFIX location if not in user's bashrc
        # try:
        #     OPAL_PREFIX = environ['OPAL_PREFIX']
        # except KeyError:
        #     OPAL_PREFIX = '/usr/global/openmpi/1.6.0/intel'
        # Make the string to clean up after the job is done
        template = '\nmv {0} {1}.{2} 2>/dev/null'
        cleanstr = '# Copy files'
        for raw, ext in self.save_files.items():
            cleanstr += template.format(raw, self.noext['full'], ext)
        cleanstr += '\ntar -czf {0}.tar.gz * 2>/dev/null'.format( self.noext['base'])
        cleanstr += '\nmv *.tar.gz {0} 2>/dev/null'.format(self.path)
        cleanstr += '\nrm -r $TMPDIR'

        # Edit the input file to redirect the output to the output file
        inp = self.redirect_output(open(self.input['full']).read())
        # NOTE: Comment or not for TCP workaround (leaving this in the code
        # if needed in the future).
        #comment = '' if self.host.name == 'lionxf.rcc.psu.edu' else '#'
        comment = '#'
        randomword = lambda length: ''.join(random.choice(string.ascii_lowercase) for _ in range(length))
        ranjobname = self.noext['base'][0:15] 
        randstring = randomword(4)
        ranjobname = ''.join([ranjobname, randstring])
        print (ranjobname)
        # TODO: Add a handle to automatic load ams. Configure related environmental varibels here
        # Gaohe 20241026
        return dedent('''\
    #module load ams
    # Set stuff for ADF
    cat $PBS_NODEFILE > {name}.nodefile
    cd {scratch}
    if [ ! -d "scratch_adf" ]; then
        mkdir scratch_adf
    fi
    mkdir scratch_adf/{ranjobname}
    cd scratch_adf/{ranjobname}
    export TMPDIR={temp}
    export SCM_RESULTDIR={dir}
    export SCM_TMPDIR=$TMPDIR
    export SCM_USETMPDIR=yes
    {comment}export MPI_REMSH=$ADFBIN/torque_ssh # For PlatformMPI
    {comment}export MPIRUN_OPTIONS=-TCP # Use when Infiniband is broken

    #export NSCM=$(wc -l < $PBS_NODEFILE)

    {input}

    {clean}\
    ''').format(name=self.noext['full'], dir=self.path, input=inp, comment=comment, clean="",
                base=self.noext['base'],ranjobname=ranjobname, scratch=self.host.scratch, temp=self.host.temp)


class BAND(ADF):
    '''Class that handles the submission of BAND files.
    It is a subclass of ADF and overrides some methods.'''

    def __init__(self, host, filename, opts, subopts):
        '''Initiallizes the BAND submission class'''

        # Initiallize the parent
        Scratch.__init__(self, host, filename, opts, subopts)

        # Files to save
        self.save_files = {'logfile': 'logfile', 'RUNKF': 'runkf'}

        # The raw logfile name
        self.rawlog = 'logfile'

        # Issue a simple warning for .inp files.
        if self.ext == 'inp':
            print('Warning: .inp extention for BAND is being '
                  'depreciated for .run.', file=sys.stderr)



class ReaxFF(ADF):
    '''Class that handles the submission of BAND files.
    It is a subclass of ADF and overrides some methods.'''

    def __init__(self, host, filename, opts, subopts):
        '''Initiallizes the BAND submission class'''

        # Initiallize the parent
        Scratch.__init__(self, host, filename, opts, subopts)

        # Files to save
        self.save_files = {'summary.txt' : 'logfile',
                           'xmolout'     : 'rxxmol',
                           'thermolog'   : 'rxthermo',
                           'energylog'   : 'rxenergy',
                           'molfra.out'  : 'rxmolfra',
                           'reaxout.kf'  : 'rxkf',
                          }

        # The raw logfile name
        self.rawlog = 'summary.txt'

        # Issue a simple warning for .inp files.
        if self.ext == 'inp':
            print('Warning: .inp extention for ReaxFF is being '
                  'depreciated for .run.', file=sys.stderr)

    def redirect_output(self, inputfile):
        '''Defines how to edit the input file to best redirect output.
        For ReaxFF we only do one redirection, which is different from ADF or
        BAND.'''
        # Redirect output from the executable to the output file.
        inputfile = inputfile.replace('"$ADFBIN/reaxff"',
                                      '"$ADFBIN/reaxff">'+self.output['full'])
        # Redirect the logfile to our result directory
        s = 'touch "$SCM_LINK_SUMMARY_TXT"'
        n = 'export SCM_LINK_SUMMARY_TXT="$SCM_RESULTDIR/{base}.logfile"; '
        return inputfile.replace(s, n.format(base=self.noext['base'])+s)



class NWChem(Scratch):
    '''Class that handles the submission of NWChem files.
    It is a subclass of Submittable and overrides some methods.'''

    def __init__(self, host, filename, opts, subopts):
        '''Initiallizes the NWChem submission class'''
        # Initiallize the parent
        Scratch.__init__(self, host, filename, opts, subopts)

    def executable(self):
        '''The executable to use for interactive jobs.
        Overrides the base class'''
        try:
            return os.environ['NWCHEM_TOP']
        except KeyError:
            sys.exit('$NWCHEM_TOP environment variable is not defined!')

    def add_input(self,  arguments):
        '''Appends the input files to the executable statement
        in the appropriate way.  This overrides the base class.'''
        if self.nodes:
            return arguments + ['mpirun', '-n', str(self.nodes), 'nwchem', self.input['base']]
        else:
            return arguments + ['nwchem', self.input['base']]

    def clean(self, **kwargs):
        '''Cleans up after a job.  Returns the sources and destinations
        of files to copy.'''
        from os.path import join, basename
        from os import chdir
        from glob import glob
        import tarfile
        try:
            tmpdir = kwargs['tmpdir']
        except KeyError:
            sys.exit('Missing key "tmpdir" in clean')
        # Change to temp and tar all files together
        chdir(tmpdir)
        tarname = '.'.join([self.noext['base'], 'tar.gz'])
        tar = tarfile.open(tarname, 'w:gz')
        for f in glob(join(tmpdir, '*')): tar.add(basename(f))
        tar.close()
        # Go back to the input dir
        chdir(self.path)
        # Create a list of the sources and the dest files
        sources = [join(tmpdir, tarname)]
        dests   = [join(self.path, tarname)]
        return sources, dests

    def create_script(self, **kwargs):
        '''Write the NWCHEM script to file.'''
        from os import environ
        # Define NWChem location.  Use an environment variable if possible.
        try:
            nw = environ['NWCHEM']
        except KeyError:
            nw = '/gpfs/group/jensen/nwchem-6.1.1/bin/LINUX64/nwchem'
            print("$NWCHEM environment variable not defined")
            print("Defaulting to {0}".format(nw))
        if self.host.queue == 'lxj18_collab':
            return dedent('''\
    #PBS -e {name}.logfile

    module purge
    module load intel/2015.0090 intel-mpi mkl/090-11.2-0

    cd /gpfs/scratch/$USER
    mkdir {jobname}
    export TMPDIR=gpfs/scratch/$USER/{jobname}

    cd $TMPDIR
    mpirun {nw} {inp} > {out}
    tar -czf {base}.tar.gz --exclude='*.tar.gz' $TMPDIR
    cp {base}.tar.gz {dir}\
    ''').format(name=self.noext['full'], inp=self.input['full'],
                base=self.noext['base'], out=self.output['full'],
                nw=nw, dir=self.path, user=environ['USER'],jobname = self.noext['base'][0:15])
        else:
            return dedent('''\
    #PBS -e {name}.logfile

    #module load openmpi/intel/1.7.3
    #module load intel mkl impi 

    cd $TMPDIR
    #mpirun {nw} {inp} > {out}
    srun {nw} {inp} > {out}
    tar -czf {base}.tar.gz --exclude='*.tar.gz' $TMPDIR
    cp {base}.tar.gz {dir}\
    ''').format(name=self.noext['full'], inp=self.input['full'],
                base=self.noext['base'], out=self.output['full'],
                nw=nw, dir=self.path, user=environ['USER'])



class Gaussian(Scratch):
    '''Class that handles the submission of Gaussian files.
    It is a subclass of Submittable and overrides some methods.'''

    def __init__(self, host, filename, opts, subopts):
        '''Initiallizes the Gaussian submission class'''
        # Initiallize the parent
        Scratch.__init__(self, host, filename, opts, subopts)

    def create_script(self, **kwargs):
        '''Write the Gaussian script to file.'''
        # Gaussian by default writes output to .log files.  We name the
        # files with error messages .errorfile to make this less annoying
        # if something goes wrong.
        return dedent('''\
          #PBS -e {name}.errorfile

          cd $PBS_O_WORKDIR

          module load gaussian/g09c01

          g09 {inp}
          ''').format(name=self.noext['base'], inp=self.input['base'])


class QChem(Scratch):
    '''Class that handles the submission of Q-Chem files.
    It is a subclass of Submittable and overrides some methods.'''

    def __init__(self, host, filename, opts, subopts):
        '''Initiallizes the Q-Chem submission class'''
        # Initiallize the parent
        Scratch.__init__(self, host, filename, opts, subopts)

    def create_script(self, **kwargs):
        '''Write the Q-Chem script to file.'''
        return dedent('''\
          #PBS -e {name}.logfile

          module load qchem/4.001

          cat  $PBS_NODEFILE
          set NN = `cat $PBS_NODEFILE | wc -l`
          setenv ONEEXE -DONEEXE

          cd $PBS_O_WORKDIR
          qchem -pbs -np $NN {inp} {out}

          # Remove the temporary file created after the job finishes
          rm TMP
          ''').format(name=self.noext['base'], inp=self.input['base'],
                      out=self.output['base'])


class Noscratch(Submittable):
    '''This provides the submit_interactive class for programs
    that take care of the scratch directory themselves.'''

    def __init__(self, host, filename, opts, subopts):
        '''Initiallizes the Nocratch class'''
        Submittable.__init__(self, host, filename, opts, subopts)

    def add_input(self, arguments):
        '''Adds the arguments to the executable in a way appropriate for this
        program.  Must be implemented in the subclass.'''
        pass

    def stdstreams(self, **kwargs):
        '''Returns the proper standard in, out and error.'''
        pass

    def submit_interactive(self):
        '''Submits a job interactively
        without an excplicit scratch directory'''
        from subprocess import call
        from os import devnull

        # Use nice to control the processor usage
        arguments = ['nice', '-n', str(self.nice), self.executable()]

        # Pass any sub arguments that were given
        if getattr(self, 'subopts', False): arguments += self.subopts

        # Add the input file name
        arguments = self.add_input(arguments)

        # Put job information into a files depending on the scenario
        logfile = '.'.join([self.noext['full'], 'logfile'])
        with open(devnull, 'w') as dev_null:
            # Set outputs for quiet runs
            stdin, stdout, stderr = self.stdstreams(log=logfile, dn=dev_null)

            # Run
            call(arguments, stderr=stderr, stdout=stdout)

            # Clean up
            self.clean(log=logfile, dn=dev_null)



class Dalton(Noscratch):
    '''Class that handles the submission of Dalton files.
    It is a subclass of Submittable and overrides some methods.'''

    def __init__(self, host, filename, opts, subopts):
        '''Initiallizes the Dalton submission class'''
        # Initiallize the parent
        Noscratch.__init__(self, host, filename, opts, subopts)

    def executable(self):
        '''The executable to use for interactive jobs.
        Overrides the base class'''
        from os.path import join
        from os import environ
        try:
            return join(environ['DALHOME'], 'bin', 'dalton')
        except KeyError:
            sys.exit('$DALHOME environment variable is not defined!')

    def add_input(self, arguments):
        '''Appends the input files to the executable statement
        in the appropriate way'''
        from os.path import relpath
        if relpath(self.path) == '.':
            inp = [self.input['base']]
        else:
            inp = ['-w', relpath(self.path), self.input['base']]
        if self.out:
            out = ['-o', self.output['base']]
        else:
            out = []
        return arguments + out + inp

    def stdstreams(self, **kwargs):
        '''Returns the proper standard in, out and error.'''
        try:
            dn = kwargs['dn']
        except KeyError:
            sys.exit('Missing key "dn" in stdstreams')
        if self.quiet:
            return None, dn, dn
        else:
            return None, sys.stdout, sys.stderr

    def create_script(self, **kwargs):
        '''Write the Dalton script to file.'''
        from os.path import join
        from os import environ
        # Make an explicit scratch directory
        scratch = join(self.host.scratch, self.noext['base'])
        # Define the restart section
        restart = restopt = ''
        # Define Dalton location.  Use environment variable if possible
        try:
            dal = environ['DALTON']
        except KeyError:
            dal = '/gpfs/group/jensen/dalton-2011/DALTON/bin/lionxg/dalton_mpi.x'
            print("$DALTON environment variable not defined")
            print("Defaulting to {0}".format(dal))

        # Define the MKL library for loading (deprectaed)
        #if self.host.name in ('lionxg.rcc.psu.edu',):
        #    try:
        #        mkl = environ['DALMKL']
        #    except KeyError:
        #        mkl = '10.3.12.361'
        #else:
        #    try:
        #        mkl = environ['DALMKL']
        #    except KeyError:
        #        mkl = '10.2.7.041'
        # It seems that Lion-XF and Lion-XG and very sensitive to the value
        # called 'WRKMEM' by Dalton.  Choosing large values always yields errors
        # that say the memory cannot be allocated.  Some testing has indicated that
        # setting workmem to half of the memory per processor will work on those
        # clusters.  Values are given to Dalton in megawords.
        if self.host.name in ('lionxg.rcc.psu.edu', 'lionxf.rcc.psu.edu',):
            wrkmem = self.mem * 128 * 1024
            wrkmem = int(wrkmem / 2)
        else:
            wrkmem = self.mem * 128000
        if self.restart:
            if '/' in self.restart:
                # If the restart file has a path associated with it, use that
                # rather than where the file was submitted from.  This will
                # probably only work with the absolute path.
                restart = dedent('''\
                  # Explicitly perform the -f flag (Dalton local submission)
                  tar -x SIRIUS.RST -vzf {rstfile}.tar.gz
                  tar -x RSPVEC -vzf {rstfile}.tar.gz
                  ''').format(scratch=scratch, rstfile=self.restart)
            else:
                # Restart file is in the same directory.
                restart = dedent('''\
                  # Explicitly perform the -f flag (Dalton local submission)
                  tar -x SIRIUS.RST -vzf {dir}/{rstfile}.tar.gz
                  tar -x RSPVEC -vzf {dir}/{rstfile}.tar.gz
                  ''').format(scratch=scratch, dir=self.path,
                              rstfile=self.restart)
            restopt = '-f {0}'.format(self.restart)
        # Restart directory.  This either assumes the file is named
        # identically to the filename being run, or that it is named
        # with "tpa_" as the first four characters.
        elif self.restartdir:
            if (self.restartdir[-1] == '/'):
                # Conditional statement is for files with "tpa_" in the name.
                # This currently assumes you are running the jobs using
                # the nmodes2numdiff type of naming.
                if "tpa_" in self.noext['base']:
                    self.restartdir = self.restartdir + self.noext['base'].replace("tpa_","")
                else:
                    self.restartdir = self.restartdir + self.noext['base']
            else:
                # Conditional statement is for files with "tpa_" in the name.
                # This currently assumes you are running the jobs using
                # the nmodes2numdiff type of naming.
                if "tpa_" in self.noext['base']:
                    self.restartdir = self.restartdir + '/' + self.noext['base'].replace("tpa_","")
                else:
                    self.restartdir = self.restartdir + '/' + self.noext['base']
            restart = dedent('''\
              # Explicitly perform the -f flag (Dalton local submission)
              tar -x SIRIUS.RST -vzf {rstfile}.tar.gz
              tar -x RSPVEC -vzf {rstfile}.tar.gz
              ''').format(scratch=scratch, rstfile=self.restartdir)
        else:
            restart, restopt = '', ''
        # Define files to grab
        files = ('SIRIUS.RST', 'SIRIFC',     'molden.inp', 'DALTON.ORB',
                 'DALTON.MOL', 'DALTON.ERR', 'DALTON.CM',  'DALTON.BAS',
                 'RSPVEC')
        return dedent('''\
          mkdir -p {scratch}

          module load openmpi/intel/1.6.0
          export WRKMEM={wrkmem:d}
          export NSCM={nscm:d}

          cp {inp} {scratch}/DALTON.INP
          cd {scratch}
          {restart}
          mpirun {dal} {restopt}
          cp {scratch}/DALTON.OUT {out}
          tar -C {scratch} -cvzf {name}.tar.gz {files}
          cp {scratch}/{name}.tar.gz {dir}
          cd {dir}
          rm -rf {scratch}\
          ''').format(scratch=scratch, inp=self.input['full'],
                      out=self.output['full'], dir=self.path, dal=dal,
                      wrkmem=wrkmem, nscm=8, name=self.noext['base'],
                      files=' '.join(files), restopt=restopt, restart=restart)



class POVRay(Noscratch):
    '''Class that handles the submission of POVRay files.
    It is a subclass of Submittable and overrides some methods.'''

    def __init__(self, host, filename, opts, subopts):
        '''Initiallizes the POVRay submission class'''

        # Initiallize the parent
        Noscratch.__init__(self, host, filename, opts, subopts)

        # Set the VMD option here
        if opts.vmd:
            h = int(opts.vmd * 800)
            w = int(opts.vmd * 800)
            self.subopts.extend(['+H{0}'.format(h), '+W{0}'.format(w)])

    def output_name(self):
        '''Creates the full output file name. Overrides the base
        class's method.'''
        return '.'.join([self.noext['full'], 'png'])

    def display_prog(self):
        '''The program to display the results of execution (for debugging).'''
        return 'display'

    def executable(self):
        '''The executable to use for interactive jobs.
        Overrides the base class'''
        from os.path import join
        return join('/usr/global/bin', 'povray')

    def stdstreams(self, **kwargs):
        '''Returns the proper standard in, out and error.'''
        try:
            log = kwargs['log']
        except KeyError:
            sys.exit('Missing key "log" in stdstreams')
        if self.quiet:
            return None, sys.stdout, open(log, 'w')
        else:
            return None, sys.stdout, sys.stderr

    def add_input(self, arguments):
        '''Appends the input files to the executable statement
        in the appropriate way'''
        if self.out:
            return arguments + [self.input['full'], '-O'+self.output['full']]
        else:
            return arguments + [self.input['full']]

    def clean(self, **kwargs):
        '''Cleans up after a POVRay job.  Converts logfile to unix format'''
        from subprocess import call
        for key in ('log', 'dn'):
            try:
                log = kwargs[key]
            except KeyError:
                sys.exit('Missing key "'+key+'" in clean')
        if self.quiet: call(['mac2unix', kwargs['log']], stderr=kwargs['dn'])
        return None, None

    def create_script(self, **kwargs):
        '''Write the POV-Ray script to file.'''
        from os import environ
        return dedent('''\
          #PBS -o {name}.logfile

          cd $TMPDIR

          {povray} +L{dir} +L{home}/.povray/3.6/include {opts} {inp} -O{outbase}

          # Move image from $TMPDIR to the correct folder'
          cp $TMPDIR/{outbase} {out}\
          ''').format(name=self.noext['full'], home=environ['HOME'],
                     dir=self.path, inp=self.input['full'],
                     opts=' '.join(self.subopts), out=self.output['full'],
                     povray='/usr/global/povray/3.6.1/bin/povray',
                     outbase=self.output['base'])


class DIM(Noscratch):
    '''Class that handles the submission of DIM files.
    It is a subclass of Submittable and overrides some methods.'''

    def __init__(self, host, filename, opts, subopts):
        '''Initiallizes the DIM submission class'''

        # Initiallize the parent
        Noscratch.__init__(self, host, filename, opts, subopts)

    def executable(self):
        '''The executable to use for interactive jobs.
        Overrides the base class'''
        from os.path import join
        from os import environ, pathsep, access
        for path in environ['DIMPATH'].split(pathsep):
            print(path)
            exe = join(path, 'dim.py')
            if access(exe, os.X_OK):
                return exe
        else:
            sys.exit('Could not find "dim" or "dim.py" in your PATH!')

    def add_input(self, arguments):
        '''Adds the input to the DIM executable'''
        if self.out and self.nodes:
            return arguments + [self.input['full'], '-o', self.output['full'],
                                '-n', str(self.nodes)]
        elif self.out:
            return arguments + [self.input['full'], '-o', self.output['full']]
        elif self.nodes:
            return arguments + [self.input['full'], '-n', str(self.nodes)]
        else:
            return arguments + [self.input['full']]

    def stdstreams(self, **kwargs):
        '''Returns the proper standard in, out and error.'''
        try:
            log = kwargs['log']
        except KeyError:
            sys.exit('Missing key "log" in stdstreams')
        if self.quiet:
            return None, open(log, 'w'), sys.stderr
        else:
            return None, sys.stdout, sys.stderr

    def create_script(self, **kwargs):
        '''Write the DIM script to file.'''
        from os import environ
        try:
            dim = environ['DIM']
        except KeyError:
            dim = '/gpfs/group/jensen/dim/dim.py'
            print("$DIM environment variable not defined")
            print("Defaulting to {0}".format(dim))
        if self.host.queue == 'lxj18_collab':
            return dedent('''\
    #PBS -e {name}.err

    module load python/2.7.9
    module load openmpi/1.8.4_A

    {dim} -n -1 {inp} -o{out} > {name}.logfile
    ''').format(name=self.noext['full'], inp=self.input['full'],
                out=self.output['full'], dim=dim)

        else:
            return dedent('''\
   #PBS -e {name}.err

    module purge
    module load intel
    module load mkl impi
    module load python/3.11.2

    export PBS_NODEFILE=$SLURM_JOB_NODELIST

    {dim} -n -1 {inp} -o{out} > {name}.logfile
    ''').format(name=self.noext['full'], inp=self.input['full'],
                out=self.output['full'], dim=dim)

class Host(object):
    '''A base class for a host system.'''

    def __init__(self, hostname):
        '''
        Initiallizes the host and defines its properties.
        Raises ann EnvironmentError if this is an undefined host.
        '''

        # Store name
        self.name = hostname
        self.shortname = self.name.split('.')[0]

    def verify_options(self, args):
        '''
        Check the optons given on the command line and make sure that
        they are valid.  Return the appropriate values based on the
        host type.
        '''
        from os.path import exists, isfile, getsize
        from os import access, R_OK

        # Set the defaults if requested, but don't override user choices
        if args.default and self.submit_type == 'queue':
            # First try and read defaults from a .submitrc
            self.import_defaults()
            # Now set defaults
            args.nodes = args.nodes if args.nodes else self.defaultnodes
            args.ppn   = args.ppn   if args.ppn   else self.defaultppn
            args.wall  = args.wall  if args.wall  else self.defaultwall
            args.mem   = args.mem   if args.mem   else self.defaultmem

        # Try to unpack all into nodes, ppn and wall
        try:
            args.nodes, args.ppn, args.wall, args.mem = args.all
        # If args.all is not defined, then each is defined separately
        except (TypeError, AttributeError):
            pass
        # Try to unpack exlusive  into nodes and wall
        try:
            args.nodes, args.wall = args.exclusive
            args.lexclusive = True
        # If args.exclusive is not defined, then each is defined separately
        except (TypeError, AttributeError):
            pass

        # ppn of -1 makes no sense with the exact option
        if args.exact and args.ppn == -1:
            sys.exit('--exact not valid with --ppn = -1')

        # Make sure the scratch directory is an absolute path
        self.scratch = abs_file_path(args.scratch)

        # Make path to file absolute, then make sure the file is submittable
        input_files = []
        for f in args.input_files:
            input_files.append(abs_file_path(f.strip()))
            l = input_files[-1]
            if not (exists(l) and isfile(l) and getsize(l) and access(l,R_OK)):
                # List limits if requested
                if f == 'list_limits':
                    self.list_limits()
                else:
                    print('File not suitable for submission:', l,
                          file=sys.stderr)

        # Some opts only work for one input file at a time
        if (args.restart or args.out) and len(input_files) > 1:
            sys.exit('--restart and --out are only valid for one '
                     'input file at a time.')

        # Check that the user didn't specify both restart flags.
        if (args.restart and args.restartdir):
            sys.exit('Either specify --restart or --restartdir, not '
                     'both.')

        return args, input_files

    def dhms2td(self, dhms):
        '''Return the number of seconds from a number in D:H:M:S format.'''
        from datetime import timedelta
        seconds = None
        if dhms[-1] == ':': dhms += '00' # i.e. convert 1:00: to 1:00:00
        nums = dhms.split(':')
        if [n for n in nums if n.isdigit()]:
            seconds = int(nums.pop()) # Last index is seconds.
            if nums: seconds += int(nums.pop()) * 60 # Next is minutes.
            if nums: seconds += int(nums.pop()) * 3600 # Next is hours.
            if nums: seconds += int(nums.pop()) * 86400 # Last is days.
        return timedelta(seconds=seconds)

    def td2hms(self, td):
        '''Return h:m:s format from a timedelta.'''
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds  = divmod(remainder, 60)
        hours += td.days * 24
        return '{0}:{1:02d}:{2:02d}'.format(hours, minutes, seconds)


class Interactive(Host):
    '''Class for hosts that offer interactive submissions.'''

    def __init__(self, hostname):
        '''Initiallizes the interactive class'''
        Host.__init__(self, hostname)

        # Set the submit type
        self.submit_type = 'interactive'

    def list_limits(self):
        '''List the host's limits and exit'''
        print(self.name, 'is an interactive host.  There are no limits.')
        sys.exit(0)


class Local(Interactive):
    '''Class for local hosts. A subclass of Interactive'''

    def __init__(self, hostname):
        '''Initiallize the local class'''
        Interactive.__init__(self, hostname)
        # Is local
        self.local = True
        # Set default scratch
        self.scratch = '/scratch'

class Queue(Host):
    '''Class for hosts that offer a batch queueing system'''

    def __init__(self, hostname):
        '''Initiallizes the queue class'''

        # Initiallize the host class
        Host.__init__(self, hostname)

        # Set the submit type and locality
        self.submit_type = 'queue'
        self.local = False
        self.queue_type  = None

        # Set default values for jobs.  May be overridden in subclass
        self.defaultnodes = 8
        self.defaultppn   = 1
        self.defaultwall  = '24:00:00'
        self.defaultmem   = 2000 # in MB

        # List of the max limits to set.  Used for defining in each subclass
        self.limit_names = ('maxnodes', 'maxppn',  'maxtotal',
                            'minnodes', 'maxwall', 'maxmem')

    def _set_limits(self, maxnodes, maxppn,  maxtotal,
                          minnodes, maxwall, maxmem):
        '''Sets the limits of this host.'''
        self.maxnodes = maxnodes
        self.maxppn   = maxppn
        self.maxtotal = maxtotal
        self.minnodes = minnodes
        self.maxwall  = maxwall
        self.maxmem   = maxmem

    def import_defaults(self):
        '''Try to read in defaults for this host
        from a .submitrc file in $HOME'''
        from os import environ
        from os.path import join
        from ConfigParser import RawConfigParser

        # Initiallize the parser with defaults
        defaults = RawConfigParser({'nodes' : self.defaultnodes,
                                    'ppn'   : self.defaultppn,
                                    'wall'  : self.defaultwall,
                                    'mem'   : self.defaultmem, })

        # Try to load the file.  If it fails do nothing
        try:
            rc = open(join(environ['HOME'], '.submitrc'))
        except IOError:
            pass
        # If it succeeds, see if this file has any defaults for this host
        else:
            defaults.readfp(rc)

            # If this section doesn't exist, quit
            if not defaults.has_section('lionxf'):
                return

            # Grab the data
            try:
                self.defaultnodes = defaults.getint(self.shortname, 'nodes')
            except ValueError:
                sys.exit('Invalid nodes in .submitrc')
            try:
                self.defaultppn = defaults.getint(self.shortname, 'ppn')
            except ValueError:
                sys.exit('Invalid ppn in .submitrc')
            try:
                self.defaultwall = self.dhms2td(defaults.get(self.shortname,
                                                             'wall'))
            except (TypeError, ValueError):
                sys.exit('Invalid wall in .submitrc')
            self.defaultwall = self.td2hms(self.defaultwall)
            try:
                self.defaultmem = defaults.getint(self.shortname, 'mem')
            except ValueError:
                sys.exit('Invalid mem in .submitrc')

    def list_limits(self):
        '''List the host's limits and exit'''
        print('Host name                     :', self.name)
        print('Max # nodes                   :', self.maxnodes)
        print('Min # nodes                   :', self.minnodes)
        print('Max # processors per node     :', self.maxppn)
        print('Max # total processors        :', self.maxtotal)
        print('Max memory per node           :', self.maxmem / 1000, 'GB')
        print('Max wall time                 :', self.td2hms(self.maxwall))
        print()
        print('Default # Nodes               :', self.defaultnodes)
        print('Default # processors per node :', self.defaultppn)
        print('Default memory per processor  :', self.defaultmem / 1000, 'GB')
        #print('Default wall time             :', self.td2hms(self.defaultwall))
        print('Default wall time             :', self.defaultwall)
        sys.exit(0)

    def type_check(self, nodes, ppn, wall, mem):
        '''Checks the type of the job parameter options.'''
        try:
            nodes = int(nodes)
        except ValueError:
            exit('Nodes must be an integer')
        try:
            ppn = int(ppn)
        except ValueError:
            exit('PPN must be an integer')
        # Convert wall time into a timedelta object for easier comparisons
        try:
            wall = self.dhms2td(wall)
        except (TypeError, ValueError):
            from datetime import timedelta
            if not isinstance(wall, timedelta):
                exit('The wall value {0} is not valid.'.format(wall))
        try:
            mem = int(mem)
        except ValueError:
            exit('Memory must be an integer')

        return nodes, ppn, wall, mem

    def check_limits(self, nodes, ppn, wall, mem):
        '''Checks that the value of a given parameter is within the limits'''
        from sys import exit as x

        w = 'Max wall time on {0} is {1}'
        # Check node and ppn limits
        self.check_node_ppn_mem_limits(nodes, ppn, mem)
        # Max wall time
        if wall > self.maxwall:
            x(w.format(self.name, self.td2hms(self.maxwall)))

    def check_node_ppn_mem_limits(self, nodes, ppn, mem):
        '''Checks the node and ppn limits that are given.
        May be overridden by the subclass.'''
        from sys import exit as x
        s = 'Max {0} on {1} is {2:d}'
        m = 'Min {0} on {1} is {2:d}'
        a = 'Max memory per node on {0} is {1}'
        # Make sure PPN makes physical sense
        if ppn < 1: x('PPN must be greater than 0')
        # Max nodes
        if nodes > self.maxnodes:
            x(s.format('nodes', self.name, self.maxnodes))
        # Max PPN
        if ppn > self.maxppn:
            x(s.format('PPN', self.name, self.maxppn))
        # Max total processors
        if nodes * ppn > self.maxtotal:
            x(s.format('total processors', self.name, self.maxtotal))
        # Min number of nodes
        if nodes < self.minnodes:
            x(m.format('nodes', self.name, self.minnodes))
        # Max memory per node
        if mem is not None and ( ppn * mem ) > self.maxmem:
            x(a.format(self.name, self.maxmem))


class Stampede(Queue):
    '''Class for the TACC Stampede cluster.  A subclass of Queue'''

    def __init(self, hostname):
        '''Initializes the Stampede class'''
        # Initialize the Host class
        Queue.__init__(self, hostname)
        # Default scratch directory
        self.scratch = os.getenv('SCRATCH')
        # Set the queue name for this host
        self.queue = 'normal'
        # maxnodes, maxppn, maxtotal, minnodes, maxwall, maxmem (in MB)
        self._set_limits(256, 16, 4096, 1, self.dhms2td('48:00:00'), 32000)
        # Change the default ppn.  This will always be 16.
        self.defaultppn = 16

        self.queue_type = 'PBS'

# jbb5516 Adding ACIb functionality. will remove comment when debugged
class ACIb(Queue):
    '''Class for the ACIb cluster. A subclass of Queue'''

    def __init__(self, hostname):
        '''Initializes the ACIb class'''
        # Initialize the Host class
        Queue.__init__(self, hostname)
        # Default scratch directory
        self.scratch = os.path.join('/gpfs/scratch/', os.getenv('USER'))
        self.temp = os.path.join('/tmp/')
        # Set queue name for this host
	# does not work the same on ACIb
        self.queue = 'lxj18_collab'
        # maxnodes, maxppn, maxtotal, minnodes, maxwall, maxmem (in MB)
        # these are just temp limits. should change if we buy in
        self._set_limits(253, 20, 160, 1, self.dhms2td('192:00:00'), 256000)
        # Change the default ppn
        self.defaultppn = -1

        self.queue_type = 'PBS'

    def check_node_ppn_mem_limits(self, nodes, ppn, mem):
        '''Checks the node and ppn limits that are given.
        This overrides the subclass's definition.'''
        from sys import exit as x
        s = 'Max {0} on {1} is {2:d}'
        m = 'Min {0} on {1} is {2:d}'
        # If PPN = -1 then nodes is actually the total processors
        if ppn == -1:
            # Max nodes
            if nodes > self.maxtotal:
                x(s.format('total processors', self.name, self.maxtotal))
                # Min number of nodes
            if nodes < self.minnodes:
                x(m.format('total processors', self.name, self.minnodes))
            # It's difficult to process memory without ppn, so we won't
        else:
            # Use the default checker
            Queue.check_node_ppn_mem_limits(self, nodes, ppn, mem)

class Hpc(Queue):
    '''Class for the HPC cluster. A subclass of Queue'''

    def __init__(self, hostname):
        '''Initializes the Hpc class'''
        # Initialize the Host class
        Queue.__init__(self, hostname)
        # Default scratch directory
        self.scratch = os.path.join('/scratch/', os.getenv('USER'))
        self.temp = os.path.join('/tmp/')
        # Set queue name for this host
	# does not work the same on ACIb
        self.queue = 'lxj18_collab'
        # maxnodes, maxppn, maxtotal, minnodes, maxwall, maxmem (in MB)
        # these are just temp limits. should change if we buy in
        self._set_limits(253, 48, 160, 1, self.dhms2td('192:00:00'), 256000)
        # Change the default ppn
        self.defaultppn = -1

        self.queue_type = 'SBATCH'

    def check_node_ppn_mem_limits(self, nodes, ppn, mem):
        '''Checks the node and ppn limits that are given.
        This overrides the subclass's definition.'''
        from sys import exit as x
        s = 'Max {0} on {1} is {2:d}'
        m = 'Min {0} on {1} is {2:d}'
        # If PPN = -1 then nodes is actually the total processors
        if ppn == -1:
            # Max nodes
            if nodes > self.maxtotal:
                x(s.format('total processors', self.name, self.maxtotal))
            # Min number of nodes
            if nodes < self.minnodes:
                x(m.format('total processors', self.name, self.minnodes))
            # It's difficult to process memory without ppn, so we won't
        else:
            # Use the default checker
            Queue.check_node_ppn_mem_limits(self, nodes, ppn, mem)
 


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
