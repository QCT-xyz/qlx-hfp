from qlx_hfp_prototype import assemble_hfp, derive_key_from_hfp

def test_hfp_repro_and_sensitivity():
    seed = "qlx-demo-seed-phi369"
    h1 = assemble_hfp(seed, levels=5)
    h2 = assemble_hfp(seed, levels=5)
    assert h1["fingerprint_hash"] == h2["fingerprint_hash"]
    h3 = assemble_hfp(seed + "-delta", levels=5)
    assert h3["fingerprint_hash"] != h1["fingerprint_hash"]

def test_kdf_length():
    h = assemble_hfp("seed-for-kdf", levels=5)
    key = derive_key_from_hfp(b"demo-password", h["fingerprint_hash"], key_len=32)
    assert isinstance(key, (bytes, bytearray)) and len(key) == 32
