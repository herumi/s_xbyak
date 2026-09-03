from dataclasses import dataclass

@dataclass(frozen=True)
class Prime:
  p: int  # characteristic
  c: str  # curve tag

primeTbl = {
  'BN254-p' : Prime(p=0x2523648240000001ba344d80000000086121000000000013a700000000000013, c='c0p'),
  'BN254-r' : Prime(p=0x2523648240000001ba344d8000000007ff9f800000000010a10000000000000d, c='c0r'),
  'BN-SNARK-p' : Prime(p=0x30644e72e131a029b85045b68181585d97816a916871ca8d3c208c16d87cfd47, c='c4p'),
  'BN-SNARK-r' : Prime(p=0x30644e72e131a029b85045b68181585d2833e84879b9709143e1f593f0000001, c='c4r'),
  'BLS12-381-p' : Prime(p=0x1a0111ea397fe69a4b1ba7b6434bacd764774b84f38512bf6730d2a0f6b0f6241eabfffeb153ffffb9feffffffffaaab, c='c5p'),
  'BLS12-381-r' : Prime(p=0x73eda753299d7d483339d80809a1d80553bda402fffe5bfeffffffff00000001, c='c5r'),
  'BLS12-377-p' : Prime(p=0x1ae3a4617c510eac63b05c06ca1493b1a22d9f300f5138f1ef3622fba094800170b5d44300000008508c00000000001, c='c8p'),
  'BLS12-377-r' : Prime(p=0x12ab655e9a2ca55660b44d1e5c37b00159aa76fed00000010a11800000000001, c='c8r'),
  'secp256k1-p' : Prime(p=0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f, c='c102p'),
  'secp256k1-r' : Prime(p=0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141, c='c102r'),
  'p511' : Prime(p=0x65b48e8f740f89bffc8ab0d15e3e4c4ab42d083aedc88c425afbfcc69322c9cda7aac6c567f35507516730cc1f0b4f25c2721bf457aca8351b81b90533c6c87b, c='c511p'),
}
