#!/usr/bin/env python

from __future__ import print_function, division
import sys, os
from chemPackage import collect

def main():
    """\
    A method to quickly extract the coordinates from a file and write to
    an xyz file.  The new file will have the same name as the input with
    the extention .xyz.  By default, only the QM portion of the coordinates
    is extracted, but this can be changed.
    """

    from argparse import ArgumentParser, RawDescriptionHelpFormatter
    from textwrap import dedent
    parser = ArgumentParser(description=dedent(main.__doc__),
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('files', nargs='+', help='The files containing the '
                        'coordinates to extract.')
    parser.add_argument('--atoms', '-a', help='The range of atoms to print. '
                        'The default is all atoms.  Note: if you are choosing '
                        '--DIMQM, then the atoms are grouped together, so '
                        'this should be taken into account when choosing '
                        'atoms.', nargs=2, type=int, default=[1, None],
                        metavar=('A1', 'A2'))
    parser.add_argument('--center', '-c', help='Center the moleucule on the '
                        'origin', action='store_true', default=False)
    parser.add_argument('--dim', '--DIM', help='Only include DIM component.',
                        action='store_const', const='DIM', dest='mode',
                        default='QM')
    parser.add_argument('--dimqm', '--DIMQM', help='Include both QM and DIM '
                        'component.', action='store_const', const='DIMQM',
                        dest='mode', default='QM')
    parser.add_argument('--ignore_errors', help='Ignores collection errors',
                        action='store_true', default=False)
    args = parser.parse_args()

    # Make a dict to pass as the keyword args
    if args.mode == 'DIMQM':
        kwargs = { 'qm': True, 'dim': True }
    elif args.mode == 'DIM':
        kwargs = { 'qm': False, 'dim': True }
    else:
        kwargs = { 'qm': True, 'dim': False }
    # Now add in the atom range
    kwargs['a1'] = args.atoms[0]
    kwargs['a2'] = args.atoms[1]

    # Perform a writeCoords on each file
    for f in args.files:
        try:
            if args.ignore_errors:
                coords = collect(f, raise_err=False)
            else:
                coords = collect(f)
        except IOError:
            print('File', f, 'does not exist.  Skipping...', file=sys.stderr)
        # Center if requested
        if args.center: coords.shift_to_origin()
        # Write coordinates
        try:
            coords.writeCoords(**kwargs)
        except AssertionError as a:
            print(f+':', a, 'Skipping...', file=sys.stderr)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
