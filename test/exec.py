import sys
sys.path.append('../')
from s_xbyak import *
import argparse

def genFunc1():
  with FuncProc('get_d1'):
    with StackFrame(0):
      mov(rax, 'd1')
      mov(rax, ptr(rax))

def genFunc2():
  with FuncProc('get_d2'):
    with StackFrame(0):
      lea(rax, ptr('d2'))
      mov(rax, ptr(rax))

def genFunc3():
  with FuncProc('get_d3'):
    with StackFrame(0):
      mov(rax, ptr('d3'))

def genFunc4():
  with FuncProc('get_d4'):
    with StackFrame(0):
      mov(rax, ptr(rip+'d4'))

def genFunc5():
  with FuncProc('get_d5'):
    with StackFrame(0):
      lea(rax, ptr(rip+'d5'))
      mov(rax, ptr(rax))

def genCFuncs():
  print('''#include <cybozu/test.hpp>

extern "C" {
int get_d1();
int get_d2();
int get_d3();
int get_d4();
int get_d5();
extern int d5;
}

CYBOZU_TEST_AUTO(test)
{
//  CYBOZU_TEST_EQUAL(get_d1(), 11111);
//  CYBOZU_TEST_EQUAL(get_d2(), 22222);
//  CYBOZU_TEST_EQUAL(get_d3(), 33333);
//  CYBOZU_TEST_EQUAL(get_d4(), 44444);
  CYBOZU_TEST_EQUAL(get_d5(), 55555);
  d5 = 9;
  CYBOZU_TEST_EQUAL(get_d5(), 9);
}
''')

def main():
  parser = getDefaultParser()
  parser.add_argument('-cpp', help='generate cpp', action='store_true')
  global param

  param = parser.parse_args()
  if param.cpp:
    genCFuncs()
    return

  init(param)
  segment('data')

#  global_('d1')
  makeLabel('d1')
  dq_(hex(11111))

  makeLabel('d2')
  dq_(22222)

  makeLabel('d3')
  dq_(33333)

  makeLabel('d4')
  dq_(44444)

#  makeLabel('d5')
  global_('d5')
  dq_(55555)

  segment('text')

#  genFunc1()
#  genFunc2() # require /LARGEADDRESSAWARE:NO / -fPIE
#  genFunc3() # require /LARGEADDRESSAWARE:NO
#  genFunc4() # seg on Linux, err on masm
  genFunc5()


  term()

if __name__ == '__main__':
  main()
