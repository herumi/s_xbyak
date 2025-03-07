import sys
sys.path.append('../')
from s_xbyak import *

def main():
  parser = getDefaultParser()
  param = parser.parse_args()

  init(param)
  segment('data')
  extern_('g_a', 'dword')
  segment('text')

  with FuncProc('sum3'):
    with StackFrame(1) as sf:
      mov(eax, ptr(rip+'g_a'))
      add(eax, ptr(rip+'g_a'+4))
      add(eax, ptr(rip+'g_a'+8))
      #vmovups(xm0, ptr(rip+'g_a'))

  term()

if __name__ == '__main__':
  main()
