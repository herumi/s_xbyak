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

  term()

if __name__ == '__main__':
  main()
