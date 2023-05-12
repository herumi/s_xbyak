import sys
sys.path.append('../')
from s_xbyak import *

def main():
  parser = getDefaultParser()
  param = parser.parse_args()

  init(param)
  segment('data')
  global_('g_x')
  dd_(123)
  segment('text')

  with FuncProc('add_x'):
    with StackFrame(1) as sf:
      y = sf.p[0]
      mov(eax, ptr(rip+'g_x'))
      add(rax, y)

  term()

if __name__ == '__main__':
  main()
