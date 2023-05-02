# static version of xbyak
# This file provides a xbyak-like DSL to generate a asm code for nasm/yasm/gas .
RAX = 0
RCX = 1
RDX = 2
RBX = 3
RSP = 4
RBP = 5
RSI = 6
RDI = 7
R8 = 8
R9 = 9
R10 = 10
R11 = 11
R12 = 12
R13 = 13
R14 = 14
R15 = 15

g_nasm = False # nasm syntax
g_gas = False # gas syntax
g_masm = False # masm syntax
g_text = []
g_undefLabel = {}
g_defLabelN = 1
g_undefLabelN = 1

def getLine():
  return len(g_text)

T_REG = 0
T_FPU = 1
T_XMM = 2 # contains ymm, zmm
T_MASK = 3 # k1, k2, ...
T_ATTR = 4

# attr
# one of (sae, rn, rd, ru, rz) or zero
T_ZERO = 1
T_SAE = (1<<1)
T_RN =  (2<<1)
T_RD =  (3<<1)
T_RU =  (4<<1)
T_RZ =  (5<<1)

def mergeAttr(attr1, attr2):
  if (attr1>>1) and (attr2>>1):
    raise Exception("can't merge attr", attr1, attr2)
  return attr1 | attr2

class Operand:
  def __init__(self, idx=0, bit=0, kind=T_REG, attr=0):
    self.idx = idx
    self.bit = bit
    self.kind = kind
    self.attr = attr
  def copy(self):
    r = Operand()
    r.idx = self.idx
    r.bit = self.bit
    r.kind = self.kind
    r.attr = self.attr
    if hasattr(self, 'k'):
      r.k = self.k
    return r

  def __str__(self):
    if self.kind == T_REG:
      if self.bit == 64:
        tbl = ['rax', 'rcx', 'rdx', 'rbx', 'rsp', 'rbp', 'rsi', 'rdi', 'r8', 'r9', 'r10',  'r11', 'r12', 'r13', 'r14', 'r15']
      elif self.bit == 32:
        tbl = ['eax', 'ecx', 'edx', 'ebx', 'esp', 'ebp', 'esi', 'edi', 'r8d', 'r9d', 'r10d',  'r11d', 'r12d', 'r13d', 'r14d', 'r15d']
      elif self.bit == 8:
        tbl = ['al', 'cl', 'dl', 'bl', 'ah', 'ch', 'dh', 'bh', 'r8b', 'r9b', 'r10b',  'r11b', 'r12b', 'r13b', 'r14b', 'r15b']
      else:
        raise Exception('bad bit', self.bit)
      s = '%' if g_gas else ''
      return s + tbl[self.idx]

    # xmm4|k3, k1|k2
    s = '%' if g_gas else ''
    if self.kind == T_XMM:
      if self.bit == 128:
        s += 'x'
      elif self.bit == 256:
        s += 'y'
      elif self.bit == 512:
        s += 'z'
      s += f'mm{self.idx}'
    elif self.kind == T_MASK:
      s += f'k{self.idx}'
    elif self.kind == T_ATTR:
      tbl = {
        T_SAE : 'sae',
        T_RN : 'rn-sae',
        T_RD : 'rd-sae',
        T_RU : 'ru-sae',
        T_RZ : 'rz-sae',
      }
      # no % even if g_gas
      # ignore T_z
      s = '{' + tbl[self.attr & ~1] + '}'
      return s
    else:
      raise Exception('bad kind', self.kind)
    if hasattr(self, 'k') and self.k.idx > 0:
      s += f'{{{self.k}}}'
    if (self.attr & T_ZERO) != 0:
      s += '{z}'
    return s

  def __mul__(self, scale):
    if isinstance(scale, int) and scale in [1, 2, 4, 8]:
      return RegExp(None, self, scale)
    raise Exception('bad scale', scale)

  def __add__(self, rhs):
    if isinstance(rhs, int):
      return RegExp(self, None, 1, rhs)
    if isinstance(rhs, RegExp):
      return RegExp(self, rhs.index, rhs.scale, rhs.offset)
    if rhs.kind == T_REG:
      return RegExp(self, rhs)
    raise Exception('bad add type', rhs)

  def __sub__(self, rhs):
    if not isinstance(rhs, int):
      raise Exception('bad sub type', rhs)
    return RegExp(self, None, 1, -rhs)

  def __or__(self, rhs):
    if rhs.kind == T_MASK:
      r = self.copy()
      r.k = rhs
      return r
    elif rhs.kind == T_ATTR:
      r = self.copy()
      r.attr = mergeAttr(r.attr, rhs.attr)
      if hasattr(rhs, 'k'):
        r.k = rhs.k
      return r
    else:
      raise Exception('bad arg', k)

class Reg(Operand):
  def __init__(self, idx, bit):
    super().__init__(idx, bit, T_REG)

class Xmm(Reg):
  def __init__(self, idx, bit):
    super().__init__(idx, bit)
    self.kind = T_XMM

class MaskReg(Reg):
  def __init__(self, idx):
    super().__init__(idx, 64)
    self.kind = T_MASK

class Attribute(Operand):
  def __init__(self, attr):
    super().__init__(0, 0, T_ATTR, attr)

T_z = Attribute(T_ZERO)
T_sae = Attribute(T_SAE)
T_rn_sae = Attribute(T_RN)
T_rd_sae = Attribute(T_RD)
T_ru_sae = Attribute(T_RU)
T_rz_sae = Attribute(T_RZ)


class RegExp:
  def __init__(self, reg, index = None, scale = 1, offset = 0):
    self.base = reg
    self.index = index
    self.scale = scale
    self.offset = offset
  def __add__(self, rhs):
    if type(rhs) == int:
      return RegExp(self.base, self.index, self.scale, self.offset + rhs)
    if type(rhs) == Reg:
      if self.index:
        raise Exception('already index exists', self.index, rhs)
      return RegExp(self.base, rhs.base, rhs.scale, self.offset + rhs.offset)
    raise Exception(f'bad add self={self} rhs={rhs}')
  def __sub__(self, rhs):
    if type(rhs) == int:
      return RegExp(self.base, self.index, self.scale, self.offset - rhs)
    raise Exception(f'bad sub self={self} rhs={rhs}')
  def __str__(self):
    if g_gas:
      s = '('
      if self.offset:
        s = f'{self.offset}('
      if self.base:
        s += str(self.base)
      if self.index:
        s += f',{self.index},{self.scale}'
      return s + ')'
    s = ''
    if self.base:
      s += str(self.base)
    if self.index:
      if s:
        s += '+'
      s += str(self.index)
      if self.scale > 1:
        s += '*' + str(self.scale)
    if self.offset:
      if self.offset > 0:
        s += '+'
      s += str(self.offset)
    return s

class Address:
  def __init__(self, exp=None, bit=0, broadcast=False):
    self.exp = exp
    self.bit = bit
    self.ripLabel = None
    self.broadcast = broadcast
    self.broadcastRate = 0
  def setRip(self, label):
    self.ripLabel = label

  # compute X of {1toX} by bitSize and T_B64, T_B32.
  def setBroadcastRage(self, name, bitSize):
    if name in avx512broadcastTbl:
      self.broadcastRate = bitSize // avx512broadcastTbl[name]
      self.bit = bitSize // self.broadcastRate
  def getBroadcastStr(self):
    if self.broadcast and self.broadcastRate > 0:
      return f'{{1to{self.broadcastRate}}}'
    return ''
  def __str__(self):
    if self.ripLabel:
      if g_gas:
        return f'{self.ripLabel}(%rip)'
      if g_masm:
        return f'offset {self.ripLabel}'
      return f'[rel {self.ripLabel}]'
    if g_gas:
      if type(self.exp) == Reg:
        s = '(' + str(self.exp) + ')'
      else:
        s = str(self.exp)
      s += self.getBroadcastStr()
      return s
    s = '[' + str(self.exp) + ']'
    if g_nasm:
      tbl = { 128 : 'oword', 256 : 'yword', 512 : 'zword' }
      if self.bit > 64:
        s = tbl[self.bit] + ' ' + s
      return s + self.getBroadcastStr()
    # g_masm
    tbl = { 32 : 'd', 64 : 'q', 128 : 'xmm', 256 : 'ymm', 512 : 'zmm' }
    if self.broadcast:
      # To distinguish vcvtpd2dq(xmm0, ptr_b(rax)) and vcvtpd2dq(xmm0, yword_b(rax)) on masm, but that doesn't seem to affect NASM (bug?).
      # https://developercommunity.visualstudio.com/t/ml64exe-cant-deal-with-vcvtpd2dq-xmm0/10352105
      if hasattr(self, 'bitForAddress'):
        s = f'{tbl[self.bitForAddress]}word ptr ' + s
      return f'{tbl[self.bit]}word bcst ' + s
    else:
      if self.bit > 64:
        s = f'{tbl[self.bit]}word ptr ' + s
      return s

def ptr(exp):
  return Address(exp)

def xword(exp):
  return Address(exp, bit=128)

def yword(exp):
  return Address(exp, bit=256)

def zword(exp):
  return Address(exp, bit=512)

def ptr_b(exp):
  return Address(exp, broadcast=True)

def xword_b(exp):
  return Address(exp, bit=128, broadcast=True)

def yword_b(exp):
  return Address(exp, bit=256, broadcast=True)

def zword_b(exp):
  return Address(exp, bit=512, broadcast=True)

def rip(label):
  addr = Address()
  addr.setRip(label)
  return addr

rax = Reg(RAX, 64)
rcx = Reg(RCX, 64)
rdx = Reg(RDX, 64)
rbx = Reg(RBX, 64)
rsp = Reg(RSP, 64)
rbp = Reg(RBP, 64)
rsi = Reg(RSI, 64)
rdi = Reg(RDI, 64)
r8 = Reg(R8, 64)
r9 = Reg(R9, 64)
r10 = Reg(R10, 64)
r11 = Reg(R11, 64)
r12 = Reg(R12, 64)
r13 = Reg(R13, 64)
r14 = Reg(R14, 64)
r15 = Reg(R15, 64)

eax = Reg(RAX, 32)
ecx = Reg(RCX, 32)
edx = Reg(RDX, 32)
ebx = Reg(RBX, 32)
esp = Reg(RSP, 32)
ebp = Reg(RBP, 32)
esi = Reg(RSI, 32)
edi = Reg(RDI, 32)
r8d = Reg(R8, 32)
r9d = Reg(R9, 32)
r10d = Reg(R10, 32)
r11d = Reg(R11, 32)
r12d = Reg(R12, 32)
r13d = Reg(R13, 32)
r14d = Reg(R14, 32)
r15d = Reg(R15, 32)

al = Reg(RAX, 8)
cl = Reg(RCX, 8)
dl = Reg(RDX, 8)
bl = Reg(RBX, 8)
ah = Reg(RSP, 8)
ch = Reg(RBP, 8)
dh = Reg(RSI, 8)
bh = Reg(RDI, 8)
r8d = Reg(R8, 8)
r9d = Reg(R9, 8)
r10b = Reg(R10, 8)
r11b = Reg(R11, 8)
r12b = Reg(R12, 8)
r13b = Reg(R13, 8)
r14b = Reg(R14, 8)
r15b = Reg(R15, 8)

# define xmm, ymm, zmm registers
for (p, bit) in [('x', 128), ('y', 256), ('z', 512)]:
  for idx in range(32):
    globals()[f'{p}mm{idx}'] = Xmm(idx, bit)
    globals()[f'{p}m{idx}'] = Xmm(idx, bit)

# define mask registers k0, ..., k7
for i in range(8):
  globals()[f'k{i}'] = MaskReg(i)

win64ABI = False

def setWin64ABI(win64):
  global win64ABI
  win64ABI = win64

win64Regs = [rcx, rdx, r8, r9, r10, r11, rdi, rsi, rbx, rbp, r12, r13, r14, r15]
linuxRegs = [rdi, rsi, rdx, rcx, r8, r9, r10, r11, rbx, rbp, r12, r13, r14, r15]

def getRegTbl():
  if win64ABI:
    return win64Regs
  else:
    return linuxRegs

def getReg(pos):
  return getRegTbl()[pos]

def getRcxPos():
  return 0 if win64ABI else 3

def getRdxPos():
  return 1 if win64ABI else 2

def getNoSaveNum():
  return 6 if win64ABI else 8

class StackFrame:
  def __init__(self, pNum, tNum = 0, useRDX=False, useRCX=False, stackSizeByte=0, callRet=True):
    self.pos = 0
    self.useRDX = useRDX
    self.useRCX = useRCX
    self.callRet = callRet
    self.p = []
    self.t = []
    allRegNum = pNum + tNum + (1 if useRDX else 0) + (1 if useRCX else 0)
    noSaveNum = getNoSaveNum()
    self.saveNum = max(0, allRegNum - noSaveNum)
    tbl = getRegTbl()[noSaveNum:]
    for i in range(self.saveNum):
      push(tbl[i])
    self.P = (stackSizeByte + 7) // 8
    # 16 byte alignment
    if self.P > 0 and (self.P & 1) == (self.saveNum & 1):
      self.P += 1
    self.P *= 8
    if self.P > 0:
      sub(rsp, self.P)
    for i in range(pNum):
      self.p.append(self.getRegIdx())
    for i in range(tNum):
      self.t.append(self.getRegIdx())
    if self.useRCX and getRcxPos() < pNum:
      mov(r10, rcx)
    if self.useRDX and getRdxPos() < pNum:
      mov(r11, rdx)
  def close(self, callRet=True):
    if self.P > 0:
      add(rsp, self.P)
    noSaveNum = getNoSaveNum()
    tbl = getRegTbl()[noSaveNum:]
    for i in range(self.saveNum-1,-1,-1):
      pop(tbl[i])
    if callRet:
      ret()
  def __enter__(self):
    return self
  def __exit__(self, ex_type, ex_value, trace):
    self.close(self.callRet)

  def getRegIdx(self):
    r = getReg(self.pos)
    self.pos += 1
    if self.useRCX:
      if r == rcx:
        return r10
      if r == r10:
        r = getReg(self.pos)
        self.pos += 1
    if self.useRDX:
      if r == rdx:
        return r11
      if r == r11:
        r = getReg(self.pos)
        self.pos += 1
        return r
    return r

def init(param):
  """
    initialize s_xbyak
    param.win : use Win64 ABI
    param.mode : asm mode (nasm|masm|gas)
  """
  mode = param.mode
  setWin64ABI(param.win)
  global g_nasm, g_gas, g_masm, g_text
  g_nasm = mode == 'nasm'
  g_gas = mode == 'gas'
  g_masm = mode == 'masm'
  g_text = []
  if g_gas:
    output('''# for gas
#ifdef __linux__
  #define PRE(x) x
  #define TYPE(x) .type x, @function
  #define SIZE(x) .size x, .-x
#else
  #ifdef _WIN32
    #define PRE(x) x
  #else
    #define PRE(x) _ ## x
  #endif
  #define TYPE(x)
  #define SIZE(x)
#endif''')
  elif g_masm:
    output('; for masm (ml64.exe)')
  else:
    output('''; for nasm
%imacro _global 1
  %ifdef ADD_UNDERSCORE
    global _%1
    %1:
    _%1:
  %else
    global %1
    %1:
  %endif
%endmacro
''')

def addPRE(s):
  if g_gas:
    return f'PRE({s})'
  else:
    return s

def output(s):
  g_text.append(s)

g_segment_code = False

def segment(mode):
  if g_masm:
    global g_segment_code
    if mode == 'code':
      g_segment_code = True
    if mode == 'text':
      if g_segment_code:
        output(f'_data ends')
        g_segment_code = False
  if g_gas:
    output(f'.{mode}')
  elif g_masm:
    output(f'_{mode} segment')
  else:
    output(f'segment .{mode}')

def db_(s):
  if g_gas:
    output(f'.byte {s}')
  else:
    output(f'db {s}')
def dd_(s):
  if g_gas:
    output(f'.long {s}')
  else:
    output(f'dd {s}')
def dq_(s):
  if g_gas:
    output(f'.quad {s}')
  else:
    output(f'dq {s}')
def global_(s):
  if g_gas:
    output(f'.global PRE({s})')
  if g_masm:
    output(f'public {s}')
  if g_nasm:
    output(f'_global {s}')
def extern_(s, size):
  if g_gas:
    output(f'.extern PRE({s})')
  elif g_masm:
    output(f'extern {s}:{size}')
  else:
    output(f'extern PRE({s})')
def makeLabel(s):
  output(addPRE(s) + ':')
def align(n):
  if g_gas:
    output(f'.align {n}')
  else:
    output(f'align {n}')

def getDefLabel(n):
  if g_gas:
    return f'.L{n}'
  else:
    return f'@L{n}'

def getUndefLabel(n):
  return f'@L{n}_undef'

class Label:
  def __init__(self):
    self.n = 0
  def __str__(self):
    if self.n > 0:
      return getDefLabel(self.n)
    global g_undefLabel
    global g_undefLabelN
    if -self.n in g_undefLabel:
      g_undefLabel[-self.n].append(getLine())
    else:
      self.n = -g_undefLabelN
      g_undefLabelN += 1
      g_undefLabel.setdefault(-self.n, []).append(getLine())
    return getUndefLabel(-self.n)

def L(label):
  if type(label) != Label:
    raise Exception(f'bad type {label}')
  if label.n > 0:
    raise Exception(f'already defined {label}')
  lines = []
  if label.n < 0:
    global g_undefLabelN
    n = -label.n
    if n in g_undefLabel:
      lines = g_undefLabel[n]
      oldStr = getUndefLabel(n)
      del g_undefLabel[n]
  global g_defLabelN
  label.n = g_defLabelN
  g_defLabelN += 1
  if lines:
    newStr = getDefLabel(label.n)
    global g_text
    for line in lines:
      g_text[line] = g_text[line].replace(oldStr, newStr)
  output(f'{getDefLabel(label.n)}:')

def term():
  if g_masm:
    output('_text ends')
    output('end')

  n = len(g_text)
  i = 0
  while i < n:
    s = g_text[i]
    # QQQ (bad knowhow) remove unnecessary pattern
    if g_gas and s == 'mov %rdx, %r11' and g_text[i+1] == 'mov %r11, %rdx':
      i += 2
    elif not g_gas and s == 'mov r11, rdx' and g_text[i+1] == 'mov rdx, r11':
      i += 2
    else:
      print(s)
      i += 1

def defineName(name):
  global_(name)
  makeLabel(name)

# reverse [a, b, c] to [c, b, a] like as Xbyak::util::Pack
def Pack(*args):
  a = list(args)
  a.reverse()
  return a

class FuncProc:
  def __init__(self, name):
    self.name = name
    if g_masm:
      output(f'{self.name} proc export')
      return
    if g_nasm:
      if win64ABI:
        output(f'export {name}')
      global_(name)
      return
    if g_gas:
      global_(name)
      output(f'PRE({name}):')
      output(f'TYPE({self.name})')
      return
  def close(self):
    if g_masm:
      output(f'{self.name} endp')
    if g_gas:
      output(f'SIZE({self.name})')
  def __enter__(self):
    return self
  def __exit__(self, ex_type, ex_value, trace):
    self.close()

def makeVar(name, bit, v, const=False, static=False):
  if not static:
    global_(name)
  makeLabel(name)
  L = 64
  mask = (1<<L)-1
  n = (bit + L-1) // L
  if n == 0:
    n = 1
  if g_gas:
    s = '.quad '
  else:
    s = 'dq '
  for i in range(n):
    if i > 0:
      s += ', '
    s += str(v & mask)
    v >>= L
  output(s)

def getNameSuffix(bit):
  if bit == 128:
    return 'x'
  if bit == 256:
    return 'y'
  if bit == 512:
    return 'z'
  return ''

def genFunc(name):
  def f(*args):
    # special case (mov label, reg)
    if g_gas and name == 'mov' and isinstance(args[1], str):
      output(f'movabs ${args[1]}, {args[0]}')
      return
    if not args:
      return output(name)

    # check max bit size of regs and attributes
    bitSize = 0
    sae = 0
    for arg in args:
      if isinstance(arg, Operand):
        bitSize = max(bitSize, arg.bit)
        if arg.attr > 1:
          sae = arg.attr
      if isinstance(arg, Address):
        bitSize = max(bitSize, arg.bit)

    # mnemonic requiring size for Address
    # bitForAddress is used to detect a suffix of a mnemonic in specialNameTbl for gas and masm
    bitForAddress = 0
    specialNameTbl = ['vcvtpd2dq', 'vcvtpd2ps', 'vcvttpd2dq', 'vcvtqq2ps', 'vcvtuqq2ps', 'vcvtpd2udq', 'vcvttpd2udq', 'vfpclasspd', 'vfpclassps']

    # set bit size to Address
    for arg in args:
      if isinstance(arg, Address):
        if arg.broadcast:
          if g_masm and arg.bit > 128:
            arg.bitForAddress = arg.bit
          arg.setBroadcastRage(name, bitSize)
        elif name in specialNameTbl:
          if arg.bit == 0:
            arg.bit = 128 # default size
          bitForAddress = arg.bit
        if g_masm and arg.bit == 0:
          arg.bit = bitSize

    param = list(args)

    # insert sae at the end of arguments.
    # if the last argument is immediate, insert sae at the front of it.
    # masm requires sae at the end of arguments without a comma.
    if not g_masm and sae > 0:
      if isinstance(args[-1], Operand) and args[-1].kind != T_ATTR:
        param.append(Attribute(sae))
      elif isinstance(args[-1], int):
        param.insert(-1, Attribute(sae))

    s = ''
    if g_gas:
      param.reverse()
    for arg in param:
      if s != '':
        s += ', '
      if g_gas and isinstance(arg, int):
        s += '$' + str(arg)
      else:
        s += str(arg)
    if g_masm and sae > 0:
      s += str(Attribute(sae))

    suffix = ''
    if g_gas and bitForAddress > 0:
      suffix = getNameSuffix(bitForAddress)
    return output(name + suffix + ' ' + s)
  return f

def genAllFunc():
  tbl = [
    'push', 'mov', 'pop', 'jmp', 'test',
    'aaa','aad','aadd','aam','aand','aas','adc','adcx',
    'add','addpd','addps','addsd','addss','addsubpd','addsubps','adox',
    'aesdec','aesdeclast','aesenc','aesenclast','aesimc','aeskeygenassist','and_','andn',
    'andnpd','andnps','andpd','andps','aor','axor','bextr','blendpd',
    'blendps','blendvpd','blendvps','blsi','blsmsk','blsr','bnd','bndcl',
    'bndcn','bndcu','bndldx','bndmk','bndmov','bndstx','bsf','bsr',
    'bswap','bt','btc','btr','bts','bzhi','cbw','cdq',
    'cdqe','char','clc','cld','cldemote','clflush','clflushopt','cli',
    'clui','clwb','clzero','cmc','cmova','cmovae','cmovb','cmovbe',
    'cmovc','cmove','cmovg','cmovge','cmovl','cmovle','cmovna','cmovnae',
    'cmovnb','cmovnbe','cmovnc','cmovne','cmovng','cmovnge','cmovnl','cmovnle',
    'cmovno','cmovnp','cmovns','cmovnz','cmovo','cmovp','cmovpe','cmovpo',
    'cmovs','cmovz','cmp','cmpbexadd','cmpbxadd','cmpeqpd','cmpeqps','cmpeqsd',
    'cmpeqss','cmplepd','cmpleps','cmplesd','cmpless','cmplexadd','cmpltpd','cmpltps',
    'cmpltsd','cmpltss','cmplxadd','cmpnbexadd','cmpnbxadd','cmpneqpd','cmpneqps','cmpneqsd',
    'cmpneqss','cmpnlepd','cmpnleps','cmpnlesd','cmpnless','cmpnlexadd','cmpnltpd','cmpnltps',
    'cmpnltsd','cmpnltss','cmpnlxadd','cmpnoxadd','cmpnpxadd','cmpnsxadd','cmpnzxadd','cmpordpd',
    'cmpordps','cmpordsd','cmpordss','cmpoxadd','cmppd','cmpps','cmppxadd','cmpsb',
    'cmpsd','cmpsq','cmpss','cmpsw','cmpsxadd','cmpunordpd','cmpunordps','cmpunordsd',
    'cmpunordss','cmpxchg','cmpxchg16b','cmpxchg8b','cmpzxadd','comisd','comiss','cpuid',
    'cqo','crc32','cvtdq2pd','cvtdq2ps','cvtpd2dq','cvtpd2pi','cvtpd2ps','cvtpi2pd',
    'cvtpi2ps','cvtps2dq','cvtps2pd','cvtps2pi','cvtsd2si','cvtsd2ss','cvtsi2sd','cvtsi2ss',
    'cvtss2sd','cvtss2si','cvttpd2dq','cvttpd2pi','cvttps2dq','cvttps2pi','cvttsd2si','cvttss2si',
    'cwd','cwde','daa','das','dec','div','divpd','divps',
    'divsd','divss','dppd','dpps','emms','endbr32','endbr64','enter',
    'extractps','f2xm1','fabs','fadd','faddp','fbld','fbstp','fchs',
    'fclex','fcmovb','fcmovbe','fcmove','fcmovnb','fcmovnbe','fcmovne','fcmovnu',
    'fcmovu','fcom','fcomi','fcomip','fcomp','fcompp','fcos','fdecstp',
    'fdiv','fdivp','fdivr','fdivrp','ffree','fiadd','ficom','ficomp',
    'fidiv','fidivr','fild','fimul','fincstp','finit','fist','fistp',
    'fisttp','fisub','fisubr','fld','fld1','fldcw','fldenv','fldl2e',
    'fldl2t','fldlg2','fldln2','fldpi','fldz','fmul','fmulp','fnclex',
    'fninit','fnop','fnsave','fnstcw','fnstenv','fnstsw','fpatan','fprem',
    'fprem1','fptan','frndint','frstor','fsave','fscale','fsin','fsincos',
    'fsqrt','fst','fstcw','fstenv','fstp','fstsw','fsub','fsubp',
    'fsubr','fsubrp','ftst','fucom','fucomi','fucomip','fucomp','fucompp',
    'fwait','fxam','fxch','fxrstor','fxrstor64','fxtract','fyl2x','fyl2xp1',
    'gf2p8affineinvqb','gf2p8affineqb','gf2p8mulb','haddpd','haddps','hlt','hsubpd','hsubps',
    'idiv','imul','in_','inc','insertps','int3','int_','into',
    'ja','jae','jb','jbe','jc','jcxz','je','jecxz',
    'jg','jge','jl','jle','jna','jnae','jnb','jnbe',
    'jnc','jne','jng','jnge','jnl','jnle','jno','jnp',
    'jns','jnz','jo','jp','jpe','jpo','jrcxz','js',
    'jz','kaddb','kaddd','kaddq','kaddw','kandb','kandd','kandnb',
    'kandnd','kandnq','kandnw','kandq','kandw','kmovb','kmovd','kmovq',
    'kmovw','knotb','knotd','knotq','knotw','korb','kord','korq',
    'kortestb','kortestd','kortestq','kortestw','korw','kshiftlb','kshiftld','kshiftlq',
    'kshiftlw','kshiftrb','kshiftrd','kshiftrq','kshiftrw','ktestb','ktestd','ktestq',
    'ktestw','kunpckbw','kunpckdq','kunpckwd','kxnorb','kxnord','kxnorq','kxnorw',
    'kxorb','kxord','kxorq','kxorw','lahf','lddqu','ldmxcsr','lds',
    'ldtilecfg','lea','leave','les','lfence','lfs','lgs','lock',
    'lodsb','lodsd','lodsq','lodsw','loop','loope','loopne','lss',
    'lzcnt','maskmovdqu','maskmovq','maxpd','maxps','maxsd','maxss','mfence',
    'minpd','minps','minsd','minss','monitor','monitorx','movapd','movaps',
    'movbe','movd','movddup','movdir64b','movdiri','movdq2q','movdqa','movdqu',
    'movhlps','movhpd','movhps','movlhps','movlpd','movlps','movmskpd','movmskps',
    'movntdq','movntdqa','movnti','movntpd','movntps','movntq','movq','movq2dq',
    'movsb','movsd','movshdup','movsldup','movsq','movss','movsw','movsx',
    'movsxd','movupd','movups','movzx','mpsadbw','mul','mulpd','mulps',
    'mulsd','mulss','mulx','mwait','mwaitx','neg','not_','or_',
    'orpd','orps','out_','outsb','outsd','outsw','pabsb','pabsd',
    'pabsw','packssdw','packsswb','packusdw','packuswb','paddb','paddd','paddq',
    'paddsb','paddsw','paddusb','paddusw','paddw','palignr','pand','pandn',
    'pause','pavgb','pavgw','pblendvb','pblendw','pclmulhqhdq','pclmulhqlqdq','pclmullqhdq',
    'pclmullqlqdq','pclmulqdq','pcmpeqb','pcmpeqd','pcmpeqq','pcmpeqw','pcmpestri','pcmpestrm',
    'pcmpgtb','pcmpgtd','pcmpgtq','pcmpgtw','pcmpistri','pcmpistrm','pdep','pext',
    'pextrb','pextrd','pextrq','pextrw','phaddd','phaddsw','phaddw','phminposuw',
    'phsubd','phsubsw','phsubw','pinsrb','pinsrd','pinsrq','pinsrw','pmaddubsw',
    'pmaddwd','pmaxsb','pmaxsd','pmaxsw','pmaxub','pmaxud','pmaxuw','pminsb',
    'pminsd','pminsw','pminub','pminud','pminuw','pmovmskb','pmovsxbd','pmovsxbq',
    'pmovsxbw','pmovsxdq','pmovsxwd','pmovsxwq','pmovzxbd','pmovzxbq','pmovzxbw','pmovzxdq',
    'pmovzxwd','pmovzxwq','pmuldq','pmulhrsw','pmulhuw','pmulhw','pmulld','pmullw',
    'pmuludq','popa','popad','popcnt','popf','popfd','popfq','por',
    'prefetchit0','prefetchit1','prefetchnta','prefetcht0','prefetcht1','prefetcht2','prefetchw','prefetchwt1',
    'psadbw','pshufb','pshufd','pshufhw','pshuflw','pshufw','psignb','psignd',
    'psignw','pslld','pslldq','psllq','psllw','psrad','psraw','psrld',
    'psrldq','psrlq','psrlw','psubb','psubd','psubq','psubsb','psubsw',
    'psubusb','psubusw','psubw','ptest','punpckhbw','punpckhdq','punpckhqdq','punpckhwd',
    'punpcklbw','punpckldq','punpcklqdq','punpcklwd','pusha','pushad','pushf','pushfd',
    'pushfq','pxor','rcl','rcpps','rcpss','rcr','rdmsr','rdpmc',
    'rdrand','rdseed','rdtsc','rdtscp','rep','repe','repne','repnz',
    'repz','ret','retf','rol','ror','rorx','roundpd','roundps',
    'roundsd','roundss','rsqrtps','rsqrtss','sahf','sal','sar','sarx',
    'sbb','scasb','scasd','scasq','scasw','senduipi','serialize','seta',
    'setae','setb','setbe','setc','sete','setg','setge','setl',
    'setle','setna','setnae','setnb','setnbe','setnc','setne','setng',
    'setnge','setnl','setnle','setno','setnp','setns','setnz','seto',
    'setp','setpe','setpo','sets','setz','sfence','sha1msg1','sha1msg2',
    'sha1nexte','sha1rnds4','sha256msg1','sha256msg2','sha256rnds2','shl','shld','shlx',
    'shr','shrd','shrx','shufpd','shufps','sqrtpd','sqrtps','sqrtsd',
    'sqrtss','stac','stc','std','sti','stmxcsr','stosb','stosd',
    'stosq','stosw','sttilecfg','stui','sub','subpd','subps','subsd',
    'subss','syscall','sysenter','sysexit','sysret','tdpbf16ps','tdpbssd','tdpbsud',
    'tdpbusd','tdpbuud','tdpfp16ps','testui','tileloadd','tileloaddt1','tilerelease','tilestored',
    'tilezero','tpause','tzcnt','ucomisd','ucomiss','ud2','uiret','umonitor',
    'umwait','unpckhpd','unpckhps','unpcklpd','unpcklps','v4fmaddps','v4fmaddss','v4fnmaddps',
    'v4fnmaddss','vaddpd','vaddph','vaddps','vaddsd','vaddsh','vaddss','vaddsubpd',
    'vaddsubps','vaesdec','vaesdeclast','vaesenc','vaesenclast','vaesimc','vaeskeygenassist','valignd',
    'valignq','vandnpd','vandnps','vandpd','vandps','vbcstnebf162ps','vbcstnesh2ps','vblendmpd',
    'vblendmps','vblendpd','vblendps','vblendvpd','vblendvps','vbroadcastf128','vbroadcastf32x2','vbroadcastf32x4',
    'vbroadcastf32x8','vbroadcastf64x2','vbroadcastf64x4','vbroadcasti128','vbroadcasti32x2','vbroadcasti32x4','vbroadcasti32x8','vbroadcasti64x2',
    'vbroadcasti64x4','vbroadcastsd','vbroadcastss','vcmpeq_ospd','vcmpeq_osps','vcmpeq_ossd','vcmpeq_osss','vcmpeq_uqpd',
    'vcmpeq_uqps','vcmpeq_uqsd','vcmpeq_uqss','vcmpeq_uspd','vcmpeq_usps','vcmpeq_ussd','vcmpeq_usss','vcmpeqpd',
    'vcmpeqps','vcmpeqsd','vcmpeqss','vcmpfalse_ospd','vcmpfalse_osps','vcmpfalse_ossd','vcmpfalse_osss','vcmpfalsepd',
    'vcmpfalseps','vcmpfalsesd','vcmpfalsess','vcmpge_oqpd','vcmpge_oqps','vcmpge_oqsd','vcmpge_oqss','vcmpgepd',
    'vcmpgeps','vcmpgesd','vcmpgess','vcmpgt_oqpd','vcmpgt_oqps','vcmpgt_oqsd','vcmpgt_oqss','vcmpgtpd',
    'vcmpgtps','vcmpgtsd','vcmpgtss','vcmple_oqpd','vcmple_oqps','vcmple_oqsd','vcmple_oqss','vcmplepd',
    'vcmpleps','vcmplesd','vcmpless','vcmplt_oqpd','vcmplt_oqps','vcmplt_oqsd','vcmplt_oqss','vcmpltpd',
    'vcmpltps','vcmpltsd','vcmpltss','vcmpneq_oqpd','vcmpneq_oqps','vcmpneq_oqsd','vcmpneq_oqss','vcmpneq_ospd',
    'vcmpneq_osps','vcmpneq_ossd','vcmpneq_osss','vcmpneq_uspd','vcmpneq_usps','vcmpneq_ussd','vcmpneq_usss','vcmpneqpd',
    'vcmpneqps','vcmpneqsd','vcmpneqss','vcmpnge_uqpd','vcmpnge_uqps','vcmpnge_uqsd','vcmpnge_uqss','vcmpngepd',
    'vcmpngeps','vcmpngesd','vcmpngess','vcmpngt_uqpd','vcmpngt_uqps','vcmpngt_uqsd','vcmpngt_uqss','vcmpngtpd',
    'vcmpngtps','vcmpngtsd','vcmpngtss','vcmpnle_uqpd','vcmpnle_uqps','vcmpnle_uqsd','vcmpnle_uqss','vcmpnlepd',
    'vcmpnleps','vcmpnlesd','vcmpnless','vcmpnlt_uqpd','vcmpnlt_uqps','vcmpnlt_uqsd','vcmpnlt_uqss','vcmpnltpd',
    'vcmpnltps','vcmpnltsd','vcmpnltss','vcmpord_spd','vcmpord_sps','vcmpord_ssd','vcmpord_sss','vcmpordpd',
    'vcmpordps','vcmpordsd','vcmpordss','vcmppd','vcmpph','vcmpps','vcmpsd','vcmpsh',
    'vcmpss','vcmptrue_uspd','vcmptrue_usps','vcmptrue_ussd','vcmptrue_usss','vcmptruepd','vcmptrueps','vcmptruesd',
    'vcmptruess','vcmpunord_spd','vcmpunord_sps','vcmpunord_ssd','vcmpunord_sss','vcmpunordpd','vcmpunordps','vcmpunordsd',
    'vcmpunordss','vcomisd','vcomish','vcomiss','vcompressb','vcompresspd','vcompressps','vcompressw',
    'vcvtdq2pd','vcvtdq2ph','vcvtdq2ps','vcvtne2ps2bf16','vcvtneebf162ps','vcvtneeph2ps','vcvtneobf162ps','vcvtneoph2ps',
    'vcvtneps2bf16','vcvtpd2dq','vcvtpd2ph','vcvtpd2ps','vcvtpd2qq','vcvtpd2udq','vcvtpd2uqq','vcvtph2dq',
    'vcvtph2pd','vcvtph2ps','vcvtph2psx','vcvtph2qq','vcvtph2udq','vcvtph2uqq','vcvtph2uw','vcvtph2w',
    'vcvtps2dq','vcvtps2pd','vcvtps2ph','vcvtps2phx','vcvtps2qq','vcvtps2udq','vcvtps2uqq','vcvtqq2pd',
    'vcvtqq2ph','vcvtqq2ps','vcvtsd2sh','vcvtsd2si','vcvtsd2ss','vcvtsd2usi','vcvtsh2sd','vcvtsh2si',
    'vcvtsh2ss','vcvtsh2usi','vcvtsi2sd','vcvtsi2sh','vcvtsi2ss','vcvtss2sd','vcvtss2sh','vcvtss2si',
    'vcvtss2usi','vcvttpd2dq','vcvttpd2qq','vcvttpd2udq','vcvttpd2uqq','vcvttph2dq','vcvttph2qq','vcvttph2udq',
    'vcvttph2uqq','vcvttph2uw','vcvttph2w','vcvttps2dq','vcvttps2qq','vcvttps2udq','vcvttps2uqq','vcvttsd2si',
    'vcvttsd2usi','vcvttsh2si','vcvttsh2usi','vcvttss2si','vcvttss2usi','vcvtudq2pd','vcvtudq2ph','vcvtudq2ps',
    'vcvtuqq2pd','vcvtuqq2ph','vcvtuqq2ps','vcvtusi2sd','vcvtusi2sh','vcvtusi2ss','vcvtuw2ph','vcvtw2ph',
    'vdbpsadbw','vdivpd','vdivph','vdivps','vdivsd','vdivsh','vdivss','vdpbf16ps',
    'vdppd','vdpps','vexp2pd','vexp2ps','vexpandpd','vexpandps','vextractf128','vextractf32x4',
    'vextractf32x8','vextractf64x2','vextractf64x4','vextracti128','vextracti32x4','vextracti32x8','vextracti64x2','vextracti64x4',
    'vextractps','vfcmaddcph','vfcmulcph','vfixupimmpd','vfixupimmps','vfixupimmsd','vfixupimmss','vfmadd132pd',
    'vfmadd132ph','vfmadd132ps','vfmadd132sd','vfmadd132sh','vfmadd132ss','vfmadd213pd','vfmadd213ph','vfmadd213ps',
    'vfmadd213sd','vfmadd213sh','vfmadd213ss','vfmadd231pd','vfmadd231ph','vfmadd231ps','vfmadd231sd','vfmadd231sh',
    'vfmadd231ss','vfmaddcph','vfmaddsub132pd','vfmaddsub132ph','vfmaddsub132ps','vfmaddsub213pd','vfmaddsub213ph','vfmaddsub213ps',
    'vfmaddsub231pd','vfmaddsub231ph','vfmaddsub231ps','vfmsub132pd','vfmsub132ph','vfmsub132ps','vfmsub132sd','vfmsub132sh',
    'vfmsub132ss','vfmsub213pd','vfmsub213ph','vfmsub213ps','vfmsub213sd','vfmsub213sh','vfmsub213ss','vfmsub231pd',
    'vfmsub231ph','vfmsub231ps','vfmsub231sd','vfmsub231sh','vfmsub231ss','vfmsubadd132pd','vfmsubadd132ph','vfmsubadd132ps',
    'vfmsubadd213pd','vfmsubadd213ph','vfmsubadd213ps','vfmsubadd231pd','vfmsubadd231ph','vfmsubadd231ps','vfmulcph','vfnmadd132pd',
    'vfnmadd132ph','vfnmadd132ps','vfnmadd132sd','vfnmadd132sh','vfnmadd132ss','vfnmadd213pd','vfnmadd213ph','vfnmadd213ps',
    'vfnmadd213sd','vfnmadd213sh','vfnmadd213ss','vfnmadd231pd','vfnmadd231ph','vfnmadd231ps','vfnmadd231sd','vfnmadd231sh',
    'vfnmadd231ss','vfnmsub132pd','vfnmsub132ph','vfnmsub132ps','vfnmsub132sd','vfnmsub132sh','vfnmsub132ss','vfnmsub213pd',
    'vfnmsub213ph','vfnmsub213ps','vfnmsub213sd','vfnmsub213sh','vfnmsub213ss','vfnmsub231pd','vfnmsub231ph','vfnmsub231ps',
    'vfnmsub231sd','vfnmsub231sh','vfnmsub231ss','vfpclasspd','vfpclassph','vfpclassps','vfpclasssd','vfpclasssh',
    'vfpclassss','vgatherdpd','vgatherdps','vgatherpf0dpd','vgatherpf0dps','vgatherpf0qpd','vgatherpf0qps','vgatherpf1dpd',
    'vgatherpf1dps','vgatherpf1qpd','vgatherpf1qps','vgatherqpd','vgatherqps','vgetexppd','vgetexpph','vgetexpps',
    'vgetexpsd','vgetexpsh','vgetexpss','vgetmantpd','vgetmantph','vgetmantps','vgetmantsd','vgetmantsh',
    'vgetmantss','vgf2p8affineinvqb','vgf2p8affineqb','vgf2p8mulb','vhaddpd','vhaddps','vhsubpd','vhsubps',
    'vinsertf128','vinsertf32x4','vinsertf32x8','vinsertf64x2','vinsertf64x4','vinserti128','vinserti32x4','vinserti32x8',
    'vinserti64x2','vinserti64x4','vinsertps','vlddqu','vldmxcsr','vmaskmovdqu','vmaskmovpd','vmaskmovps',
    'vmaxpd','vmaxph','vmaxps','vmaxsd','vmaxsh','vmaxss','vminpd','vminph',
    'vminps','vminsd','vminsh','vminss','vmovapd','vmovaps','vmovd','vmovddup',
    'vmovdqa','vmovdqa32','vmovdqa64','vmovdqu','vmovdqu16','vmovdqu32','vmovdqu64','vmovdqu8',
    'vmovhlps','vmovhpd','vmovhps','vmovlhps','vmovlpd','vmovlps','vmovmskpd','vmovmskps',
    'vmovntdq','vmovntdqa','vmovntpd','vmovntps','vmovq','vmovsd','vmovsh','vmovshdup',
    'vmovsldup','vmovss','vmovupd','vmovups','vmovw','vmpsadbw','vmulpd','vmulph',
    'vmulps','vmulsd','vmulsh','vmulss','vorpd','vorps','vp2intersectd','vp2intersectq',
    'vp4dpwssd','vp4dpwssds','vpabsb','vpabsd','vpabsq','vpabsw','vpackssdw','vpacksswb',
    'vpackusdw','vpackuswb','vpaddb','vpaddd','vpaddq','vpaddsb','vpaddsw','vpaddusb',
    'vpaddusw','vpaddw','vpalignr','vpand','vpandd','vpandn','vpandnd','vpandnq',
    'vpandq','vpavgb','vpavgw','vpblendd','vpblendmb','vpblendmd','vpblendmq','vpblendmw',
    'vpblendvb','vpblendw','vpbroadcastb','vpbroadcastd','vpbroadcastmb2q','vpbroadcastmw2d','vpbroadcastq','vpbroadcastw',
    'vpclmulqdq','vpcmpb','vpcmpd','vpcmpeqb','vpcmpeqd','vpcmpeqq','vpcmpeqw','vpcmpestri',
    'vpcmpestrm','vpcmpgtb','vpcmpgtd','vpcmpgtq','vpcmpgtw','vpcmpistri','vpcmpistrm','vpcmpq',
    'vpcmpub','vpcmpud','vpcmpuq','vpcmpuw','vpcmpw','vpcompressd','vpcompressq','vpconflictd',
    'vpconflictq','vpdpbssd','vpdpbssds','vpdpbsud','vpdpbsuds','vpdpbusd','vpdpbusds','vpdpbuud',
    'vpdpbuuds','vpdpwssd','vpdpwssds','vperm2f128','vperm2i128','vpermb','vpermd','vpermi2b',
    'vpermi2d','vpermi2pd','vpermi2ps','vpermi2q','vpermi2w','vpermilpd','vpermilps','vpermpd',
    'vpermps','vpermq','vpermt2b','vpermt2d','vpermt2pd','vpermt2ps','vpermt2q','vpermt2w',
    'vpermw','vpexpandb','vpexpandd','vpexpandq','vpexpandw','vpextrb','vpextrd','vpextrq',
    'vpextrw','vpgatherdd','vpgatherdq','vpgatherqd','vpgatherqq','vphaddd','vphaddsw','vphaddw',
    'vphminposuw','vphsubd','vphsubsw','vphsubw','vpinsrb','vpinsrd','vpinsrq','vpinsrw',
    'vplzcntd','vplzcntq','vpmadd52huq','vpmadd52luq','vpmaddubsw','vpmaddwd','vpmaskmovd','vpmaskmovq',
    'vpmaxsb','vpmaxsd','vpmaxsq','vpmaxsw','vpmaxub','vpmaxud','vpmaxuq','vpmaxuw',
    'vpminsb','vpminsd','vpminsq','vpminsw','vpminub','vpminud','vpminuq','vpminuw',
    'vpmovb2m','vpmovd2m','vpmovdb','vpmovdw','vpmovm2b','vpmovm2d','vpmovm2q','vpmovm2w',
    'vpmovmskb','vpmovq2m','vpmovqb','vpmovqd','vpmovqw','vpmovsdb','vpmovsdw','vpmovsqb',
    'vpmovsqd','vpmovsqw','vpmovswb','vpmovsxbd','vpmovsxbq','vpmovsxbw','vpmovsxdq','vpmovsxwd',
    'vpmovsxwq','vpmovusdb','vpmovusdw','vpmovusqb','vpmovusqd','vpmovusqw','vpmovuswb','vpmovw2m',
    'vpmovwb','vpmovzxbd','vpmovzxbq','vpmovzxbw','vpmovzxdq','vpmovzxwd','vpmovzxwq','vpmuldq',
    'vpmulhrsw','vpmulhuw','vpmulhw','vpmulld','vpmullq','vpmullw','vpmultishiftqb','vpmuludq',
    'vpopcntb','vpopcntd','vpopcntq','vpopcntw','vpor','vpord','vporq','vprold',
    'vprolq','vprolvd','vprolvq','vprord','vprorq','vprorvd','vprorvq','vpsadbw',
    'vpscatterdd','vpscatterdq','vpscatterqd','vpscatterqq','vpshldd','vpshldq','vpshldvd','vpshldvq',
    'vpshldvw','vpshldw','vpshrdd','vpshrdq','vpshrdvd','vpshrdvq','vpshrdvw','vpshrdw',
    'vpshufb','vpshufbitqmb','vpshufd','vpshufhw','vpshuflw','vpsignb','vpsignd','vpsignw',
    'vpslld','vpslldq','vpsllq','vpsllvd','vpsllvq','vpsllvw','vpsllw','vpsrad',
    'vpsraq','vpsravd','vpsravq','vpsravw','vpsraw','vpsrld','vpsrldq','vpsrlq',
    'vpsrlvd','vpsrlvq','vpsrlvw','vpsrlw','vpsubb','vpsubd','vpsubq','vpsubsb',
    'vpsubsw','vpsubusb','vpsubusw','vpsubw','vpternlogd','vpternlogq','vptest','vptestmb',
    'vptestmd','vptestmq','vptestmw','vptestnmb','vptestnmd','vptestnmq','vptestnmw','vpunpckhbw',
    'vpunpckhdq','vpunpckhqdq','vpunpckhwd','vpunpcklbw','vpunpckldq','vpunpcklqdq','vpunpcklwd','vpxor',
    'vpxord','vpxorq','vrangepd','vrangeps','vrangesd','vrangess','vrcp14pd','vrcp14ps',
    'vrcp14sd','vrcp14ss','vrcp28pd','vrcp28ps','vrcp28sd','vrcp28ss','vrcpph','vrcpps',
    'vrcpsh','vrcpss','vreducepd','vreduceph','vreduceps','vreducesd','vreducesh','vreducess',
    'vrndscalepd','vrndscaleph','vrndscaleps','vrndscalesd','vrndscalesh','vrndscaless','vroundpd','vroundps',
    'vroundsd','vroundss','vrsqrt14pd','vrsqrt14ps','vrsqrt14sd','vrsqrt14ss','vrsqrt28pd','vrsqrt28ps',
    'vrsqrt28sd','vrsqrt28ss','vrsqrtph','vrsqrtps','vrsqrtsh','vrsqrtss','vscalefpd','vscalefph',
    'vscalefps','vscalefsd','vscalefsh','vscalefss','vscatterdpd','vscatterdps','vscatterpf0dpd','vscatterpf0dps',
    'vscatterpf0qpd','vscatterpf0qps','vscatterpf1dpd','vscatterpf1dps','vscatterpf1qpd','vscatterpf1qps','vscatterqpd','vscatterqps',
    'vshuff32x4','vshuff64x2','vshufi32x4','vshufi64x2','vshufpd','vshufps','vsqrtpd','vsqrtph',
    'vsqrtps','vsqrtsd','vsqrtsh','vsqrtss','vstmxcsr','vsubpd','vsubph','vsubps',
    'vsubsd','vsubsh','vsubss','vtestpd','vtestps','vucomisd','vucomish','vucomiss',
    'vunpckhpd','vunpckhps','vunpcklpd','vunpcklps','vxorpd','vxorps','vzeroall','vzeroupper',
    'wait','wbinvd','wrmsr','xadd','xgetbv','xlatb','xor_','xorpd',
    'xorps',
  ]
  for name in tbl:
    asmName = name.strip('_')
    globals()[name] = genFunc(asmName)

genAllFunc()

# used in Address.setBroadcastRage()
T_B16 = 16
T_B32 = 32
T_B64 = 64
avx512broadcastTbl = {
  'vaddpd' : T_B64,
  'vaddps' : T_B32,
  'vandnpd' : T_B64,
  'vandnps' : T_B32,
  'vandpd' : T_B64,
  'vandps' : T_B32,
  'vbcstnebf162ps' : T_B16,
  'vbcstnesh2ps' : T_B16,
  'vcvtdq2pd' : T_B32,
  'vcvtdq2ps' : T_B32,
  'vcvtneps2bf16' : T_B32,
  'vcvtpd2dq' : T_B64,
  'vcvtpd2ps' : T_B64,
  'vcvtps2dq' : T_B32,
  'vcvtps2pd' : T_B32,
  'vcvttpd2dq' : T_B64,
  'vcvttps2dq' : T_B32,
  'vdivpd' : T_B64,
  'vdivps' : T_B32,
  'vfmadd132pd' : T_B64,
  'vfmadd132ps' : T_B32,
  'vfmadd213pd' : T_B64,
  'vfmadd213ps' : T_B32,
  'vfmadd231pd' : T_B64,
  'vfmadd231ps' : T_B32,
  'vfmaddsub132pd' : T_B64,
  'vfmaddsub132ps' : T_B32,
  'vfmaddsub213pd' : T_B64,
  'vfmaddsub213ps' : T_B32,
  'vfmaddsub231pd' : T_B64,
  'vfmaddsub231ps' : T_B32,
  'vfmsub132pd' : T_B64,
  'vfmsub132ps' : T_B32,
  'vfmsub213pd' : T_B64,
  'vfmsub213ps' : T_B32,
  'vfmsub231pd' : T_B64,
  'vfmsub231ps' : T_B32,
  'vfmsubadd132pd' : T_B64,
  'vfmsubadd132ps' : T_B32,
  'vfmsubadd213pd' : T_B64,
  'vfmsubadd213ps' : T_B32,
  'vfmsubadd231pd' : T_B64,
  'vfmsubadd231ps' : T_B32,
  'vfnmadd132pd' : T_B64,
  'vfnmadd132ps' : T_B32,
  'vfnmadd213pd' : T_B64,
  'vfnmadd213ps' : T_B32,
  'vfnmadd231pd' : T_B64,
  'vfnmadd231ps' : T_B32,
  'vfnmsub132pd' : T_B64,
  'vfnmsub132ps' : T_B32,
  'vfnmsub213pd' : T_B64,
  'vfnmsub213ps' : T_B32,
  'vfnmsub231pd' : T_B64,
  'vfnmsub231ps' : T_B32,
  'vgf2p8affineinvqb' : T_B64,
  'vgf2p8affineqb' : T_B64,
  'vmaxpd' : T_B64,
  'vmaxps' : T_B32,
  'vminpd' : T_B64,
  'vminps' : T_B32,
  'vmulpd' : T_B64,
  'vmulps' : T_B32,
  'vorpd' : T_B64,
  'vorps' : T_B32,
  'vpabsd' : T_B32,
  'vpackssdw' : T_B32,
  'vpackusdw' : T_B32,
  'vpaddd' : T_B32,
  'vpaddq' : T_B64,
  'vpdpbusd' : T_B32,
  'vpdpbusds' : T_B32,
  'vpdpwssd' : T_B32,
  'vpdpwssds' : T_B32,
  'vpermd' : T_B32,
  'vpermilpd' : T_B64,
  'vpermilpd' : T_B64,
  'vpermilps' : T_B32,
  'vpermilps' : T_B32,
  'vpermpd' : T_B64,
  'vpermpd' : T_B64,
  'vpermps' : T_B32,
  'vpermq' : T_B64,
  'vpermq' : T_B64,
  'vpmadd52huq' : T_B64,
  'vpmadd52luq' : T_B64,
  'vpmaxsd' : T_B32,
  'vpmaxud' : T_B32,
  'vpminsd' : T_B32,
  'vpminud' : T_B32,
  'vpmuldq' : T_B64,
  'vpmulld' : T_B32,
  'vpmuludq' : T_B64,
  'vpshufd' : T_B32,
  'vpslld' : T_B32,
  'vpsllq' : T_B64,
  'vpsllvd' : T_B32,
  'vpsllvq' : T_B64,
  'vpsrad' : T_B32,
  'vpsravd' : T_B32,
  'vpsrld' : T_B32,
  'vpsrlq' : T_B64,
  'vpsrlvd' : T_B32,
  'vpsrlvq' : T_B64,
  'vpsubd' : T_B32,
  'vpsubq' : T_B64,
  'vpunpckhdq' : T_B32,
  'vpunpckhqdq' : T_B64,
  'vpunpckldq' : T_B32,
  'vpunpcklqdq' : T_B64,
  'vshufpd' : T_B64,
  'vshufps' : T_B32,
  'vsqrtpd' : T_B64,
  'vsqrtps' : T_B32,
  'vsubpd' : T_B64,
  'vsubps' : T_B32,
  'vunpckhpd' : T_B64,
  'vunpckhps' : T_B32,
  'vunpcklpd' : T_B64,
  'vunpcklps' : T_B32,
  'vxorpd' : T_B64,
  'vxorps' : T_B32,
  'vaddph' : T_B16,
  'vblendmpd' : T_B64,
  'vblendmps' : T_B32,
  'vcmppd' : T_B64,
  'vcmpph' : T_B16,
  'vcmpps' : T_B32,
  'vcvtdq2ph' : T_B32,
  'vcvtne2ps2bf16' : T_B32,
  'vcvtpd2ph' : T_B64,
  'vcvtpd2qq' : T_B64,
  'vcvtpd2udq' : T_B64,
  'vcvtpd2uqq' : T_B64,
  'vcvtph2dq' : T_B16,
  'vcvtph2pd' : T_B16,
  'vcvtph2psx' : T_B16,
  'vcvtph2qq' : T_B16,
  'vcvtph2udq' : T_B16,
  'vcvtph2uqq' : T_B16,
  'vcvtph2uw' : T_B16,
  'vcvtph2w' : T_B16,
  'vcvtps2phx' : T_B32,
  'vcvtps2qq' : T_B32,
  'vcvtps2udq' : T_B32,
  'vcvtps2uqq' : T_B32,
  'vcvtqq2pd' : T_B64,
  'vcvtqq2ph' : T_B64,
  'vcvtqq2ps' : T_B64,
  'vcvttpd2qq' : T_B64,
  'vcvttpd2udq' : T_B64,
  'vcvttpd2uqq' : T_B64,
  'vcvttph2dq' : T_B16,
  'vcvttph2qq' : T_B16,
  'vcvttph2udq' : T_B16,
  'vcvttph2uqq' : T_B16,
  'vcvttph2uw' : T_B16,
  'vcvttph2w' : T_B16,
  'vcvttps2qq' : T_B32,
  'vcvttps2udq' : T_B32,
  'vcvttps2uqq' : T_B32,
  'vcvtudq2pd' : T_B32,
  'vcvtudq2ph' : T_B32,
  'vcvtudq2ps' : T_B32,
  'vcvtuqq2pd' : T_B64,
  'vcvtuqq2ph' : T_B64,
  'vcvtuqq2ps' : T_B64,
  'vcvtuw2ph' : T_B16,
  'vcvtw2ph' : T_B16,
  'vdivph' : T_B16,
  'vdpbf16ps' : T_B32,
  'vexp2pd' : T_B64,
  'vexp2ps' : T_B32,
  'vfcmaddcph' : T_B32,
  'vfcmulcph' : T_B32,
  'vfixupimmpd' : T_B64,
  'vfixupimmps' : T_B32,
  'vfmadd132ph' : T_B16,
  'vfmadd213ph' : T_B16,
  'vfmadd231ph' : T_B16,
  'vfmaddcph' : T_B32,
  'vfmaddsub132ph' : T_B16,
  'vfmaddsub213ph' : T_B16,
  'vfmaddsub231ph' : T_B16,
  'vfmsub132ph' : T_B16,
  'vfmsub213ph' : T_B16,
  'vfmsub231ph' : T_B16,
  'vfmsubadd132ph' : T_B16,
  'vfmsubadd213ph' : T_B16,
  'vfmsubadd231ph' : T_B16,
  'vfmulcph' : T_B32,
  'vfnmadd132ph' : T_B16,
  'vfnmadd213ph' : T_B16,
  'vfnmadd231ph' : T_B16,
  'vfnmsub132ph' : T_B16,
  'vfnmsub213ph' : T_B16,
  'vfnmsub231ph' : T_B16,
  'vfpclasspd' : T_B64,
  'vfpclassph' : T_B16,
  'vfpclassps' : T_B32,
  'vgetexppd' : T_B64,
  'vgetexpph' : T_B16,
  'vgetexpps' : T_B32,
  'vgetmantpd' : T_B64,
  'vgetmantph' : T_B16,
  'vgetmantps' : T_B32,
  'vmaxph' : T_B16,
  'vminph' : T_B16,
  'vmulph' : T_B16,
  'vp2intersectd' : T_B32,
  'vp2intersectq' : T_B64,
  'vpabsq' : T_B64,
  'vpandd' : T_B32,
  'vpandnd' : T_B32,
  'vpandnq' : T_B64,
  'vpandq' : T_B64,
  'vpblendmd' : T_B32,
  'vpblendmq' : T_B64,
  'vpcmpd' : T_B32,
  'vpcmpeqd' : T_B32,
  'vpcmpeqq' : T_B64,
  'vpcmpgtd' : T_B32,
  'vpcmpgtq' : T_B64,
  'vpcmpq' : T_B64,
  'vpcmpud' : T_B32,
  'vpcmpuq' : T_B64,
  'vpconflictd' : T_B32,
  'vpconflictq' : T_B64,
  'vpermi2d' : T_B32,
  'vpermi2pd' : T_B64,
  'vpermi2ps' : T_B32,
  'vpermi2q' : T_B64,
  'vpermt2d' : T_B32,
  'vpermt2pd' : T_B64,
  'vpermt2ps' : T_B32,
  'vpermt2q' : T_B64,
  'vplzcntd' : T_B32,
  'vplzcntq' : T_B64,
  'vpmaxsq' : T_B64,
  'vpmaxuq' : T_B64,
  'vpminsq' : T_B64,
  'vpminuq' : T_B64,
  'vpmullq' : T_B64,
  'vpmultishiftqb' : T_B64,
  'vpopcntd' : T_B32,
  'vpopcntq' : T_B64,
  'vpord' : T_B32,
  'vporq' : T_B64,
  'vprold' : T_B32,
  'vprolq' : T_B64,
  'vprolvd' : T_B32,
  'vprolvq' : T_B64,
  'vprord' : T_B32,
  'vprorq' : T_B64,
  'vprorvd' : T_B32,
  'vprorvq' : T_B64,
  'vpshldd' : T_B32,
  'vpshldq' : T_B64,
  'vpshldvd' : T_B32,
  'vpshldvq' : T_B64,
  'vpshrdd' : T_B32,
  'vpshrdq' : T_B64,
  'vpshrdvd' : T_B32,
  'vpshrdvq' : T_B64,
  'vpsraq' : T_B64,
  'vpsravq' : T_B64,
  'vpternlogd' : T_B32,
  'vpternlogq' : T_B64,
  'vptestmd' : T_B32,
  'vptestmq' : T_B64,
  'vptestnmd' : T_B32,
  'vptestnmq' : T_B64,
  'vpxord' : T_B32,
  'vpxorq' : T_B64,
  'vrangepd' : T_B64,
  'vrangeps' : T_B32,
  'vrcp14pd' : T_B64,
  'vrcp14ps' : T_B32,
  'vrcp28pd' : T_B64,
  'vrcp28ps' : T_B32,
  'vrcpph' : T_B16,
  'vreducepd' : T_B64,
  'vreduceph' : T_B16,
  'vreduceps' : T_B32,
  'vrndscalepd' : T_B64,
  'vrndscaleph' : T_B16,
  'vrndscaleps' : T_B32,
  'vrsqrt14pd' : T_B64,
  'vrsqrt14ps' : T_B32,
  'vrsqrt28pd' : T_B64,
  'vrsqrt28ps' : T_B32,
  'vrsqrtph' : T_B16,
  'vscalefpd' : T_B64,
  'vscalefph' : T_B16,
  'vscalefps' : T_B32,
  'vshuff32x4' : T_B32,
  'vshuff64x2' : T_B64,
  'vshufi32x4' : T_B32,
  'vshufi64x2' : T_B64,
  'vsqrtph' : T_B16,
  'vsubph' : T_B16,
}

import argparse
def getDefaultParser(description='s_xbyak'):
  parser = argparse.ArgumentParser(description=description)
  parser.add_argument('-win', '--win', help='Win64 ABI(default:Amd64 ABI)', action='store_true')
  parser.add_argument('-m', '--mode', help='asm mode(nasm|masm|gas)', default='nasm')
  return parser
