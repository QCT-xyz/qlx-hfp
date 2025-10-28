import os, json, requests
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

API_BASE = os.environ.get("API_BASE", "").rstrip("/")
if not API_BASE:
    raise RuntimeError("Set API_BASE to your QLX API base URL, e.g. https://...run.app")

app = FastAPI(title="QLX UI Proxy", version="0.1")
templates = Jinja2Templates(directory="ui-proxy/templates")

def _get_id_token(audience: str) -> str:
    # 1) Prefer Cloud Run metadata (in-prod)
    md_url = f"http://metadata/computeMetadata/v1/instance/service-accounts/default/identity?audience={audience}"
    try:
        r = requests.get(md_url, headers={"Metadata-Flavor": "Google"}, timeout=3)
        if r.ok and r.text:
            return r.text.strip()
    except Exception:
        pass
    # 2) Fallback to ADC (local dev) via google-auth if present
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.id_token import fetch_id_token
        return fetch_id_token(Request(), audience)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not mint id_token: {e}")

def _call_api(path: str, payload: dict):
    aud = API_BASE
    tok = _get_id_token(aud)
    r = requests.post(f"{API_BASE}{path}",
                      headers={"Authorization": f"Bearer {tok}",
                               "Content-Type": "application/json"},
                      data=json.dumps(payload), timeout=30)
    if not r.ok:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "api_base": API_BASE})

@app.post("/call/hfp")
def call_hfp(seed: str = Form("qlx-demo-seed-phi369"), levels: int = Form(5)):
    return JSONResponse(_call_api("/hfp", {"seed": seed, "levels": levels}))

@app.post("/call/sts")
def call_sts(seed: str = Form("qlx-demo-seed-phi369"), n_bits: int = Form(200000), whiten: str = Form("sha512")):
    return JSONResponse(_call_api("/sts", {"seed": seed, "n_bits": n_bits, "whiten": whiten}))

@app.post("/call/envelope")
def call_envelope(seed: str = Form("qlx-demo-seed-phi369"), levels: int = Form(5),
                  dac_bits: int = Form(14), sample_gsa: int = Form(64), quant: str = Form("nearest")):
    return JSONResponse(_call_api("/envelope", {
        "seed": seed, "levels": levels, "dac_bits": dac_bits, "sample_gsa": sample_gsa, "quant": quant
    }))
