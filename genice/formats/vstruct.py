# coding: utf-8
"""
Gro file format

V-structure (time average)
It works for water molecules only.
And it is for analice with loadmulti feature.

defined in http://manual.gromacs.org/current/online/gro.html
"""
import numpy as np
import genice.cells
from genice import rigid

N=25
rots = []
positions = []
drots = []
dpositions = []
cells = []

def hook5(lattice):
    global cells
    lattice.logger.info("Hook5: Store positions and orientations.")
    # cell
    mat = lattice.repcell.mat
    cells.append(mat.copy())
    # translation
    pos = lattice.reppositions
    if len(positions) > 0:
        dpositions.append(genice.cells.rel_wrap(pos - positions[-1]))
    positions.append(pos.copy())
    # rotation
    if len(rots) > 0:
        d = np.zeros_like(lattice.rotmatrices)
        for i, rot in enumerate(lattice.rotmatrices):
            d[i] = np.dot(rots[-1][i].transpose(), rot)
        drots.append(d)
    rots.append(lattice.rotmatrices.copy())
    # override with averaged values
    H = len(rots) // 2
    # cell
    avgcell = np.average(np.array(cells), axis=0)
    lattice.repcell = genice.cells.Cell(avgcell, "triclinic")
    lattice.logger.info(avgcell)
    # position
    delta = np.sum(np.array(dpositions), axis=0)
    lattice.reppositions = positions[0] + delta / 2
    # rotation
    if len(drots) == 0:
        rot = None
    elif len(drots) == 1:
        for i in range(len(lattice.rotmatrices)):
            q = rigid.rotmat2quat(drots[0][i,:,:])
            q = rigid.qmul(q, 0.5)
            lattice.rotmatrices[i] = np.dot(rots[0][i], rigid.quat2rotmat(q))
    else:
        D = np.array(drots)
        for i in range(len(lattice.rotmatrices)):
            rot = np.linalg.multi_dot(D[:,i,:,:])
            q = rigid.rotmat2quat(rot)
            q = rigid.qmul(q, 0.5)
            lattice.rotmatrices[i] = np.dot(rots[0][i], rigid.quat2rotmat(q))
    if len(rots) == N:
        rots.pop(0)
        drots.pop(0)
        positions.pop(0)
        dpositions.pop(0)
        cells.pop(0)
    lattice.logger.info("Queue size: {0}".format(len(rots)))
    lattice.logger.info("Hook5: end.")



def hook6(lattice):
    lattice.logger.info("Hook6: Output waters in Gromacs format.")
    lattice.logger.info("  Total number of atoms: {0}".format(len(lattice.atoms)))
    if len(lattice.atoms) > 99999:
        lattice.logger.warn("  Gromacs fixed format cannot deal with atoms more than 99999. Residue number and atom number are faked.")
    cellmat = lattice.repcell.mat
    s = ""
    s += "Generated by GenIce https://github.com/vitroid/GenIce \n"
    s += "{0}\n".format(len(lattice.atoms))
    molorder = 0
    for i, atom in enumerate(lattice.atoms):
        resno, resname, atomname, position, order = atom
        if resno == 0:
            molorder += 1
        if len(lattice.atoms) > 99999:
            s += "{0:5d}{1:5s}{2:>5s}{3:5d}{4:8.3f}{5:8.3f}{6:8.3f}\n".format(9999,resname, atomname, 9999,position[0],position[1],position[2])
        else:
            s += "{0:5d}{1:5s}{2:>5s}{3:5d}{4:8.3f}{5:8.3f}{6:8.3f}\n".format(molorder,resname, atomname, i+1,position[0],position[1],position[2])
    if cellmat[1,0] == 0 and cellmat[2,0] == 0 and cellmat[2,1] == 0:
        s += "    {0} {1} {2}\n".format(cellmat[0,0],cellmat[1,1],cellmat[2,2])
    else:
        assert cellmat[0,1] == 0 and cellmat[0,2] == 0 and cellmat[1,2] == 0
        s += "    {0} {1} {2} {3} {4} {5} {6} {7} {8}\n".format(cellmat[0,0],
                                                                cellmat[1,1],
                                                                cellmat[2,2],
                                                                cellmat[0,1],
                                                                cellmat[0,2],
                                                                cellmat[1,0],
                                                                cellmat[1,2],
                                                                cellmat[2,0],
                                                                cellmat[2,1],
                                                                )
    s += '#' + "\n#".join(lattice.doc) + "\n"
    print(s,end="")
    lattice.logger.info("Hook6: end.")


hooks = {5:hook5, 6:hook6}
