import sys
sys.path.append('../')
from s_xbyak import *
import argparse

def assertEq(x, y):
  if x != y:
    raise Exception('not equal', x, y)

def maskTest():
  # for nasm/masm
  assertEq(str(rax), 'rax')
  assertEq(str(al), 'al')
  assertEq(str(ecx+eax*4+123), 'ecx+eax*4+123')
  assertEq(str(ecx+eax*8-123), 'ecx+eax*8-123')
  assertEq(str(ecx), 'ecx')
  assertEq(str(xmm1), 'xmm1')
  assertEq(str(ymm2), 'ymm2')
  assertEq(str(zmm3), 'zmm3')
  assertEq(str(xmm1|k2), 'xmm1{k2}')
  assertEq(str(xmm1|k0), 'xmm1')
  assertEq(str(k1|k2), 'k1{k2}')
  assertEq(str(k2|k1), 'k2{k1}')
  assertEq(str(k1|T_z), 'k1{z}')
  assertEq(str(k2|k1|T_z), 'k2{k1}{z}')
  assertEq(str(xmm1|k2|T_z), 'xmm1{k2}{z}')

SIMD_BYTE=64
def Unroll(n, op, *args, addrOffset=None):
  xs = list(args)
  for i in range(n):
    ys = []
    for e in xs:
      if isinstance(e, list):
        ys.append(e[i])
      elif isinstance(e, Address):
        if addrOffset == None:
          if e.broadcast:
            addrOffset = 0
          else:
            addrOffset = SIMD_BYTE
        ys.append(e + addrOffset*i)
      else:
        ys.append(e)
    op(*ys)

def miscTest():
  vbroadcastss(zmm1, ptr(rax))
  vaddpd(zmm2, zmm5, zmm30)
  vaddpd(xmm30, xmm20, ptr(rax))
  vaddps(xmm30, xmm20, ptr(rax))
  vaddpd(zmm2 | k5, zmm4, zmm2)
  vaddpd(zmm2 | k5 | T_z, zmm4, zmm2)
  vaddpd(zmm2 | k5 | T_z, zmm4, zmm2 | T_rd_sae)
  vaddpd(zmm2 | k5 | T_z | T_rd_sae, zmm4, zmm2)
  vcmppd(k4 | k3, zmm1, zmm2 | T_sae, 5)
  vcmpnltpd(k4|k3,zmm1,zmm2|T_sae)
  vmovups(xm2|k1|T_z, ptr(rax))
  vcvttsh2usi(r9, xmm1|T_sae)
  vcvttph2qq(zmm1|k5|T_z, xmm3|T_sae)

  vaddpd(xmm1, xmm2, ptr (rax+256))
  vaddpd(xmm1, xmm2, ptr_b (rax+256))
  vaddpd(ymm1, ymm2, ptr_b (rax+256))
  vaddpd(zmm1, zmm2, ptr_b (rax+256))
  vaddps(zmm1, zmm2, ptr_b (rax+rcx*8+8))

  vcvtpd2dq(xmm16, xword (eax+33))
  vcvtpd2dq(xmm16, ptr (eax+33))
  vcvtpd2dq(xmm21, ptr_b (eax+32))
  vcvtpd2dq(xmm0, yword (eax+33))
  vcvtpd2dq(xmm19, yword_b (eax+32))

  vfpclassps(k5|k3, zword (rax+64), 5)
  vfpclasspd(k5|k3, xword_b (rax+64), 5)
  vfpclassps(k5|k3, yword_b (rax+64), 5)

  vmovups(ptr(rax+rcx*4+123)|k1, zmm0)

  L1 = Label()
  L2 = Label()
  L(L1)
  vaddps(zmm0, zmm1, ptr(rip+L1+128));
  vaddps(zmm0, zmm1, ptr(rip+L2+256));
  vaddps(zmm0, zmm1, ptr_b(rip+L1+128));
  vaddps(zmm0, zmm1, ptr_b(rip+L2+256));
  L(L2)
  vpdpbusd(xmm0, xmm1, xmm2)
  vpdpbusd(xmm0, xmm1, xmm2, EvexEncoding)
  vpdpbusd(xmm0, xmm1, xmm2, VexEncoding)

  v2 = [zmm0, zmm1, zmm2]
  v1 = [zmm3, zmm4, zmm5]
  Unroll(3, vfmadd213ps, v2, v1, ptr(rax))
  Unroll(3, vfmadd213ps, v2, v1, ptr_b(rax))
  Unroll(3, vfmadd213ps, v2, v1, ptr_b(rax), addrOffset=4)

def runTest():
  vaddpd(zmm2 | k5 | T_z, zmm4, zmm2 | T_rd_sae)
  vaddpd(zmm2 | k5 | T_z|T_rd_sae, zmm4, zmm2)
  return
  vgatherdps(zmm3|k2, ptr(rcx+zmm13*2+64))
  vbroadcastss(zmm1, ptr(rax))
  return
  vcvtpd2dq(xmm19, yword_b (eax+32))
  vmovdqu(xmm1, ptr(r8))
  L1 = Label()
  L2 = Label()
  L(L1)
  vaddps(zmm0, zmm1, ptr(rip+L1+128))
  vaddps(xmm0, xmm1, ptr(rip+L1+128))
  vextractps(ptr(rax), xmm1, 3)
  L(L2)


def main():
  # before calling init()
  maskTest()

  parser = getDefaultParser()
  parser.add_argument('-run', help='run runTest', action='store_true')
  global param
  param = parser.parse_args()

  init(param)
  segment('text')

  if param.run:
    runTest()
  else:
    miscTest()

  term()

if __name__ == '__main__':
  main()
