import numpy as np
import math
from math import pi
from decimal import *
from numpy.linalg import norm
from cmath import polar
import _pickle as cPickle
import argparse


def main():
    
    parser = argparse.ArgumentParser(description="Creates rotation matrix")

    parser.add_argument("--xyz", metavar="xyz", type=str, 
            help="xyz file")

    parser.add_argument("--rotmat", metavar="rotmat", type=str,
            help="A rotation matrix provided by the user to be used to produce a rotated xyz file called tmp.xyz")

    parser.add_argument("--line", metavar=("atom1","atom2"), nargs=2, type=int, 
            help="Indices of 2 atoms that define a line you intend to align with the direction.")

    parser.add_argument("--plane", metavar=("atom1","atom2","atom3"), nargs=3, type=int,
            help="Indices of 3 atoms that define a plane whose normal vector aligns with the direction")

    parser.add_argument("--direction", metavar="direction", type=str,
            help="Axis to align with: input MUST be x, y, or z")


    args = parser.parse_args()



    atomnote, coord = coordfromxyz(args.xyz)

    if args.direction == None and args.rotmat == None:
        print("You did not specify a direction.")
    elif args.direction == 'x' and args.rotmat == None:
        dirVec = [1, 0, 0]
    elif args.direction == 'y' and args.rotmat == None:
        dirVec = [0, 1, 0]
    elif args.direction == 'z' and args.rotmat == None:
        dirVec = [0, 0, 1]
    else:
        print("You specified something other than x, y, or z.")


    if args.rotmat != None:
        print("You are providing your own rotation matrix...scary.")
        U=readRotmat(args.rotmat)
        num = coord.shape[0]
        for i in range(num):
            coord[i] = np.matmul(U, coord[i])
        printcoord('tmp.xyz', atomnote, coord)

    
    if args.line != None and args.plane == None and args.rotmat == None:
        U=align_line(coord, args.line[0], args.line[1], dirVec)
        print(U)
        num = coord.shape[0]
        for i in range(num):
            coord[i] = np.matmul(U, coord[i])
        printcoord('tmp.xyz', atomnote, coord)
    
    if args.plane != None and args.line == None and args.rotmat == None:
        U=align_plane(coord, args.plane[0], args.plane[1], args.plane[2], dirVec)
        print(U)
        num = coord.shape[0]
        for i in range(num):
            coord[i] = np.matmul(U, coord[i])
        printcoord('tmp.xyz', atomnote, coord)


    #align_line(coord, 3, 2, [0, 0, 1])
    #U = align_plane(coord, 49, 31, 6, [0, 0, 1])
#    print(U)
    
#    num = coord.shape[0]
#    for i in range(num):
#        coord[i] = np.matmul(U, coord[i])

#    printcoord('tmp.xyz', atomnote, coord)


def calc_rotmatrix(A, B): 
## calc the rotation matrix which aligns two vectors A and B parallel 
  A = A / np.linalg.norm(A)
  B = B / np.linalg.norm(B)
  
  tmpcos = np.dot(A, B)
  tmpsin = np.linalg.norm(np.cross(A, B) )
  G = np.zeros((3, 3))
  G[0][0] = tmpcos
  G[0][1] = -1 * tmpsin
  G[1][0] = tmpsin
  G[1][1] = tmpcos
  G[2][2] = 1.0
  u = A.copy()
  if np.linalg.norm(B-tmpcos*A ) == 0.0:
    v = np.array([0, 0, 0])
  else:
    v = (B - tmpcos*A) / (np.linalg.norm(B-tmpcos*A ))
  w = np.cross(B, A)  
  F_inv = np.zeros((3, 3))
  for i in range(3):
    F_inv[i][0] = u[i]
  
  for i in range(3):
    F_inv[i][1] = v[i]
  
  for i in range(3):
    F_inv[i][2] = w[i]
  
  F = np.linalg.inv(F_inv)
  U = np.matmul(F_inv , np.matmul(G, F))

  return U


def align_plane(coord, p1, p2, p3, direction): 
## p1 p2 p3 are indices of atoms in a plane
## direction can be x [1, 0, 0] for example which is normal to the atomic plane
## origin is the index of the atom which is selected to be at origin
  vec1 = coord[p2 -1] - coord[p1 - 1] 
  vec2 = coord[p3 -1] - coord[p1 - 1] 
  A = np.cross(vec1, vec2)
  B = np.array(direction)
  U = calc_rotmatrix(A, B)
  return U
#  num = coord.shape[0]
#  for i in range(num):
#    coord[i] = np.matmul(U, coord[i])


def align_line(coord, v1, v2, direction): ## extra varable: normalmode

  A1 = coord[v2-1] - coord[v1-1]
  B1 = np.array(direction)

  U1 = calc_rotmatrix(A1, B1)
  return U1
#  num = coord.shape[0]
#  for i in range(num):
#    coord[i] = np.matmul(U1, coord[i])
##  normalmode[i] = np.matmul(U1, normalmode[i])


def readRotmat(rotmat):
  opener = open(rotmat)
  data = opener.readlines()
  opener.close()
  U = np.zeros((3,3))
  for i in range(3):
    for j in range(3):
      U[i][j] = float(data[i].strip('\n').split()[j])
  return U



def coordfromxyz(filename):
  f = open(filename)
  f1 = f.readlines()
  f.close()
  num = int(f1[0].strip('\n'))
  coord = np.zeros((num, 3))
  atomnote = []
  for i in range(num):
    atomnote.append(f1[i+2].strip('\n').split()[0])
    coord[i][0] = float(f1[i+2].strip('\n').split()[1])
    coord[i][1] = float(f1[i+2].strip('\n').split()[2])
    coord[i][2] = float(f1[i+2].strip('\n').split()[3])
  return atomnote, coord


def printcoord(xyzname, atomnote, coord):
  num = len(atomnote)
  g = open(xyzname, 'w')
  g.write(str(num)+'\n')
  g.write('\n')
  for i in range(num):
    g.write('{0:}        {1: .8f}        {2: .8f}        {3: .8f}\n'.format(atomnote[i], coord[i][0], coord[i][1], coord[i][2]))
  g.close()


## an example for how to use the script to calculate the rotation matrix externally (wrt to plotraman function in the chemPackage)



if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
