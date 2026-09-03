import sys
sys.path.append('../')
from s_xbyak_llvm import *
from mont import *
from primetbl import *
import argparse

unit = 0
unit2 = 0
mont = None

def gen_add(N):
  bit = unit * N
  resetGlobalIdx()
  pz = IntPtr(unit)
  px = IntPtr(unit)
  py = IntPtr(unit)
  with Function(f'mcl_fp_addPre{N}', Void, pz, px, py):
    x = zext(loadN(px, N), bit + unit)
    y = zext(loadN(py, N), bit + unit)
    z = add(x, y)
    storeN(trunc(z, bit), pz)
    r = trunc(lshr(z, bit), unit)
    ret(Void)

def gen_mulUU():
  resetGlobalIdx();
  z = Int(unit2)
  x = Int(unit)
  y = Int(unit)
  with Function(f'mul{unit}x{unit}L', z, x, y, private=True) as f:
    x = zext(x, unit2)
    y = zext(y, unit2)
    z = mul(x, y)
    ret(z)
  return f

def gen_extractHigh():
  resetGlobalIdx()
  z = Int(unit)
  x = Int(unit2)
  with Function(f'extractHigh{unit}', z, x, private=True) as f:
    x = lshr(x, unit)
    z = trunc(x, unit)
    ret(z)
  return f

def gen_mulPos(mulUU):
  resetGlobalIdx()
  xy = Int(unit2)
  px = IntPtr(unit)
  y = Int(unit)
  i = Int(unit)
  with Function(f'mulPos{unit}x{unit}', xy, px, y, i, private=True) as f:
    x = load(getelementptr(px, i))
    xy = call(mulUU, x, y)
    ret(xy)
  return f

def gen_once():
  mulUU = gen_mulUU()
  gen_extractHigh()
  gen_mulPos(mulUU)

def gen_add_raw(x, y, p, isFullBit):
  bit = x.bit
  if isFullBit:
    x = zext(x, bit + unit)
    y = zext(y, bit + unit)
    x = add(x, y)
    p = zext(p, bit + unit)
    y = sub(x, p)
    c = trunc(lshr(y, bit), 1)
    x = select(c, x, y)
    x = trunc(x, bit)
  else:
    x = add(x, y)
    y = sub(x, p)
    c = trunc(lshr(y, bit - 1), 1)
    x = select(c, x, y)
  return x

def gen_fp_add(name, N, dataVar):
  bit = unit * N
  resetGlobalIdx();
  pz = IntPtr(unit)
  px = IntPtr(unit)
  py = IntPtr(unit)
  with Function(name, Void, pz, px, py):
    pp = bitcast(dataVar, unit)
    # volatile: keep the operand loads unfused so store-forwarded inputs
    # (common in dependency chains) do not pay the folded-load latency.
    x = loadN(px, N, volatile=True)
    y = loadN(py, N, volatile=True)
    p = loadN(pp, N)
    x = gen_add_raw(x, y, p, mont.isFullBit)
    storeN(x, pz)
    ret(Void)

def gen_fp2_add(name, N, dataVar, offset):
  bit = unit * N
  resetGlobalIdx();
  pz = IntPtr(unit)
  px = IntPtr(unit)
  py = IntPtr(unit)
  with Function(name, Void, pz, px, py):
    pp = bitcast(dataVar, unit)
    p = loadN(pp, N)
    for i in range(2):
      x = loadN(px, N, offset=i*offset, volatile=True)
      y = loadN(py, N, offset=i*offset, volatile=True)
      x = gen_add_raw(x, y, p, mont.isFullBit)
      storeN(x, pz, offset=i*offset)

    ret(Void)

# Writable {zero, p} table for the sub reduction. Layout is
# [Npad x i64] zero, then p, padded to 2*Npad limbs (Npad = N rounded up to a
# power of two so the borrow-scaled offset is a single shift and each entry is
# cache-line aligned). It must be a non-constant global with external linkage:
# if the optimizer can prove the contents (constant, or internal + never
# stored), it folds the conditional +p back into an and-mask/cmov sequence.
def makeSubTbl(pre, mont):
  N = mont.pn
  Npad = 1 << (N - 1).bit_length()
  mask = (1 << unit) - 1
  limbs = [(mont.p >> (unit * i)) & mask for i in range(N)]
  v = [0] * Npad + limbs + [0] * (Npad - N)
  tbl = makeVar(f'{pre}sub_tbl', unit, v, static=False, const=False, align=64)
  return (tbl, Npad)

# Reduction via the {zero, p} table indexed by the borrow. The variable-index
# GEP cannot be rewritten into a select of the loaded values (the table is
# writable memory), so the conditional +p lowers to an add/adc chain with
# folded memory operands: the same idiom as the hand-written x64 asm.
def gen_sub_raw_tbl(x, y, ptbl, Npad, isFullBit):
  bit = x.bit
  if isFullBit:
    x = zext(x, bit + unit)
    y = zext(y, bit + unit)
    v = sub(x, y)
    c = trunc(lshr(v, bit), 1)
    v = trunc(v, bit)
  else:
    v = sub(x, y)
    c = trunc(lshr(v, bit - 1), 1)
  off = shl(zext(c, unit), Npad.bit_length() - 1)
  addr = getelementptr(ptbl, off)
  p = load(bitcast(addr, bit))
  v = add(v, p)
  return v

# Reduction via an and-mask: p is loaded from a fixed address known at
# function entry, so the load runs in parallel with the subtraction and only
# sext -> and -> add follow the borrow. The table variant instead derives the
# load address from the borrow, which puts the L1 load-use latency (~4 cycles)
# on the dependency chain when the borrow pattern defeats address prediction;
# on aarch64 this made sub latency 1.23x of mcl. On x64 the table still wins
# because it lowers to add/adc with folded memory operands, so this variant is
# selected by -sub_mask (passed by the Makefile on non-x86_64).
def gen_sub_raw_mask(x, y, p, isFullBit):
  bit = x.bit
  if isFullBit:
    x = zext(x, bit + unit)
    y = zext(y, bit + unit)
    v = sub(x, y)
    c = trunc(lshr(v, bit), 1)
    v = trunc(v, bit)
  else:
    v = sub(x, y)
    c = trunc(lshr(v, bit - 1), 1)
  v = add(v, and_(p, sext(c, bit)))
  return v

def gen_fp_sub(name, N, subTbl, dataVar, useMask):
  bit = unit * N
  resetGlobalIdx();
  pz = IntPtr(unit)
  px = IntPtr(unit)
  py = IntPtr(unit)
  with Function(name, Void, pz, px, py):
    if useMask:
      p = loadN(bitcast(dataVar, unit), N)
    else:
      tbl, Npad = subTbl
      ptbl = bitcast(tbl, unit)
    x = loadN(px, N, volatile=True)
    y = loadN(py, N, volatile=True)
    if useMask:
      v = gen_sub_raw_mask(x, y, p, mont.isFullBit)
    else:
      v = gen_sub_raw_tbl(x, y, ptbl, Npad, mont.isFullBit)
    storeN(v, pz)
    ret(Void)

def gen_fp2_sub(name, N, subTbl, dataVar, useMask, offset):
  bit = unit * N
  resetGlobalIdx();
  pz = IntPtr(unit)
  px = IntPtr(unit)
  py = IntPtr(unit)
  with Function(name, Void, pz, px, py):
    if useMask:
      p = loadN(bitcast(dataVar, unit), N)
    else:
      tbl, Npad = subTbl
      ptbl = bitcast(tbl, unit)
    for i in range(2):
      x = loadN(px, N, offset=i*offset, volatile=True)
      y = loadN(py, N, offset=i*offset, volatile=True)
      if useMask:
        v = gen_sub_raw_mask(x, y, p, mont.isFullBit)
      else:
        v = gen_sub_raw_tbl(x, y, ptbl, Npad, mont.isFullBit)
      storeN(v, pz, offset=i*offset)

    ret(Void)

# split x into (high, low) with low being sizeL bits
def split(x, sizeL):
  H = lshr(x, sizeL)
  H = trunc(H, x.bit - sizeL)
  L = trunc(x, sizeL)
  return (H, L)

# return [xs[n-1]:xs[n-2]:...:xs[0]]
def pack(xs):
  x = xs[0]
  for y in xs[1:]:
    shift = x.bit
    size = x.bit + y.bit
    x = zext(x, size)
    y = zext(y, size)
    y = shl(y, shift)
    x = or_(x, y)
  return x

def gen_mulUnit(name, N, mulPos, extractHigh):
  bit = unit * N
  bu = bit + unit
  resetGlobalIdx()
  z = Int(bu)
  px = IntPtr(unit)
  y = Int(unit)
  # alwaysinline: for N >= 8 clang stops inlining this into mulPre and the
  # 2N call round-trips cost ~1.7x in throughput (see memo.md 2026-08-31)
  with Function(name, z, px, y, private=True, alwaysinline=True) as f:
    L = []
    H = []
    for i in range(N):
      xy = call(mulPos, px, y, Imm(i, unit))
      L.append(trunc(xy, unit))
      H.append(call(extractHigh, xy))

    LL = pack(L)
    HH = pack(H)
    LL = zext(LL, bu)
    HH = zext(HH, bu)
    HH = shl(HH, unit)
    z = add(LL, HH)
    ret(z)
  return f

def gen_mul(name, mont, dataVar, mulUnit):
  N = mont.pn
  bit = unit * N
  bu = bit + unit
  bu2 = bit + unit * 2
  resetGlobalIdx()
  pz = IntPtr(unit)
  px = IntPtr(unit)
  py = IntPtr(unit)
  with Function(name, Void, pz, px, py) as f:
    pp = bitcast(dataVar, unit)
    ipval = mont.ip
    if mont.isFullBit:
      for i in range(N):
        y = load(getelementptr(py, i))
        xy = call(mulUnit, px, y)
        if i == 0:
          a = zext(xy, bu2)
          at = trunc(xy, unit)
        else:
          xy = zext(xy, bu2)
          a = add(s, xy)
          at = trunc(a, unit)
        q = mul(at, ipval)
        pq = call(mulUnit, pp, q)
        pq = zext(pq, bu2)
        t = add(a, pq)
        s = lshr(t, unit)

      s = trunc(s, bu)
      p = zext(loadN(pp, N), bu)
      vc = sub(s, p)
      c = trunc(lshr(vc, bit), 1)
      z = select(c, s, vc)
      z = trunc(z, bit)
      storeN(z, pz)
    else:
      y = load(py)
      xy = call(mulUnit, px, y)
      c0 = trunc(xy, unit)
      q = mul(c0, ipval)
      pq = call(mulUnit, pp, q)
      t = add(xy, pq)
      t = lshr(t, unit)
      for i in range(1, N):
        y = load(getelementptr(py, i))
        xy = call(mulUnit, px, y)
        t = add(t, xy)
        c0 = trunc(t, unit)
        q = mul(c0, ipval)
        pq = call(mulUnit, pp, q)
        t = add(t, pq)
        t = lshr(t, unit)
      t = trunc(t, bit)
      vc = sub(t, loadN(pp, N))
      c = trunc(lshr(vc, bit - 1), 1)
      z = select(c, t, vc)
      storeN(z, pz)
    ret(Void)
  return f

# Montgomery reduction core: reduce a 2N-unit value to z = xy R^-1 mod p and
# return it (bit wide). The low N units come packed in lo; the high units are
# fetched one per iteration via getHi(i) -> unit-wide limb N+i, so the caller
# chooses the source (memory for gen_mod, an SSA value for gen_sqr).
def mod_raw(lo, getHi, mont, pp, mulUnit):
  N = mont.pn
  bit = unit * N
  bu = bit + unit
  bu2 = bit + unit * 2
  ipval = mont.ip
  p = loadN(pp, N)
  t = lo
  H = None
  for i in range(N):
    if N == 1:
      q = mul(t, ipval)
    else:
      q = mul(trunc(t, unit), ipval)
    pq = call(mulUnit, pp, q)
    if i > 0:
      H = zext(H, bu)
      H = shl(H, bit)
      pq = add(pq, H)
    nxt = getHi(i)
    t = pack([t, nxt])
    t = zext(t, bu2)
    pq = zext(pq, bu2)
    t = add(t, pq)
    t = lshr(t, unit)
    t = trunc(t, bu)
    H, t = split(t, bit)
  if mont.isFullBit:
    p = zext(p, bu)
    t = pack([t, H])
    vc = sub(t, p)
    c = trunc(lshr(vc, bit), 1)
    z = select(c, t, vc)
    z = trunc(z, bit)
  else:
    vc = sub(t, p)
    c = trunc(lshr(vc, bit - 1), 1)
    z = select(c, t, vc)
  return z

# Montgomery reduction: z = xy R^-1 mod p where xy has 2N units.
def gen_mod(name, mont, dataVar, mulUnit):
  N = mont.pn
  resetGlobalIdx()
  pz = IntPtr(unit)
  pxy = IntPtr(unit)
  with Function(name, Void, pz, pxy) as f:
    pp = bitcast(dataVar, unit)
    lo = loadN(pxy, N)
    z = mod_raw(lo, lambda i: load(getelementptr(pxy, N + i)), mont, pp, mulUnit)
    storeN(z, pz)
    ret(Void)
  return f

# Radix-2^128 variant of mod_raw. The serial recurrence of mod_raw
# (t0 -> q = t0*ip -> p[0]*q -> new t0, ~8-9 cycles/unit on Apple M4) is the
# bottleneck of the reduction, so q is computed two units at a time from the
# current t via ip2 = -p^-1 mod 2^128: the odd step's q no longer waits for
# the even step's accumulation and the recurrence has half as many stages.
# The cost is hi64((t mod 2^128) * ip2) (umulh + 2 madd per pair). The
# accumulation is kept in exactly the shape of mod_raw: merging the two p*q
# rows before adding them to t makes clang interleave two carry chains via
# mrs/msr NZCV and costs 10% throughput. See memo.md 2026-08-03.
# Requires N even and p not full bit.
def mod128_raw(lo, getHi, mont, pp, mulUnit):
  N = mont.pn
  assert N % 2 == 0 and not mont.isFullBit
  bit = unit * N
  bu = bit + unit
  bu2 = bit + unit * 2
  u2 = unit * 2
  ip2 = (-pow(mont.p, -1, 1 << u2)) % (1 << u2)
  p = loadN(pp, N)
  t = lo
  H = None
  for i in range(N // 2):
    q = mul(trunc(t, u2), ip2)
    qs = [trunc(q, unit), trunc(lshr(q, unit), unit)]
    for j in range(2):
      pq = call(mulUnit, pp, qs[j])
      if i > 0 or j > 0:
        # previous carry, added into the top unit of pq (headroom: p is not
        # full bit)
        pq = add(pq, shl(zext(H, bu), bit))
      nxt = getHi(2 * i + j)
      t = pack([t, nxt])
      t = add(zext(t, bu2), zext(pq, bu2))
      t = lshr(t, unit)
      t = trunc(t, bu)
      H, t = split(t, bit)
  vc = sub(t, p)
  c = trunc(lshr(vc, bit - 1), 1)
  return select(c, t, vc)

# Montgomery reduction, radix-2^128 variant (see mod128_raw).
def gen_mod128(name, mont, dataVar, mulUnit):
  N = mont.pn
  resetGlobalIdx()
  pz = IntPtr(unit)
  pxy = IntPtr(unit)
  with Function(name, Void, pz, pxy) as f:
    pp = bitcast(dataVar, unit)
    lo = loadN(pxy, N)
    z = mod128_raw(lo, lambda i: load(getelementptr(pxy, N + i)), mont, pp, mulUnit)
    storeN(z, pz)
    ret(Void)
  return f

# Radix-2^128 variant of the fused Montgomery mul (see mod128_raw for the
# idea): q is computed two units at a time via ip2 = -p^-1 mod 2^128, so the
# serial recurrence t0 -> q -> p[0]*q -> new t0 has half as many stages.
# The row accumulation is kept in exactly the shape of gen_mul (one unit at a
# time); only the q supply changes. The pair's q needs t mod 2^128 after the
# x*y[2i] row plus the contribution of the x*y[2i+1] row to the second unit,
# which is just lo(x[0]*y[2i+1]): only that single unit is computed early, so
# the full xy1 row is not kept live across the first reduction row (computing
# it early doubles the live ranges and costs ~2x stack traffic on x64).
# Requires N even and p not full bit.
def gen_mul128(name, mont, dataVar, mulUnit):
  N = mont.pn
  assert N % 2 == 0 and not mont.isFullBit
  bit = unit * N
  u2 = unit * 2
  ip2 = (-pow(mont.p, -1, 1 << u2)) % (1 << u2)
  resetGlobalIdx()
  pz = IntPtr(unit)
  px = IntPtr(unit)
  py = IntPtr(unit)
  with Function(name, Void, pz, px, py) as f:
    pp = bitcast(dataVar, unit)
    x0 = load(px)
    for i in range(N // 2):
      y0 = load(getelementptr(py, 2 * i))
      xy0 = call(mulUnit, px, y0)
      if i == 0:
        t = xy0
      else:
        t = add(t, xy0)
      y1 = load(getelementptr(py, 2 * i + 1))
      m1 = mul(x0, y1) # low unit of the x*y[2i+1] row
      lo2 = add(trunc(t, u2), shl(zext(m1, u2), unit))
      q = mul(lo2, ip2)
      qs = [trunc(q, unit), trunc(lshr(q, unit), unit)]
      pq = call(mulUnit, pp, qs[0])
      t = add(t, pq)
      t = lshr(t, unit)
      xy1 = call(mulUnit, px, y1)
      t = add(t, xy1)
      pq = call(mulUnit, pp, qs[1])
      t = add(t, pq)
      t = lshr(t, unit)
    t = trunc(t, bit)
    vc = sub(t, loadN(pp, N))
    c = trunc(lshr(vc, bit - 1), 1)
    z = select(c, t, vc)
    storeN(z, pz)
    ret(Void)
  return f

# pz[2N] = px[N] * py[N] (no reduction). Port of gen.py:generic_fpDbl_mul of
# mcl: schoolbook rows x * y[i] accumulated in the bit+unit accumulator t, whose
# bottom unit is final after each row and is stored immediately.
def mulPre_raw(pz, px, py, N, mulUnit):
  if N == 1:
    x = zext(load(px), unit2)
    y = zext(load(py), unit2)
    storeN(mul(x, y), pz)
    return
  y = load(py)
  xy = call(mulUnit, px, y)
  store(trunc(xy, unit), pz)
  t = lshr(xy, unit)
  for i in range(1, N):
    y = load(getelementptr(py, i))
    xy = call(mulUnit, px, y)
    t = add(t, xy)
    if i < N - 1:
      storeN(trunc(t, unit), pz, i)
      t = lshr(t, unit)
  storeN(t, pz, N - 1)

# mulPre: pz[2N] = px[N] * py[N] (no reduction).
def gen_mulPre(name, N, mulUnit):
  resetGlobalIdx()
  pz = IntPtr(unit)
  px = IntPtr(unit)
  py = IntPtr(unit)
  with Function(name, Void, pz, px, py) as f:
    mulPre_raw(pz, px, py, N, mulUnit)
    ret(Void)
  return f

# mulPreWide: pz[2N] = px[N] * py[N] via a single wide "mul i(2*bit)"
def gen_mulPreWide(name, N):
  resetGlobalIdx()
  pz = IntPtr(unit)
  px = IntPtr(unit)
  py = IntPtr(unit)
  bit = unit * N
  with Function(name, Void, pz, px, py) as f:
    x = zext(loadN(px, N), bit * 2)
    y = zext(loadN(py, N), bit * 2)
    storeN(mul(x, y), pz)
    ret(Void)
  return f

# sqrPreWide: pz[2N] = px[N]^2 via a single wide "mul i(2*bit)"
def gen_sqrPreWide(name, N):
  resetGlobalIdx()
  pz = IntPtr(unit)
  px = IntPtr(unit)
  bit = unit * N
  with Function(name, Void, pz, px) as f:
    x = zext(loadN(px, N), bit * 2)
    storeN(mul(x, x), pz)
    ret(Void)
  return f

# If True then sqrPre(z, x) is a call to mulPre(z, x, x), as in mcl's
# gen_mcl_fpDbl_sqrPre, instead of the dedicated schedule below.
# This used to be the fastest variant: the old row-major triangle accumulation
# rippled every add's carry up to the top of one wide accumulator and lost to
# the plain 36-mulx schoolbook. The bottom-up anti-diagonal schedule below
# matches the handwritten x64 sqrPre6, so the call variant is now obsolete.
USE_MULPRE_FOR_SQRPRE = not True

# sqrPre: pz[2N] = px[N]^2 (no reduction).
# Same schedule as the handwritten x64 sqrPre6 of fp_generator.hpp: the cross
# products on the anti-diagonal d = j - i, x[i]*x[i+d], sit at limbs
# d, d+2, ... and tile without overlap, so a row is a plain concat (pack).
# Rows are accumulated bottom-up (d = N-1 .. 1); each row extends the
# accumulator by one limb at both ends, so a row add is one short carry chain
# absorbed in the row's own top limb. Keeping the accumulator at its minimal
# width (grow by 2 limbs per row, no early zext to 2N limbs) matters: with
# full-width adds clang keeps 2N-limb values live and spills heavily.
# Finally double the accumulator (each cross term appears twice by symmetry)
# and add the diagonal squares x[i]^2, which tile the full 2N limbs exactly.
def sqrPre_raw(x, N):
  bit2 = unit * N * 2
  if N == 1:
    return mul(zext(x[0], unit2), zext(x[0], unit2))
  acc = None
  for d in range(N - 1, 0, -1):
    row = pack([mul(zext(x[i], unit2), zext(x[i + d], unit2)) for i in range(N - d)])
    if acc is None:
      acc = row
    else:
      acc = add(shl(zext(acc, row.bit), unit), row)
  acc = zext(acc, acc.bit + unit)
  acc = add(acc, acc)
  z = shl(zext(acc, bit2), unit)
  # emit the diagonal mulx last, close to their only use: hoisting them to
  # the top lengthens their live ranges and costs ~1 cycle in practice
  diag = pack([mul(zext(x[i], unit2), zext(x[i], unit2)) for i in range(N)])
  z = add(z, diag)
  return z

def gen_sqrPre(name, N, mulPreF):
  resetGlobalIdx()
  pz = IntPtr(unit)
  px = IntPtr(unit)
  with Function(name, Void, pz, px):
    if USE_MULPRE_FOR_SQRPRE:
      call(mulPreF, pz, px, px)
      ret(Void)
      return
    x = [load(getelementptr(px, i)) for i in range(N)]
    storeN(sqrPre_raw(x, N), pz)
    ret(Void)

# If True then sqr(z, x) is a call to mul(z, x, x) instead of the fused
# sqrPre + Montgomery reduction below. The fused variant needs fewer muls
# (N(N+1)/2 + N^2 + N = 63 vs 2N^2 + N = 78 for N=6) but loses to mul(x, x)
# on both Xeon w9-3495X (26.8/21.9 vs 23.7/19.9 ns latency/throughput,
# BLS12-381-p) and Apple M4 (21.5/14.8 vs 18.7/14.1): sqrPre_raw keeps the
# whole 2N-limb product live when the serial reduction starts, which the
# register file cannot hold, and the saved muls are eaten by spills.
# See memo.md 2026-07-27.
USE_MUL_FOR_SQR = True

# sqr: z = x^2 R^-1 mod p. A call to mul (see USE_MUL_FOR_SQR above), or the
# fused variant: the 2N-unit product of sqrPre_raw stays in one SSA value and
# is reduced in place by mod_raw, so the intermediate never goes through
# memory and the call overhead of a sqrPre + mod pair is gone.
def gen_sqr(name, mont, dataVar, mulUnit, mulF):
  N = mont.pn
  bit = unit * N
  resetGlobalIdx()
  pz = IntPtr(unit)
  px = IntPtr(unit)
  with Function(name, Void, pz, px):
    if USE_MUL_FOR_SQR:
      call(mulF, pz, px, px)
      ret(Void)
      return
    pp = bitcast(dataVar, unit)
    x = [load(getelementptr(px, i)) for i in range(N)]
    xy = sqrPre_raw(x, N)
    lo = trunc(xy, bit)
    z = mod_raw(lo, lambda i: trunc(lshr(xy, bit + i * unit), unit), mont, pp, mulUnit)
    storeN(z, pz)
    ret(Void)

# Fp2 mul: (z.a, z.b) = (a c - b d, a d + b c) where x = (a, b), y = (c, d),
# each component N limbs in Montgomery form, b at offset limbs from a.
# Same Karatsuba structure as gen_fp2_mul of gen_ff_x64.py:
#   s = a + b, t = c + d (no carry out since p is not full bit)
#   d1 = s t, d0 = a c, d2 = b d (3 mulPre calls on alloca buffers)
#   d1 -= d0; d1 -= d2 (= a d + b c; no borrow since s t >= a c + b d)
#   d0 -= d2 (mod p 2^bit: on borrow, add p to the high half; the +p comes
#     from the writable {zero, p} table like gen_sub_raw_tbl, so it lowers
#     to an add chain with memory operands instead of a 2N-limb select)
#   z.a = mod(d0), z.b = mod(d1)
def gen_fp2_mul(name, mont, mulPreF, modF, subTbl, offset):
  N = mont.pn
  bit = unit * N
  bit2 = bit * 2
  resetGlobalIdx()
  pz = IntPtr(unit)
  px = IntPtr(unit)
  py = IntPtr(unit)
  with Function(name, Void, pz, px, py):
    tbl, Npad = subTbl
    ptbl = bitcast(tbl, unit)
    ps = alloca_(unit, N)
    pt = alloca_(unit, N)
    pd0 = alloca_(unit, 2*N)
    pd1 = alloca_(unit, 2*N)
    pd2 = alloca_(unit, 2*N)
    a = loadN(px, N)
    b = loadN(px, N, offset=offset)
    c = loadN(py, N)
    d = loadN(py, N, offset=offset)
    storeN(add(a, b), ps)
    storeN(add(c, d), pt)
    call(mulPreF, pd1, ps, pt)
    call(mulPreF, pd0, px, py)
    call(mulPreF, pd2, getelementptr(px, offset), getelementptr(py, offset))
    d0 = loadN(pd0, 2*N)
    d1 = loadN(pd1, 2*N)
    d2 = loadN(pd2, 2*N)
    d1 = sub(sub(d1, d0), d2)
    storeN(d1, pd1)
    v = sub(d0, d2)
    # borrow flag: d0, d2 < p^2 < 2^(bit2-2), so the top bit is set iff
    # the sub wrapped around
    c = trunc(lshr(v, bit2 - 1), 1)
    off = shl(zext(c, unit), Npad.bit_length() - 1)
    addr = getelementptr(ptbl, off)
    pc = load(bitcast(addr, bit)) # p if borrow else 0
    hi = add(trunc(lshr(v, bit), bit), pc)
    storeN(trunc(v, bit), pd0)
    storeN(hi, pd0, offset=N)
    call(modF, pz, pd0)
    call(modF, getelementptr(pz, offset), pd1)
    ret(Void)

# Fp2 sqr: (z.a, z.b) = (a^2 - b^2, 2 a b) where x = (a, b), b at offset
# limbs from a. Same structure as mcl's gen_fp2_sqr (fp_generator.hpp): two
# calls of the fused Montgomery mul on alloca buffers, no sqrPre (both
# products are cross products, so squaring symmetry cannot be exploited):
#   t1 = 2b, z.b = mul(t1, a) = 2 a b R^(-1)
#   t2 = a + b, t3 = a + p - b (adding p unconditionally avoids a borrow
#     check; p (a + b) vanishes mod p)
#   z.a = mul(t2, t3) = (a^2 - b^2) R^(-1)
# The mul operands are < 2p, so the products are < 4p^2 < p R, which
# requires p < R/4 (the caller checks this nocarry condition). sqr(x, x)
# works in place: when the first mul writes z.b it only reads x.a, which
# does not overlap x.b, and the second mul reads only the t2/t3 copies.
def gen_fp2_sqr(name, mont, mulF, dataVar, offset):
  N = mont.pn
  resetGlobalIdx()
  pz = IntPtr(unit)
  px = IntPtr(unit)
  with Function(name, Void, pz, px):
    pp = bitcast(dataVar, unit)
    pt1 = alloca_(unit, N)
    pt2 = alloca_(unit, N)
    pt3 = alloca_(unit, N)
    a = loadN(px, N)
    b = loadN(px, N, offset=offset)
    p = loadN(pp, N)
    storeN(add(b, b), pt1)
    storeN(add(a, b), pt2)
    storeN(sub(add(a, p), b), pt3)
    call(mulF, getelementptr(pz, offset), pt1, px)
    call(mulF, pz, pt2, pt3)
    ret(Void)

def gen_get_prime(name, pStr):
  resetGlobalIdx()
  r = IntPtr(8, const=True)
  with Function(name, r):
    ret(bitcast(pStr, 8))

def main():
  parser = argparse.ArgumentParser(description='gen bint')
  parser.add_argument('-u', type=int, default=64, help='unit bit size (64 or 32)')
  parser.add_argument('-n', type=int, default=0, help='max size of unit')
  parser.add_argument('-p', type=str, default='', help='characteristic of a finite field')
  parser.add_argument('-type', type=str, default='BLS12-381-p', help='elliptic curve type')
  parser.add_argument('-offset', type=int, default=6, help='sizeof(Fp)/sizeof(Uuit)')
  parser.add_argument('-proto', action='store_true', default=False, help='show prototype')
  parser.add_argument('-pre', type=str, default='mcl_fp_', help='prefix of a Fp function name')
  parser.add_argument('-addn', type=int, default=0, help='mad size of add/sub')
  parser.add_argument('-add', action='store_true', default=False, help='add add function')
  parser.add_argument('-sub', action='store_true', default=False, help='add sub function')
  parser.add_argument('-sub_mask', action='store_true', default=False, help='use an and-mask for the conditional +p in sub instead of the {0,p} table (faster on aarch64)')
  parser.add_argument('-mul', action='store_true', default=False, help='add mul function')
  parser.add_argument('-sqr', action='store_true', default=False, help='add sqr function (a call to mul(z, x, x))')
  parser.add_argument('-mul128', action='store_true', default=False, help='add mul128 (fused Montgomery mul with radix-2^128 q lookahead) function')
  parser.add_argument('-mod', action='store_true', default=False, help='add mod (Montgomery reduction) function')
  parser.add_argument('-mod128', action='store_true', default=False, help='add mod128 (radix-2^128 Montgomery reduction) function')
  parser.add_argument('-mulPre', action='store_true', default=False, help='add mulPre function (z[2N] = x*y, no reduction)')
  parser.add_argument('-mulPreWide', action='store_true', default=False, help='add mulPreWide function (mulPre by a single wide LLVM mul, for bench)')
  parser.add_argument('-sqrPre', action='store_true', default=False, help='add sqrPre function (z[2N] = x^2, no reduction)')
  parser.add_argument('-sqrPreWide', action='store_true', default=False, help='add sqrPreWide function (sqrPre by a single wide LLVM mul, for bench)')
  parser.add_argument('-fp2_mul', action='store_true', default=False, help='add Fp2 mul function (Karatsuba + Montgomery reduction)')
  parser.add_argument('-fp2_sqr', action='store_true', default=False, help='add Fp2 sqr function (2 fused Montgomery mul)')

  opt = parser.parse_args()
  if opt.n == 0:
    opt.n = 9 if opt.u == 64 else 17
    opt.addn = 16 if opt.u == 64 else 32
  # the global holding p gets a per-characteristic name so that modules
  # generated for different p can be linked into one executable
  if opt.p == '':
    opt.p = primeTbl[opt.type].p
    opt.pName = f'mcl_{primeTbl[opt.type].c}_p'
  else:
    opt.p = int(opt.p, 0)
    opt.pName = f'{opt.pre}p'
  opt.pre2 = opt.pre[:-1] + '2_'
  if opt.sqrPre and USE_MULPRE_FOR_SQRPRE:
    opt.mulPre = True
  if opt.fp2_mul:
    opt.mulPre = True
    opt.mod = True
  if opt.fp2_sqr:
    opt.mul = True
  if opt.sqr and USE_MUL_FOR_SQR:
    opt.mul = True

  global mont, unit, unit2
  mont = Montgomery(opt.p, opt.u)
  unit = mont.L
  unit2 = mont.L2
  if opt.proto:
    opt.add = True
    opt.sub = True
    opt.mul = True
    opt.sqr = True
    opt.mod = True
    opt.mulPre = True
    opt.sqrPre = True
    opt.fp2_mul = True
    opt.fp2_sqr = True
    showPrototype()

  dataVar = makeVar(opt.pName, mont.bit, mont.p, const=False, static=False)
  makeVar('ip', unit, mont.ip, const=True, static=True)
  pStr = makeStrVar('pStr', hex(opt.p))

  gen_get_prime(f'{opt.pre}get_prime', pStr)

  subTbl = None
  if (opt.sub and not opt.sub_mask) or opt.fp2_mul:
    subTbl = makeSubTbl(opt.pre, mont)
  if opt.add:
    gen_fp_add(f'{opt.pre}add', mont.pn, dataVar)
    gen_fp2_add(f'{opt.pre2}add', mont.pn, dataVar, opt.offset)
  if opt.sub:
    gen_fp_sub(f'{opt.pre}sub', mont.pn, subTbl, dataVar, opt.sub_mask)
    gen_fp2_sub(f'{opt.pre2}sub', mont.pn, subTbl, dataVar, opt.sub_mask, opt.offset)

  mulUU = gen_mulUU()
  extractHigh = gen_extractHigh()
  mulPos = gen_mulPos(mulUU)
  mulUnit = gen_mulUnit(f'{opt.pre}mulUnit', mont.pn, mulPos, extractHigh)

  mulF = None
  if opt.mul:
    mulF = gen_mul(f'{opt.pre}mul', mont, dataVar, mulUnit)
  if opt.sqr:
    gen_sqr(f'{opt.pre}sqr', mont, dataVar, mulUnit, mulF)
  if opt.mul128 and mont.pn % 2 == 0 and not mont.isFullBit:
    gen_mul128(f'{opt.pre}mul128', mont, dataVar, mulUnit)
  modF = None
  if opt.mod:
    modF = gen_mod(f'{opt.pre}mod', mont, dataVar, mulUnit)
  if opt.mod128 and mont.pn % 2 == 0 and not mont.isFullBit:
    gen_mod128(f'{opt.pre}mod128', mont, dataVar, mulUnit)
  mulPreF = None
  if opt.mulPre:
    mulPreF = gen_mulPre(f'{opt.pre}mulPre', mont.pn, mulUnit)
  if opt.mulPreWide:
    gen_mulPreWide(f'{opt.pre}mulPreWide', mont.pn)
  if opt.sqrPre:
    gen_sqrPre(f'{opt.pre}sqrPre', mont.pn, mulPreF)
  if opt.sqrPreWide:
    gen_sqrPreWide(f'{opt.pre}sqrPreWide', mont.pn)
  if opt.fp2_mul and not mont.isFullBit:
    gen_fp2_mul(f'{opt.pre2}mul', mont, mulPreF, modF, subTbl, opt.offset)
  # p < R/4 so that the fused mul accepts operands < 2p
  nocarry = (mont.p >> (unit * mont.pn - 2)) == 0
  if opt.fp2_sqr and not mont.isFullBit and nocarry:
    gen_fp2_sqr(f'{opt.pre2}sqr', mont, mulF, dataVar, opt.offset)

  term()

if __name__ == '__main__':
  main()
