#!/usr/bin/env python3


import argparse
import os
import sys
from chemPackage.coords import Coordinates
from chemPackage import collect

def main():
    parser = argparse.ArgumentParser(description='Convert vibrational '
                                     'modes from an AMS frequency output '
                                     'file into PyMOL mode files.')
    parser.add_argument('freq_file', help='AMS frequency output file '
                        '(e.g. freq_mcyclic_nhc_au_iso.out)')
    parser.add_argument('-c', '--color', default='green', help='Color for '
                        'the vibrational modes (default: green)')
    parser.add_argument('--low', help='The low mode to include. The '
                        'default is %(default)s cm-1.', default=200,
                        type=float)
    parser.add_argument('--high', help='The high mode to include. The '
                        'default is %(default)s cm-1.', default=6000,
                        type=float)
    args = parser.parse_args()

    if not os.path.isfile(args.freq_file):
        print(f"Error: file not found: {args.freq_file}", file=sys.stderr)
        sys.exit(1)

    try:
        source = collect(args.freq_file)
        source.modes_to_pymol(freqmin=args.low, freqmax=args.high, color=args.color)
    except Exception as e:
        print(f"Error processing {args.freq_file}: {e}", file=sys.stderr)
        sys.exit(1)

    print("Done! PyMOL mode files have been generated.")


if __name__ == "__main__":
    main()

