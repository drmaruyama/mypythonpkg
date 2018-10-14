import sys
import math
import numpy as np
import pickle
import statsmodels.api as sm
import cupy as cp
import tqdm
import time


#
# Calculate rho(k,q,t), <rho(k,q)>, and <drho(k,q,t)drho(-k,-q,0)> from compickle.
# This script requires cupy(https://github.com/cupy/cupy) 
# and statsmodels(https://github.com/statsmodels/statsmodels).
# Install cupy using "conda install cupy".
# Install statsmodels using "using install statsmodels".
#

# Sample:
# python script/calc_rhokq.py MD/sample0001_01.pickle 1 5 0 5
#

args = sys.argv
fname = args[1]
T = float(fname.split('_')[1].split('.')[0])
nens = fname.split('_')[0][-4:]
dirname = fname.split('/')[0]
sysname = fname.split('/')[1].split('_')[0]
nk_min = int(args[2])
nk_max = int(args[3])
nq_min = int(args[4])
nq_max = int(args[5])

pi = math.pi

t = time.time()
with open(fname, mode='rb') as f:
    d = pickle.load(f)

tN = len(d['x'])
R = d['x']
V = d['v']
box_size = d['L']
R = np.around(R,decimals=3)
V = np.around(V,decimals=3)

R = cp.asarray(R)
V = cp.asarray(V)

print(tN, box_size)
print('load picklefile time:', time.time() - t)


# Phisical Parameters
N =  len(R[0])
dt = 1.0e0 #(ps)
L = box_size #(nm) 
mO = 16.00e-27 #(kg)
mH =  1.008e-27 #(kg)
Minv = 1/(mO + mH + mH) #(kg^-1)
kB = 1.3801e-23 #(J K^-1)

# Wave number Parameters
k0 = 2.0e0*pi / L # (nm^-1)
dk = 1.0e0*2.0e0*pi / L # (nm^-1)
vth = math.sqrt(3.0e0*kB*T*Minv) /1000.0e0 # (nm/fs)^-1 = (km/s)^-1
alpha = 0.0250
dq = alpha * 2.0e0*pi / vth
q0 = 0.0e0
qN = nq_max - nq_min + 1
kN = nk_max - nk_min + 1

t0 = time.time()

K = np.array([1/math.sqrt(3.0e0) * np.array([k0+i*dk, k0+i*dk, k0+i*dk]) for i in range(nk_min, nk_max+1)])
Q = np.array([1/math.sqrt(3.0e0) * np.array([q0+i*dq, q0+i*dq, q0+i*dq]) for i in range(nq_min, nq_max+1)])
K = np.around(K, decimals=3)
Q = np.around(Q, decimals=3)
K = cp.asarray(K)
Q = cp.asarray(Q)

t1 = time.time()
bnum = 500
tN_b = int(tN/bnum)
rho = np.array([[[(0.0e0+0.0e0j) for i in range(tN_b)]  for q in Q] for k in K])
rho = cp.asarray(rho)
print('rho:')
print(rho.shape)

# Calculate rho(k,q,t)
for ib,it in enumerate(range(tN_b)):
    for ik,k in enumerate(K):
        for iq,q in enumerate(Q):
            print('(it,ik,iq)=({0:d},{1:d},{2:d})'.format(it,ik,iq))
            r = R[ib*bnum:(ib+1)*bnum]
            v = V[ib*bnum:(ib+1)*bnum]
            theta = cp.dot(r,k) + cp.dot(v,q)
            dummy01 = cp.exp(theta*-1.0e0j)
            rho[ik][iq][ib] = cp.sum(dummy01)/float(bnum)
            print('rho[ik][iq]:')
            print(rho[ik][iq][ib])
print("Calculate rho(k,q,t) time:", time.time()-t1)

# Calculate <rho(k,q)>
rho_t = np.array([[(0.0e0+1.0e0j) for q in Q] for k in K])
for ik,k in enumerate(K):
    for iq,q in enumerate(Q):
        rho_t[ik][iq] = np.sum(rho[ik][iq], axis=0) / float(tN_b)

rho_t = cp.asnumpy(rho_t)
t3 = time.time()
for ik,nk in enumerate(range(nk_min, nk_max+1)):
    ofname = 'DAT/rho'+nens+'nk{0:02d}_{1:d}.dat'.format(nk,int(T))
    with open(ofname, 'wt') as f:
        f.write('# k=[{0[0]},{0[1]},{0[2]}]\n# rho(k,q,t)\n'.format(K[ik]))
    for iq,q in enumerate(Q):
        print(q)
        a = rho_t[ik][iq].real/rho_t[ik][0].real
        b = rho_t[ik][iq].imag/rho_t[ik][0].imag
        with open(ofname, 'a+') as f:
            f.write('{0}\t{1}\t{2}\n'.format(q[0], a, b))

print("write file time:", time.time()-t3)
print("total time:", time.time()-t0)
