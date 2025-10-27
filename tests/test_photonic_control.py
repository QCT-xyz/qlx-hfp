from qlx_hfp_prototype import assemble_hfp
from qlx_photonic_control import photonic_map, make_envelope, sign_envelope_hmac, canonical_json

def test_envelope_lengths_ranges_and_signature():
    hfp = assemble_hfp("seed-env", levels=5)
    params = photonic_map(hfp["band_stats"])
    env = make_envelope(hfp, params, dac_bits=14, sample_rate_GSa=64, quant_mode="nearest")
    signed = sign_envelope_hmac(env, key=b"test-key", key_id="ctrl-01")

    L = signed["band_count"]
    for k in ["I_bias_mA","phi_rad","kappa","tau_ps","delta_f_GHz","alpha"]:
        assert len(signed["params"][k]) == L

    ib = signed["params"]["I_bias_mA"]
    ph = signed["params"]["phi_rad"]
    kp = signed["params"]["kappa"]
    tp = signed["params"]["tau_ps"]
    df = signed["params"]["delta_f_GHz"]
    al = signed["params"]["alpha"]

    assert min(ib) >= 15.0 and max(ib) <= 50.0
    assert min(ph) >= 0.0 and max(ph) <= 3.141592654
    assert min(kp) >= 0.05 and max(kp) <= 0.90
    assert min(tp) >= 50.0 and max(tp) <= 300.0
    assert min(df) >= -10.0 and max(df) <= 10.0
    assert min(al) >= 2.0 and max(al) <= 6.0

    cj = canonical_json(signed)
    assert cj.startswith(b"{")
    assert "signing" in signed and isinstance(signed["signing"]["sig"], str) and len(signed["signing"]["sig"]) == 64
