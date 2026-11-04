import os, re, csv, json, time, zipfile, hashlib, tempfile
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

def env(name, default):
    """Variável vazia (comum em GitHub Actions) vale como não definida."""
    v = os.getenv(name)
    return v.strip() if v and v.strip() else default

INDEX_URL = "https://dadosabertos.pgfn.gov.br/"
BASE_URL = INDEX_URL
SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
MAX_ROWS = int(env("MAX_ROWS", "1000"))
BATCH_SIZE = int(env("BATCH_SIZE", "250"))
# Trecho do nome do ZIP a baixar. Confira o nome real no site da PGFN.
ARQUIVO = env("PGFN_ARQUIVO", "Sistema_SIDA").lower()
DELIMITER = env("CSV_DELIMITER", ";")

def retry(fn, tries=5):
    for i in range(tries):
        try:
            return fn()
        except HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or i == tries - 1: raise
        except URLError:
            if i == tries - 1: raise
        time.sleep(2 ** i * 3)

def get(url):
    req = Request(url, headers={"User-Agent": "GlobalSystem01/0.1 (public-data research)"})
    def go():
        with urlopen(req, timeout=120) as r: return r.read()
    return retry(go)

def download_to_disk(url):
    """Baixa em blocos para arquivo temporário (não carrega o ZIP na memória)."""
    req = Request(url, headers={"User-Agent": "GlobalSystem01/0.1 (public-data research)"})
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    def go():
        tmp.seek(0); tmp.truncate()
        with urlopen(req, timeout=300) as r:
            while True:
                chunk = r.read(1 << 20)
                if not chunk: break
                tmp.write(chunk)
    retry(go); tmp.close()
    return tmp.name

def latest_zip_url():
    html = get(INDEX_URL).decode("utf-8", "replace")
    folders = sorted(set(re.findall(r'href="(20\d{2}_trimestre_0[1-4]/)"', html)))
    if not folders:
        raise RuntimeError("Não foi possível localizar pastas trimestrais no índice oficial PGFN.")
    folder = folders[-1]
    page = get(BASE_URL + folder).decode("utf-8", "replace")
    links = re.findall(r'href="([^"]*\.zip)"', page)
    matches = [l for l in links if ARQUIVO in l.lower()]
    if not matches:
        raise RuntimeError(
            f"Nenhum ZIP contendo '{ARQUIVO}' em {folder}. Arquivos disponíveis: {links}. "
            "Defina a variável PGFN_ARQUIVO com um trecho do nome correto.")
    return BASE_URL + folder + matches[0], folder

def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

def choose(headers, candidates):
    normalized = {norm(h): h for h in headers}
    for c in candidates:
        if norm(c) in normalized: return normalized[norm(c)]
    for key, original in normalized.items():
        if any(norm(c) in key for c in candidates): return original
    return None

def parse_money(value):
    if value is None: return None
    s = str(value).strip().replace("R$", "").replace(" ", "")
    if not s: return None
    if "," in s: s = s.replace(".", "").replace(",", ".")
    try: return round(float(s), 2)
    except ValueError: return None

def parse_date(value):
    """Converte dd/mm/aaaa (padrão PGFN) para aaaa-mm-dd; inválida vira None."""
    s = (value or "").strip()
    if not s: return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try: return datetime.strptime(s[:10], fmt).date().isoformat()
        except ValueError: pass
    return None

def parse_cnpj(row, col):
    raw = re.sub(r"\D", "", str(row.get(col, ""))) if col else ""
    return raw if len(raw) == 14 else None

def post_batch(rows):
    if not rows: return
    # Evita erro "ON CONFLICT ... a second time": uma linha por chave no lote.
    rows = list({r["chave_origem"]: r for r in rows}.values())
    url = SUPABASE_URL + "/rest/v1/pgfn_registros?on_conflict=chave_origem"
    body = json.dumps(rows, ensure_ascii=False).encode("utf-8")
    def go():
        headers = {
            "apikey": SERVICE_KEY,
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal"}
        # Chaves novas (sb_secret_...) não são JWT: só vão em "apikey".
        # Chaves legacy (JWT) também exigem o cabeçalho Authorization.
        if not SERVICE_KEY.startswith("sb_"):
            headers["Authorization"] = "Bearer " + SERVICE_KEY
        req = Request(url, data=body, method="POST", headers=headers)
        try:
            with urlopen(req, timeout=120) as resp:
                if resp.status not in (200, 201, 204):
                    raise RuntimeError(f"Supabase retornou HTTP {resp.status}")
        except HTTPError as e:
            if e.code in (429, 500, 502, 503, 504): raise
            raise RuntimeError(f"Erro Supabase HTTP {e.code}: {e.read(1500).decode('utf-8', 'replace')}")
    retry(go)

def main():
    url, quarter = latest_zip_url()
    print(f"Fonte oficial: {url}")
    print(f"Referência: {quarter}; filtro UF: {UF_FILTER}; limite: {MAX_ROWS or 'sem limite'}")
    path = download_to_disk(url)
    zf = zipfile.ZipFile(path)
    csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    if not csv_names: raise RuntimeError("ZIP oficial não contém CSV.")
    total = sent = 0
    for csv_name in csv_names:
        print("Processando:", csv_name)
        with zf.open(csv_name) as raw:
            text = io_text(raw)
            reader = csv.DictReader(text, delimiter=DELIMITER)
            headers = reader.fieldnames or []
            print("Colunas detectadas:", headers)
            cnpj_col = choose(headers, ["CPF_CNPJ", "CPF/CNPJ", "CNPJ", "NI_DEVEDOR", "NUMERO_DOCUMENTO"])
            name_col = choose(headers, ["NOME_DEVEDOR", "NOME", "DEVEDOR", "NOME_RAZAO_SOCIAL"])
            nature_col = choose(headers, ["TIPO_CREDITO", "NATUREZA", "NATUREZA_DIVIDA", "DESCRICAO_NATUREZA"])
            status_col = choose(headers, ["TIPO_SITUACAO_INSCRICAO", "SITUACAO_INSCRICAO", "SITUACAO"])
            value_col = choose(headers, ["VALOR_CONSOLIDADO", "VALOR_INSCRICAO", "VALOR_TOTAL", "VALOR"])
            type_col = choose(headers, ["TIPO_DEVEDOR"])
            uf_col = choose(headers, ["UF_DEVEDOR", "UF", "UF_UNIDADE"])
            city_col = choose(headers, ["MUNICIPIO", "MUNICIPIO_DEVEDOR"])
            inscr_col = choose(headers, ["NUMERO_INSCRICAO", "INSCRICAO", "NUMERO_CDA"])
            date_col = choose(headers, ["DATA_INSCRICAO", "DATA_INSCRICAO_DIVIDA"])
            if not cnpj_col:
                print("AVISO: coluna de CNPJ não reconhecida. Arquivo não importado; revisar layout.")
                continue
            batch = []
            for line_no, row in enumerate(reader, start=2):
                cnpj = parse_cnpj(row, cnpj_col)
                if not cnpj: continue
                uf = str(row.get(uf_col, "")).strip().upper() if uf_col else None
                if UF_FILTER not in ("ALL", "BR", "BRASIL") and uf and uf != UF_FILTER: continue
                inscr = str(row.get(inscr_col, "")).strip() if inscr_col else f"linha{line_no}"
                identity = "|".join([quarter, csv_name, cnpj, inscr, str(row.get(type_col, ""))])
                batch.append({
                    "chave_origem": hashlib.sha256(identity.encode("utf-8")).hexdigest(),
                    "cnpj": cnpj,
                    "nome_devedor": (row.get(name_col) or "").strip() if name_col else None,
                    "natureza": (row.get(nature_col) or "").strip() if nature_col else None,
                    "situacao": (row.get(status_col) or "").strip() if status_col else None,
                    "valor_divida": parse_money(row.get(value_col)) if value_col else None,
                    "tipo_devedor": (row.get(type_col) or "").strip() if type_col else None,
                    "uf": uf,
                    "municipio": (row.get(city_col) or "").strip() if city_col else None,
                    "numero_inscricao": inscr if inscr_col else None,
                    "data_inscricao": parse_date(row.get(date_col)) if date_col else None,
                    "fonte": "PGFN Dados Abertos",
                    "url_fonte": url,
                    "importado_em": datetime.now(timezone.utc).isoformat(),
                    "dados_originais": row,
                })
                total += 1
                if len(batch) >= BATCH_SIZE:
                    post_batch(batch); sent += len(batch); batch = []
                    if sent % 5000 < BATCH_SIZE: print("Registros enviados:", sent)
                if MAX_ROWS and total >= MAX_ROWS: break
            if batch: post_batch(batch); sent += len(batch)
        if MAX_ROWS and total >= MAX_ROWS: break
    os.unlink(path)
    print(f"Concluído. Registros processados: {total}; enviados/upsert: {sent}")
    if sent == 0:
        raise RuntimeError("Nenhum registro importado. Verifique UF, layout e colunas reconhecidas.")

def io_text(raw):
    import io
    return io.TextIOWrapper(raw, encoding="latin-1", newline="")

if __name__ == "__main__":
    main()
