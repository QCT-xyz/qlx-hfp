import pytest
from qlx_hfp_prototype import assemble_hfp, derive_key_from_hfp, derive_key_scrypt
try:
    from qlx_hfp_prototype import derive_key_argon2id, HAVE_ARGON2
except Exception:
    HAVE_ARGON2 = False

def test_kdf_lengths_and_stability():
    seed = "qlx-demo-seed-phi369"
    pw = b"demo-password"
    h = assemble_hfp(seed, levels=5)

    k1 = derive_key_from_hfp(pw, h["fingerprint_hash"], key_len=32)
    k1b = derive_key_from_hfp(pw, h["fingerprint_hash"], key_len=32)
    assert len(k1) == 32 and k1 == k1b

    k2 = derive_key_scrypt(pw, h["fingerprint_hash"], key_len=32)
    k2b = derive_key_scrypt(pw, h["fingerprint_hash"], key_len=32)
    assert len(k2) == 32 and k2 == k2b

    if HAVE_ARGON2:
        k3 = derive_key_argon2id(pw, h["fingerprint_hash"], key_len=32)
        k3b = derive_key_argon2id(pw, h["fingerprint_hash"], key_len=32)
        assert len(k3) == 32 and k3 == k3b
        # Different KDFs should not collide
        assert k1 != k2 and k1 != k3 and k2 != k3
