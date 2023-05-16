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

def genFunc6():
  with FuncProc('get_d6'):
    with StackFrame(0):
      lea(rax, ptr(rip+'d6'))
      mov(rax, ptr(rax))

def genFunc7():
  with FuncProc('inc_b'):
    with StackFrame(1) as sf:
      inc(byte(sf.p[0]))

def genFunc8():
  with FuncProc('inc_w'):
    with StackFrame(1) as sf:
      inc(word(sf.p[0]))

def genFunc9():
  with FuncProc('inc_d'):
    with StackFrame(1) as sf:
      inc(dword(sf.p[0]))

def genFunc10():
  with FuncProc('inc_q'):
    with StackFrame(1) as sf:
      inc(qword(sf.p[0]))

def genCFuncs():
  print('''#include <cybozu/test.hpp>
#include <stdint.h>
extern "C" {
int get_d1();
int get_d2();
int get_d3();
int get_d4();
int get_d5();
int get_d6();
extern int d5;
void inc_b(uint64_t *);
void inc_w(uint64_t *);
void inc_d(uint64_t *);
void inc_q(uint64_t *);
}

CYBOZU_TEST_AUTO(test)
{
//  CYBOZU_TEST_EQUAL(get_d1(), 11111);
//  CYBOZU_TEST_EQUAL(get_d2(), 22222);
//  CYBOZU_TEST_EQUAL(get_d3(), 33333);
  CYBOZU_TEST_EQUAL(get_d4(), 44444);
  CYBOZU_TEST_EQUAL(get_d5(), 55555);
  d5 = 9;
  CYBOZU_TEST_EQUAL(get_d5(), 9);
  CYBOZU_TEST_EQUAL(get_d6(), 66666);
  const uint64_t allOne = ~uint64_t(0);
  uint64_t q = allOne;
  inc_b(&q);
  CYBOZU_TEST_EQUAL(q, allOne << 8);
  q = allOne;
  inc_w(&q);
  CYBOZU_TEST_EQUAL(q, allOne << 16);
  q = allOne;
  inc_d(&q);
  CYBOZU_TEST_EQUAL(q, allOne << 32);
  q = allOne;
  inc_q(&q);
  CYBOZU_TEST_EQUAL(q, 0);
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

  makeLabel('d6')
  dq_(66666)

  segment('text')

#  genFunc1() # err on mac, masm ok on linux, gas err on linux, nasm/masm ok on win
#  genFunc2() # err on mac/linux, require /LARGEADDRESSAWARE:NO
#  genFunc3() # err on mac/linux, require /LARGEADDRESSAWARE:NO
  genFunc4()
  genFunc5()
  genFunc6()
  genFunc7()
  genFunc8()
  genFunc9()
  genFunc10()


  term()

if __name__ == '__main__':
  main()
