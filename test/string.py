import sys
sys.path.append('../')
from s_xbyak import *
import argparse

def gen_findCharGeneric(name, mode):
  with FuncProc(name):
    with StackFrame(4, useRDX=True, useRCX=True, callRet=False) as sf:
      text = sf.p[0]
      textSize = sf.p[1]
      key = sf.p[2]
      keySize = sf.p[3]

      lpL = Label()
      size_lt_16L = Label()
      exitL = Label()
      lastL = Label()
      notFoundL = Label()
      foundL = Label()
      loadL = Label()

      vmovdqu(xm1, ptr(key))
      mov(rax, keySize)
      mov(rdx, textSize)
      cmp(rdx, 16)
      jb(size_lt_16L)
      and_(rdx, ~15)
      L(lpL)
      vpcmpestri(xm1, ptr(text), mode)
      jna(exitL)
      add(text, 16)
      sub(rdx, 16)
      jnz(lpL)

      mov(rdx, textSize)
      and_(edx, 15)

      L(size_lt_16L)
      test(edx, edx)
      je(notFoundL)
      mov(rcx, text)
      and_(ecx, 4095)
      cmp(ecx, 4080)
      jbe(loadL)
      add(ecx, edx)
      cmp(ecx, 4096)
      ja(loadL)
      mov(rcx, text)
      and_(rcx, -16)
      vmovdqa(xm0, ptr(rcx))
      mov(rcx, text)
      and_(ecx, 15)
      lea(textSize, rip('shiftPtn'))
#      mov(textSize, 'shiftPtn')
      vmovdqu(xm2, ptr(textSize + rcx))
      vpshufb(xm0, xm0, xm2)
      jmp(lastL)

      L(loadL)
      vmovdqu(xm0, ptr(text))

      L(lastL)
      vpcmpestri(xm1, xm0, mode)

      L(exitL)
      jnc(notFoundL)

      L(foundL)
      lea(rax, ptr(text + rcx))
      ret()

      L(notFoundL)
      xor_(eax, eax)
      ret()

def gen():
  gen_findCharGeneric('mie_findCharAnyAVX', 0)
  gen_findCharGeneric('mie_findCharRangeAVX', 4)


def main():
  parser = getDefaultParser()
  global param
  param = parser.parse_args()

  init(param)
  segment('data')
  makeLabel('shiftPtn')
  tbl = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80]
  for e in tbl:
    db_(e)
  segment('text')

  gen()

  term()

if __name__ == '__main__':
  main()
