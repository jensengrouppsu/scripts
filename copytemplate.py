#! /usr/bin/env python

from __future__ import print_function, division
from chemPackage import collect
import sys, os

def main():
    """\
    This program takes the coordinates from a given file and places it
    into a given template file.
    
    See man page for more info.
    """

    from argparse import ArgumentParser, RawDescriptionHelpFormatter
    from textwrap import dedent
    parser = ArgumentParser(description=dedent(main.__doc__),
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('--version', action='version', version='%(prog)s 1.1')
    parser.add_argument('-t', '--template', help='The template input file(s)',
                        nargs='+', required=True)
    parser.add_argument('-c', '--coordfiles', help='The files containing the '
                        'requested coordinates.', nargs='+', required=True)
    parser.add_argument('-o', '--output', help='The output filename(s).',
                        nargs='+')
    parser.add_argument('-q', '--qmcharge', help='The QM system total charge',
                        nargs='+', default=None)
    parser.add_argument('-a', '--atombasis', help='The basis set for each '
                        'atom in the system, entered in \'atom basis\' format.', 
                        nargs='+', default=None)
    parser.add_argument('--ignore_errors', help='Ignores collection errors',
                        action='store_true', default=False)
    args = parser.parse_args()

    # Make sure that the sizes of the arrays match up.
    if (len(args.coordfiles) != len(args.template) and
        len(args.coordfiles) != 1 and len(args.template) != 1):
        sys.exit('Number of template and coordinate files must be equal '
                 'or one may be equal to one')

    # If the lengths are not equal, fill so that they are equal
    if len(args.coordfiles) != len(args.template):
        if len(args.coordfiles) == 1:
            for i in xrange(1, len(args.template), 1):
                args.coordfiles.append(args.coordfiles[0])
        else:
            for i in xrange(1, len(args.coordfiles), 1):
                args.template.append(args.template[0])

    # The QM charge is needed for Dalton.  We default to 0.0 if no
    # charge is given.
    if args.qmcharge == None:
        args.qmcharge = []
        for i in range(len(args.coordfiles)):
            args.qmcharge.append('0.0')
    elif len(args.qmcharge) != len(args.coordfiles):
        if len(args.qmcharge) == 1:
            for i in xrange(1, len(args.coordfiles), 1):
                args.qmcharge.append(args.qmcharge[0])

    # Convert the atom basis (for Dalton) to a dictionary and store the
    # information as a list of dictionaries for compatability purposes.  
    # It is assumed that all files will use the same basis set information.
    if args.atombasis == None:
        args.atombasis = []
        for i in range(len(args.coordfiles)):
            args.atombasis.append(None)
    elif args.atombasis != None:
        atombasis = {}
        for elem in range(len(args.atombasis)):
            temp = args.atombasis[elem].split()
            atombasis[temp[0]] = temp[1]
        args.atombasis = []
        args.atombasis.append(atombasis)
        if len(args.atombasis) != len(args.coordfiles):
            for i in xrange(1, len(args.coordfiles), 1):
                args.atombasis.append(args.atombasis[0])

    # Now make sure that the number of output files matches, if given
    if args.output:
        if len(args.output) != len(args.template):
            sys.exit('Number of output files must equal other files')
    else:
        args.output = []
        for i in range(len(args.template)):
            args.output.append(sys.stdout)

    # Finaly, we actually make the templates
    for coord, temp, out, qmcharge, atombasis in zip(args.coordfiles, args.template, args.output, args.qmcharge, args.atombasis):

        # Load the coordinates
        if args.ignore_errors:
            c = collect(coord, raise_err=False)
        else:
            c = collect(coord)

        # Make the new file based on the template.
        c.copy_template(template=temp, file=out, charge=qmcharge, basis=atombasis)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
