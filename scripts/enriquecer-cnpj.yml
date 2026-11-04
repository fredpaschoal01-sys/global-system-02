import os, re, json, time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

def env(name, default):
    v = os.getenv(name)
    return v.strip() if v and v.strip() else default

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
MAX_CNPJS = int(env("ENRICH_MAX", "300"))
DELAY = float(env("ENRICH_DELAY", "1.0"))
INCLUIR_SOCIOS = env("INCLUIR_SOCIOS", "sim").lower() in ("sim", "s", "1", "true")
UA = {"User-Agent": "GlobalSystem01/0.1 (public-data research)"}
CAMPOS = ["cnpj", "encontrado", "razao_social", "nome_fantasia", "situacao_cadastral", "data_abertura",
          "porte", "natureza_juridica", "cnae_principal", "atividade_principal", "capital_social",
          "telefone_1", "telefone_2", "email", "logradouro", "numero", "complemento", "bairro", "cep",
          "municipio", "uf", "socios", "consultado_em"]

class Limite(Exception): pass

def sb(method, path, body=None, extra=None):
    h = {"apikey": SERVICE_KEY, "Content-Type": "application/json"}
    if not SERVICE_KEY.startswith("sb_"): h["Authorization"] = "Bearer " + SERVICE_KEY
    h.update(extra or {})
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = Request(SUPABASE_URL + "/rest/v1/" + path, data=data, method=method, headers=h)
    try:
        with urlopen(req, timeout=120) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except HTTPError as e:
        raise RuntimeError(f"Erro Supabase HTTP {e.code}: {e.read(1500).decode('utf-8', 'replace')}")

def listar(path):
    out, off = [], 0
    while True:
        rows = sb("GET", f"{path}&limit=1000&offset={off}") or []
        out += rows
        if len(rows) < 1000: return out
        off += 1000

def consultar(cnpj):
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
    for i in range(4):
        try:
            with urlopen(Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read())
        except HTTPError as e:
            if e.code in (400, 404): return None
            if e.code not in (429, 500, 502, 503, 504): raise
        except URLError: pass
        time.sleep(10 * (i + 1))
    raise Limite()

def digits(v): return re.sub(r"\D", "", str(v or "")) or None
def txt(v):
    v = str(v).strip() if v is not None else ""
    return v or None

def montar(cnpj, d):
    row = dict.fromkeys(CAMPOS)
    row["cnpj"] = cnpj
    row["consultado_em"] = datetime.now(timezone.utc).isoformat()
    if d is None:
        row["encontrado"] = False
        return row
    data = txt(d.get("data_inicio_atividade"))
    cap = d.get("capital_social")
    row.update({
        "encontrado": True,
        "razao_social": txt(d.get("razao_social")),
        "nome_fantasia": txt(d.get("nome_fantasia")),
        "situacao_cadastral": txt(d.get("descricao_situacao_cadastral")),
        "data_abertura": data if data and re.match(r"^\d{4}-\d{2}-\d{2}$", data) else None,
        "porte": txt(d.get("descricao_porte") or d.get("porte")),
        "natureza_juridica": txt(d.get("natureza_juridica")),
        "cnae_principal": txt(d.get("cnae_fiscal")),
        "atividade_principal": txt(d.get("cnae_fiscal_descricao")),
        "capital_social": cap if isinstance(cap, (int, float)) else None,
        "telefone_1": digits(d.get("ddd_telefone_1")),
        "telefone_2": digits(d.get("ddd_telefone_2")),
        "email": (txt(d.get("email")) or "").lower() or None,
        "logradouro": " ".join(filter(None, [txt(d.get("descricao_tipo_de_logradouro")), txt(d.get("logradouro"))])) or None,
        "numero": txt(d.get("numero")), "complemento": txt(d.get("complemento")),
        "bairro": txt(d.get("bairro")), "cep": digits(d.get("cep")),
        "municipio": txt(d.get("municipio")), "uf": txt(d.get("uf")),
        "socios": [{"nome": txt(s.get("nome_socio")), "qualificacao": txt(s.get("qualificacao_socio"))}
                   for s in (d.get("qsa") or [])] if INCLUIR_SOCIOS else None,
    })
    return row

def salvar(rows):
    if rows:
        sb("POST", "empresas?on_conflict=cnpj", rows,
           {"Prefer": "resolution=merge-duplicates,return=minimal"})

def main():
    cnpjs = {r["cnpj"] for r in listar("pgfn_registros?select=cnpj&cnpj=not.is.null&order=cnpj")}
    prontos = {r["cnpj"] for r in listar("empresas?select=cnpj&order=cnpj")}
    faltam = sorted(cnpjs - prontos)
    lote = faltam[:MAX_CNPJS]
    print(f"CNPJs na base: {len(cnpjs)}; já consultados: {len(prontos)}; faltam: {len(faltam)}; nesta execução: {len(lote)}")
    buf, achou, nao = [], 0, 0
    try:
        for i, cnpj in enumerate(lote, 1):
            row = montar(cnpj, consultar(cnpj))
            achou += bool(row["encontrado"]); nao += not row["encontrado"]
            buf.append(row)
            if len(buf) >= 20:
                salvar(buf); buf = []
                print(f"Progresso: {i}/{len(lote)}")
            time.sleep(DELAY)
    except Limite:
        print("Limite/instabilidade da BrasilAPI. Parando; rode de novo mais tarde (continua de onde parou).")
    finally:
        salvar(buf)
    print(f"Concluído. Encontrados: {achou}; não encontrados: {nao}")

if __name__ == "__main__":
    main()
