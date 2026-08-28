import argparse
import os
import re

# Update the MemRegTbl/RegMemTbl in ../s_xbyak.py from a text file
# converted from an Intel SDM vol.2 pdf by pdftotext (see update.sh).
# usage: python3 update.py <sdm-all.txt> [-debug]
# -debug : save the intermediate files (sdm.txt, avx.txt, tbl.py)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(BASE_DIR, '..', 's_xbyak.py')
MARKER = '# BEGIN auto-generated table by gen/update.py. Do not edit below this line.\n'

### step 1 : cut out the instruction reference pages (AAA ... XTEST)

# 'Order Number: 325383-092US' on the title page
RE_SDM_VERSION = re.compile(r'Order Number:\s*(\d+-\d+)US')

def getSdmVersion(allText):
  m = RE_SDM_VERSION.search(allText)
  if not m:
    raise Exception('SDM version (Order Number) not found')
  return m.group(1)

def detectRange(pages):
  start = end = None
  for i, page in enumerate(pages):
    if start is None and page.startswith('AAA'):
      start = i
    if 'XTEST' in page and 'Test if in Transactional Execution' in page:
      end = i
  if start is None:
    raise Exception('start page (AAA) not found')
  if end is None or end < start:
    raise Exception('end page (XTEST) not found')
  return (start, end)

def cutPages(allText):
  # pdftotext separates pages with a form feed
  pages = allText.split('\f')
  (start, end) = detectRange(pages)
  print(f'pages {start+1}-{end+1} of {len(pages)}')
  # pdftotext appends a form feed to every page including the last one
  return ''.join(page + '\f' for page in pages[start:end+1])

### step 2 : extract instruction forms such as "vaddps xmm1,xmm2,xmm3/m128"

ARGS_TBL=['<XMM0-2>', '<XMM0-6>', '<XMM0>',
  'AL', 'CL', 'AX', 'DX', 'EAX', 'ECX', 'EDX', 'RAX', 'RDX',
  'ST(i)',
  'imm',
  'k1', 'k2',
  'm8', 'm16', 'm32', 'm64', 'm128', 'm256', 'm512',
  'mm',
  'r8', 'r16', 'r32', 'r64',
  'r/m32', 'r/m64',
  'xmm', 'ymm', 'zmm',
  'vm32', 'vm64',
  '{k1}', '{sae}', '{er}',
  '{k2}',
  '.m256', # miss of SDM (VPAND ymm1, ymm2, ymm3/.m256)
]

BAD_ARGS_TBL=[
  'immediately', 'from', 'to', 'sign',
]

def validArg(s):
  for t in BAD_ARGS_TBL:
    if s.startswith(t):
      return False
  for t in ARGS_TBL:
    if s.startswith(t):
      return True
  return False

def matchArg(s):
  if s in ['0', '1', '2', '3', '4', '5', '6', '7']:
    return True
  v = s.split(' ')
  for e in v:
    if not validArg(e.strip()):
      return False
  return True

def parseArgs(args):
  r = []
  for p in args.split(','):
    p = p.strip().strip('*')
    if matchArg(p):
      r.append(p)
    else:
      return []
  return r

ALNUM = re.compile('[A-Z][A-Z0-9]+$')
def matchOp(op):
  if not ALNUM.match(op):
    return False
  if op in ['XMM', 'YMM', 'ZMM', 'IF', 'THEN', 'INPUT', 'S1']:
    return False
  return True

def extract(sdmText):
  text = sdmText.split('\n')
  r = []
  for i in range(len(text)):
    line = text[i]
    if line == '':
      continue
    op = line.split(' ')[0]
    if not matchOp(op):
      continue
    v = line[len(op)+1:]
    if v == '':
      continue
    if v[-1] == ',':
      v += text[i+1]
    args = parseArgs(v)
    if args == []:
      continue
    s = op + ' ' + ','.join(args)
    r.append(s.lower())
  return r

### step 3 : build MemRegTbl/RegMemTbl from the instruction forms

RE_MEM = re.compile(r'(m32|m64|m128|m256|m512)')
RE_XMM = re.compile(r'(xmm|ymm|zmm)')

def parse(arg):
  m = RE_MEM.search(arg)
  if m:
    return m.group(1)
  m = RE_XMM.search(arg)
  if m:
    return m.group(1)
  arg = arg.strip()
  if arg == 'imm8' or '01234567'.find(arg) >= 0:
    return 'imm'
  if arg.startswith('k1'):
    return 'k'
  return None

def makeTable(lines):
  # op reg, [m]
  RegMemTbl = {}
  # op [m], reg, ...
  MemRegTbl = {}

  for line in lines:
    if line == '':
      break
    op = line.split(' ')[0]
    v = line[len(op):].split(',')
    args = []
    for p in v:
      x = parse(p)
      if not x:
        break
      args.append(x)
    if len(args) < len(v):
      continue

    if args[0][0] == 'm':
      tbl = MemRegTbl
    else:
      tbl = RegMemTbl
    tbl.setdefault(op, set()).add(tuple(args))

  cmpTbl = ['eq', 'lt', 'le', 'unord', 'neq', 'nlt', 'nle', 'ord',
    'eq_uq', 'nge', 'ngt', 'false', 'neq_oq', 'ge', 'gt', 'true',
    'eq_os', 'lt_oq', 'le_oq', 'unord_s', 'neq_us', 'nlt_uq', 'nle_uq', 'ord_s',
    'eq_us', 'nge_uq', 'ngt_uq', 'false_os', 'neq_os', 'ge_oq', 'gt_oq', 'true_us'
  ]
  cmpArgSet = {('k', 'xmm', 'm128'),
              ('k', 'ymm', 'm256'),
              ('k', 'zmm', 'm512'),
              ('xmm', 'xmm', 'm128'),
              ('ymm', 'ymm', 'm256')}

  for suf in ['pd', 'ps']:
    for pred in cmpTbl:
      op = f'vcmp{pred}{suf}'
      RegMemTbl.setdefault(op, cmpArgSet)

  vpclmulArgSet = {('xmm', 'xmm', 'm128'),
                  ('ymm', 'ymm', 'm256'),
                  ('zmm', 'zmm', 'm512')}
  HLtbl = ['h', 'l']
  for a in HLtbl:
    for b in HLtbl:
      op = f'vpclmul{a}q{b}qdq'
      RegMemTbl.setdefault(op, vpclmulArgSet)

  return (MemRegTbl, RegMemTbl)

# pprint does not sort set elements, so the output would change on each run
# by hash randomization. Dump the tables in a deterministic format instead.
def dumpTbl(name, tbl):
  s = f'{name}={{\n'
  for op in sorted(tbl.keys()):
    args = ', '.join(map(str, sorted(tbl[op])))
    s += f" '{op}': {{{args}}},\n"
  s += '}\n'
  return s

### step 4 : replace the auto-generated table part of ../s_xbyak.py
# The table part begins at MARKER and continues to the end of the file.

def updateTarget(tblText, sdmVersion):
  lines = open(TARGET).readlines()
  if MARKER not in lines:
    raise Exception(f'marker not found in {TARGET}')
  # set SDM_VERSION just after the VERSION line
  for i, line in enumerate(lines):
    if line.startswith('VERSION='):
      v = f'SDM_VERSION="{sdmVersion}"\n'
      if i+1 < len(lines) and lines[i+1].startswith('SDM_VERSION='):
        lines[i+1] = v
      else:
        lines.insert(i+1, v)
      break
  else:
    raise Exception(f'VERSION line not found in {TARGET}')
  pos = lines.index(MARKER)
  with open(TARGET, 'w') as f:
    f.writelines(lines[:pos+1])
    f.write(tblText)
  print(f'{TARGET} updated (SDM {sdmVersion})')

def main():
  parser = argparse.ArgumentParser(description='update the tables in s_xbyak.py from a text converted from an Intel SDM vol.2 pdf')
  parser.add_argument('txt', help='text file converted from an SDM vol.2 pdf by pdftotext')
  parser.add_argument('-debug', action='store_true', help='save the intermediate files')
  param = parser.parse_args()

  def save(name, s):
    if param.debug:
      with open(os.path.join(BASE_DIR, name), 'w') as f:
        f.write(s)

  allText = open(param.txt).read()
  sdmVersion = getSdmVersion(allText)
  sdmText = cutPages(allText)
  save('sdm.txt', sdmText)
  lines = extract(sdmText)
  save('avx.txt', '\n'.join(lines) + '\n')
  (MemRegTbl, RegMemTbl) = makeTable(lines)
  tblText = dumpTbl('MemRegTbl', MemRegTbl) + dumpTbl('RegMemTbl', RegMemTbl)
  save('tbl.py', tblText)
  updateTarget(tblText, sdmVersion)

if __name__ == '__main__':
  main()
