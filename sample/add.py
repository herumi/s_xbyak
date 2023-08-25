import sys
sys.path.append('../')
from s_xbyak import *

def main():
  parser = getDefaultParser()
  param = parser.parse_args()

  init(param)
  segment('text')

  with FuncProc('add2'):
    with StackFrame(2) as sf:
      x = sf.p[0]
      y = sf.p[1]
      lea(rax, ptr(x + y))

  with FuncProc('add_avx512'):
     with StackFrame(4, vNum=1, vType=T_ZMM) as sf:
      pz = sf.p[0]
      px = sf.p[1]
      py = sf.p[2]
      n = sf.p[3]
      lpL = Label()

      L(lpL)
      vmovups(zmm0, ptr(px))
      vaddps(zmm0, zmm0, ptr(py))
      vmovups(ptr(pz), zmm0)
      add(px, 64)
      add(py, 64)
      add(pz, 64)
      sub(n, 16)
      jnz(lpL)

  term()

if __name__ == '__main__':
  main()
