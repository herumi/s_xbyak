import sys
sys.path.append('../')
from s_xbyak import *

SIMD_BIT=128

def main():
  parser = getDefaultParser()
  param = parser.parse_args()

  init(param)
  segment('text')

  with FuncProc('add_avx'):
    with StackFrame(4) as sf:
      pz = sf.p[0]
      px = sf.p[1]
      py = sf.p[2]
      n = sf.p[3]
      lpL = Label()

      L(lpL)
      vmovups(xmm0, ptr(px))
      vaddps(xmm0, xmm0, ptr(py))
      vmovups(ptr(pz), xmm0)
      add(px, 16)
      add(py, 16)
      add(pz, 16)
      sub(n, 4)
      jnz(lpL)

  term()

if __name__ == '__main__':
  main()
