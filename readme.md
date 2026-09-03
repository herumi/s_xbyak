# s_xbyak

ASM generation tool for GAS/NASM/MASM with Xbyak-like syntax in Python.

# Abstract

This file provides an Xbyak-like DSL to generate ASM code for GAS/NASM/MASM.
i.e., A static version of Xbyak

# Supported Assembler

- gas : GNU Assembler
- nasm : [Netwide Assembler (NASM)](https://www.nasm.us/)
- masm : [Microsoft Macro Assembler](https://learn.microsoft.com/vi-vn/cpp/assembler/masm/microsoft-macro-assembler-reference)

# How to use

There are several samples in the `sample/` directory.

## Sample of Adding Function
[sample/add.py](sample/add.py)
```python
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
```

Commentaries:
- `getDefaultParser()` parses some options.
  - `-win` : use Win64 ABI (default : AMD64 ABI)
  - `-m mode` : mode = gas/nasm/masm (default : nasm)
- `param` must have the following keys.
  - `win : bool`
  - `mode : str`

- `segment('text')`
  - Declare that the code starts here.
- `FuncProc('add2')`
  - Declare that the function `add2` starts here.
  - The header is emitted when the `with` block is entered (the constructor emits nothing) and the footer when it ends.
- `StackFrame(2)`
  - Declare that the function has two integer-type arguments
  - The prologue (push/sub rsp) is emitted when the `with` block is entered and the epilogue when it ends.
  - Remark : The current version supports only integer-(pointer)-type and the max number is four.
  - `sf.p[0]` : The register corresponding to the 1st argument.
  - `sf.p[1]` : The register corresponding to the 2nd argument.
- `lea(rax, ptr(x + y))`
  - `s_xbyak` uses `ptr(...)` instead of `ptr[...]`.
- `ret()` is automatically inserted when the `StackFrame` ends.
- `term()`
  - Terminates code generation.

## How to generate an ASM for GAS

```shell-session
$ python3 add.py -m gas > add_s.S
```

```gas
.text
.global PRE(add2)
PRE(add2):
TYPE(add2)
lea (%rdi,%rsi,1), %rax
ret
SIZE(add2)
```

- `PRE`, `TYPE`, `SIZE` are macros to absorb OS differences.

## How to generate an ASM for NASM

For Linux/Intel macOS
```python
python3 add.py -m nasm
```

```nasm
segment .text
_global add2
lea rax, [rdi+rsi]
ret
```

For Windows
```shell-session
> python3 add.py -m nasm -win
```

```nasm
segment .text
export add2
_global add2
lea rax, [rcx+rdx]
ret
```

## How to generate an ASM for MASM

```shell-shession
$ python3 add.py -m masm
```

```nasm
_text segment
add2 proc export
lea rax, qword ptr [rcx+rdx]
ret
add2 endp
_text ends
end
```
## Sample of Memory Aaccess
[sample/mem.py](sample/mem.py)
```python
def main():
  parser = getDefaultParser()
  param = parser.parse_args()

  init(param)
  segment('data')
  global_('g_x')
  dd_(123)
  segment('text')

  with FuncProc('inc_and_add'):
    with StackFrame(1) as sf:
      inc(dword(rip+'g_x'))
      y = sf.p[0]
      mov(eax, ptr(rip+'g_x'))
      add(rax, y)

  term()
```

Commentaries:
- `segment('data')`
  - Declare that the data starts here.
- `global_('g_x')`
  - The memory named `g_x` can be accessed from the other files.
- `dd_(123)`
  - Put `123` as 32-bit integer.
- `(rip+'g_x')`
  - Use `rip+` to access by relative addressing.
- `inc(dword(...))`
  - Use `qword(64-bit)/dword(32-bit)/word(16-bit)/byte(8-bit)` instead of `ptr` to specify the memory size.

## Sample of AVX
[sample/avx.py](sample/avx.py)
```python
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
```

This is a tiny sample of a label and AVX. This is not fast code.

Commentaries:
- `lpL = Label()`
  - Define a label instance.
- `L(lpL)`
  - Set lpL here.
- `jnz(lpL)`
  - Jump to lpL if non-zero.

# StackFrame

`StackFrame` makes a stack frame of a function according to the ABI (AMD64 or Win64) and releases it at the end of the `with` block.

```python
StackFrame(pNum, tNum=0, useRDX=False, useRCX=False, stackSizeByte=0, callRet=True, vNum=0, vType=0, noVzeroupper=False)
```

- `pNum` : number of integer arguments of the function. `sf.p[0]`, ..., `sf.p[pNum-1]` are the corresponding registers (max 4).
- `tNum` : number of temporary registers. `sf.t[0]`, ..., `sf.t[tNum-1]` are assigned and callee-saved registers are pushed/popped automatically.
- `useRDX` : set True if you want to use `rdx`. The argument assigned to `rdx` (if any) is moved to `r11`.
- `useRCX` : set True if you want to use `rcx`. The argument assigned to `rcx` (if any) is moved to `r10`.
- `stackSizeByte` : size of a local stack area. `ptr(rsp)`, ..., `ptr(rsp + stackSizeByte - 1)` are available.
- `callRet` : call `ret()` automatically at the end of the `StackFrame` (default True).
- `vNum` : number of SIMD registers. `sf.v[0]`, ..., `sf.v[vNum-1]` are assigned from the register of index 0 in order.
- `vType` : type of SIMD registers. It is required if `vNum > 0`.
- `noVzeroupper` : suppress `vzeroupper` in the epilog. It requires `vType=T_YMM` or `T_ZMM`.

vType | sf.v[i] | meaning | max vNum
-|-|-|-
`T_SSE` | `Xmm(i)` | declare that only SSE instructions are used | 16
`T_XMM` | `Xmm(i)` | use xmm registers with AVX/AVX-512 instructions | 32
`T_YMM` | `Ymm(i)` | use ymm registers | 32
`T_ZMM` | `Zmm(i)` | use zmm registers | 32

- On Win64, the lower 128 bits of xmm6-xmm15 are callee-saved, so if `vNum >= 7` then xmm6, ..., xmm(min(vNum, 16)-1) are saved in the prolog and restored in the epilog. Nothing is saved on AMD64 (Linux, macOS) because all SIMD registers are volatile.
- If `vType` is `T_YMM` or `T_ZMM`, then `vzeroupper` is inserted at the top of the epilog (before restoring the xmm registers) to avoid AVX-SSE transition penalties. Set `noVzeroupper=True` to suppress it, e.g., when the function returns a value in ymm0/zmm0.
- The save/restore instruction is `movaps` if `vzeroupper` is emitted or `vType=T_SSE`, otherwise (`T_XMM` or `noVzeroupper=True`) `vmovaps` to avoid executing a legacy SSE instruction while the upper state may be dirty.

`StackFrame` raises an exception if `vNum > 0` without `vType`, if `vNum` exceeds the max value of the table, or if `noVzeroupper=True` is specified with `vType` other than `T_YMM`/`T_ZMM`.

Example (nasm + Win64):
```python
with FuncProc('sum8'):
  with StackFrame(2, vNum=8, vType=T_ZMM) as sf:
    # sf.p[0], sf.p[1] : arguments, sf.v[0], ..., sf.v[7] : zmm0, ..., zmm7
    ...
```
```nasm
sum8:
sub rsp, 40
movaps [rsp], xmm6
movaps [rsp+16], xmm7
...
vzeroupper
movaps xmm6, [rsp]
movaps xmm7, [rsp+16]
add rsp, 40
ret
```

# Mnemonics

Most of the mnemonics are the same as defined in the Intel manual except for `and_`, `or_`, `xor_`, `not_`, `in_`, `out_`, `int_`.

# Label

```python
lpL = Label()
nextL = Label()
L(lpL)  # lpL is set here
ja(nextL)
jmp(lpL)
L(nextL)
```

# db, dw, dd, dq

Use `db_`, `dw_`, `dd_`, `dq_`.

# rip

```python
makeLabel('varX')
dq_(12345)
mov(rax, ptr(rip+'varX'))`
```

# AVX-512

- Merge-masking
  - `vaddps(xmm1 | k1, xmm2, xmm3)`
  - `vmovups(ptr(rax+rcx*4+123)|k1, zmm0)`
- Zero-masking
  - `vsubps(ymm0 | k4 | T_z, ymm1, ymm2)`
- Broadcast
  - `vmulps(zmm0, zmm1, ptr_b(rax))`
  - `ptr_b` is converted to `{1toX}` according to the mnemonics.
- Rounding
  - `vdivps(zmm0, zmm1, zmm2|T_rz_sae)`
- Suppress all exceptions
  - `vmaxss(xmm1, xmm2, xmm3|T_sae)`
- Distinguish `m128` and `m256`
  - `vcvtpd2dq(xmm16, xword (eax+32))` # `m128`
  - `vcvtpd2dq(xmm0, yword (eax+32))`  # `m256`
  - `vcvtpd2dq(xmm21, ptr_b (eax+32))` # `m128` + broadcast
  - `vcvtpd2dq(xmm19, yword_b (eax+32))` # `m256` + broadcast

# s_xbyak_llvm.py

`s_xbyak_llvm.py` is a sibling DSL that generates LLVM-IR (text) instead of x64 assembly.
It is a single file with no dependency on `s_xbyak.py`; copy it next to your generator and `from s_xbyak_llvm import *`.

```python
import sys
import argparse
sys.path.append('../')
from s_xbyak_llvm import *

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-proto', action='store_true', default=False, help='show C prototype')
  opt = parser.parse_args()
  init()
  if opt.proto:
    showPrototype()

  # a function defined in another module: emit `declare i64 @ext_f(i64)`
  ext_f = Function('ext_f', Int(64), Int(64))
  declare(ext_f)

  # `define i64 @add3(i64, i64, i64)`; the header is emitted on entering `with`
  x = Int(64)
  y = Int(64)
  z = Int(64)
  with Function('add3', Int(64), x, y, z):
    t = add(add(x, y), z)
    r = call(ext_f, t)
    ret(r)

  term()

if __name__ == '__main__':
  main()
```

- `Function(name, ret, *args)` only records the signature. Entering the `with` block emits the `define` header (or the C prototype in `-proto` mode) and leaving it emits `}`.
- `declare(f)` emits a `declare` line for a `Function` defined elsewhere (nothing in `-proto` mode).
- Operands are `Int(bit)`, `IntPtr(bit)`, `Imm(v)` and the values returned by `add`, `mul`, `zext`, `load`, `call`, `select`, `icmp`, `phi`, etc. Multi-limb helpers: `loadN`, `storeN`, `makeVar`.

# License

[modified new BSD License](http://opensource.org/licenses/BSD-3-Clause)

# Author

MITSUNARI Shigeo(herumi@nifty.com)

# Sponsors welcome
[GitHub Sponsor](https://github.com/sponsors/herumi)
