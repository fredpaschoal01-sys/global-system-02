import os, re, json, time, html
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

def env(name, default):
    v = os.getenv(name)
    return v.strip() if v and v.strip() else default

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
SERPER_KEY = os.environ["SERPER_API_KEY"]
MAX_EMPRESAS = int(env("PESQUISA_MAX", "40"))
DELAY = float(env("PESQUISA_DELAY", "1.0"))
UA_NAME = "GlobalSystem01"
UA = {"User-Agent": UA_NAME + "/0.1 (pesquisa de dados publicos; contato do dono no repositorio)"}

BLOQ = ["cnpj.biz", "casadosdados.com.br", "econodata.com.br", "cnpja.com", "cnpj.info", "empresascnpj.com",
        "consultasocio.com", "linkedin.com", "facebook.com", "instagram.com", "tiktok.com", "youtube.com",
        "twitter.com", "x.com", "jusbrasil.com.br", "serasa.com.br", "serasaexperian.com.br", "reclameaqui.com.br",
        "glassdoor.com.br", "indeed.com", "apontador.com.br", "telelistas.net", "guiamais.com.br",
        "solutudo.com.br", "cylex.com.br", "wikipedia.org", "mercadolivre.com.br", "google.com", "gov.br",
        "olx.com.br", "escavador.com", "transparencia.gov.br", "informecadastral.com.br", "cnpjs.rocks"]
REDES = {
    "instagram": r"https?://(?:www\.)?instagram\.com/[A-Za-z0-9_.]+/?",
    "facebook": r"https?://(?:www\.)?facebook\.com/[A-Za-z0-9_.\-]+/?",
    "tiktok": r"https?://(?:www\.)?tiktok\.com/@[A-Za-z0-9_.]+",
    "linkedin": r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/company/[A-Za-z0-9_\-%]+/?",
    "youtube": r"https?://(?:www\.)?youtube\.com/(?:@|channel/|c/|user/)[A-Za-z0-9_\-.]+",
}
IGNORAR = {"p", "explore", "sharer", "sharer.php", "share", "tr", "plugins", "dialog", "reel", "reels",
           "stories", "tags", "hashtag", "login", "policies", "legal", "watch", "embed", "privacy", "help"}
STOP = {"ltda", "eireli", "epp", "me", "sa", "s/a", "comercio", "industria", "servicos", "de", "da", "do", "dos",
        "das", "e", "participacoes", "empreendimentos", "grupo", "brasil", "brasileira", "sociedade", "simples"}
PHONE_RE = re.compile(r"(?<![\d/.\-])\(?\b(\d{2})\)?[\s.\-]*(9?\d{4})[\s.\-]?(\d{4})(?![\d/])")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

class Parar(Exception): pass

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

def serper(q):
    body = json.dumps({"q": q, "gl": "br", "hl": "pt-br", "num": 8}).encode("utf-8")
    for i in range(3):
        req = Request("https://google.serper.dev/search", data=body, method="POST",
                      headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=60) as r:
                return json.loads(r.read()).get("organic", [])
        except HTTPError as e:
            msg = e.read(500).decode("utf-8", "replace")
            if e.code in (429, 500, 502, 503, 504) and i < 2:
                time.sleep(5 * (i + 1)); continue
            raise Parar(f"Serper recusou (HTTP {e.code}): {msg}. Confira a chave SERPER_API_KEY e os créditos.")
        except URLError:
            time.sleep(5)
    raise Parar("Serper indisponível.")

def host(url):
    return (urlparse(url).netloc or "").lower().split(":")[0].removeprefix("www.")

def bloqueado(h):
    return any(h == d or h.endswith("." + d) for d in BLOQ)

def pode_acessar(url):
    try:
        p = urlparse(url)
        with urlopen(Request(f"{p.scheme}://{p.netloc}/robots.txt", headers=UA), timeout=10) as r:
            txt = r.read(200000).decode("utf-8", "replace")
        rp = RobotFileParser(); rp.parse(txt.splitlines())
        return rp.can_fetch(UA_NAME, url)
    except Exception:
        return True

def baixar(url):
    if not pode_acessar(url): return None
    try:
        with urlopen(Request(url, headers=UA), timeout=20) as r:
            if "html" not in (r.headers.get("Content-Type") or "").lower(): return None
            raw = r.read(600000)
            cs = r.headers.get_content_charset() or "utf-8"
        try: return raw.decode(cs, "replace")
        except LookupError: return raw.decode("utf-8", "replace")
    except Exception:
        return None

def digitos(v): return re.sub(r"\D", "", str(v or ""))

def norm_fone(p):
    p = digitos(p)
    if len(p) in (12, 13) and p.startswith("55"): p = p[2:]
    if len(p) not in (10, 11) or not (11 <= int(p[:2]) <= 99): return None
    if len(p) == 11 and p[2] != "9": return None
    return p

def extrair(htm, base_url):
    limpo = re.sub(r"<script.*?</script>|<style.*?</style>", " ", htm, flags=re.S | re.I)
    texto = html.unescape(re.sub(r"<[^>]+>", " ", limpo))
    bruto = html.unescape(htm)
    emails = {e.lower() for e in EMAIL_RE.findall(bruto)
              if not re.search(r"\.(png|jpe?g|gif|svg|webp|css|js)$|sentry|wixpress|example|seuemail|dominio", e.lower())}
    wa = {n for n in (norm_fone(x) for x in re.findall(r"(?:wa\.me/|phone=)\+?(\d{10,13})", bruto)) if n}
    tels = {n for n in (norm_fone(x) for x in re.findall(r'href=["\']tel:([^"\']+)', bruto)) if n}
    for m in PHONE_RE.finditer(texto):
        n = norm_fone("".join(m.groups()))
        if n: tels.add(n)
    tels -= wa
    redes = {}
    for rede, rx in REDES.items():
        for u in re.findall(rx, bruto):
            seg = urlparse(u).path.strip("/").split("/")[0].lower()
            if seg in IGNORAR: continue
            lst = redes.setdefault(rede, [])
            if u.rstrip("/") not in [x["url"].rstrip("/") for x in lst] and len(lst) < 2:
                lst.append({"url": u, "origem": "site"})
    titulo = re.search(r"<title[^>]*>(.*?)</title>", htm, re.S | re.I)
    cont = None
    for h in re.findall(r'href=["\']([^"\']*(?:contato|contact|fale-conosco|fale_conosco)[^"\']*)["\']', htm, re.I):
        u = urljoin(base_url, h)
        if host(u) == host(base_url) and u.startswith("http"): cont = u; break
    return {"texto": texto, "emails": sorted(emails)[:6], "whatsapp": sorted(wa)[:4],
            "telefones": sorted(tels)[:6], "redes": redes,
            "titulo": html.unescape(titulo.group(1)).strip()[:200] if titulo else None, "contato": cont}

def tokens(nome):
    sem = re.sub(r"[^a-z0-9 ]", " ", (nome or "").lower())
    return [t for t in sem.split() if len(t) > 3 and t not in STOP]

def confianca(texto, e):
    cnpj = e["cnpj"]
    fmt = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    if fmt in texto or cnpj in texto: return "alta"
    t = texto.lower()
    tk = tokens(e.get("razao_social"))
    nome_ok = (e.get("nome_fantasia") and e["nome_fantasia"].lower() in t) or \
              (len(tk) >= 2 and sum(x in t for x in tk) >= 2) or (len(tk) == 1 and tk[0] in t)
    local_ok = (e.get("municipio") and e["municipio"].lower() in t) or (e.get("cep") and e["cep"] in digitos(texto))
    return "media" if nome_ok and local_ok else "baixa"

ORDEM = {"alta": 3, "media": 2, "baixa": 1}

def pesquisar(e):
    nome = e.get("razao_social") or ""
    row = {"cnpj": e["cnpj"], "site_url": None, "site_titulo": None, "site_confianca": None,
           "telefones": None, "emails": None, "whatsapp": None, "redes": None,
           "consultado_em": datetime.now(timezone.utc).isoformat()}
    local = " ".join(filter(None, [e.get("municipio"), e.get("uf")]))
    res = serper(f'"{nome}" {local}')
    melhor, vistos = None, set()
    for r in res:
        h = host(r.get("link", ""))
        if not h or bloqueado(h) or h in vistos or r.get("link", "").lower().endswith(".pdf"): continue
        vistos.add(h)
        if len(vistos) > 3: break
        p = urlparse(r["link"]); raiz = f"{p.scheme}://{p.netloc}/"
        pag = baixar(raiz)
        if not pag: continue
        d = extrair(pag, raiz)
        c = confianca(d["texto"], e)
        if not melhor or ORDEM[c] > ORDEM[melhor[1]]: melhor = (raiz, c, d)
        if c == "alta": break
    redes = {}
    if melhor and melhor[1] != "baixa":
        raiz, c, d = melhor
        if not (d["emails"] or d["telefones"] or d["whatsapp"]) and d["contato"]:
            pag2 = baixar(d["contato"])
            if pag2:
                d2 = extrair(pag2, d["contato"])
                for k in ("emails", "telefones", "whatsapp"):
                    d[k] = sorted(set(d[k]) | set(d2[k]))[:6]
                for k, v in d2["redes"].items(): d["redes"].setdefault(k, v)
        row.update({"site_url": raiz, "site_titulo": d["titulo"], "site_confianca": c,
                    "telefones": d["telefones"], "emails": d["emails"], "whatsapp": d["whatsapp"]})
        redes = d["redes"]
    elif melhor:
        row.update({"site_url": melhor[0], "site_titulo": melhor[2]["titulo"], "site_confianca": "baixa"})
    if not redes:
        time.sleep(DELAY)
        tk = tokens(nome) + tokens(e.get("nome_fantasia"))
        for r in serper(f'{e.get("nome_fantasia") or nome} {local} instagram facebook'):
            alvo = (r.get("link", "") + " " + r.get("title", "") + " " + r.get("snippet", "")).lower()
            if not any(t in alvo for t in tk): continue
            for rede, rx in REDES.items():
                m = re.match(rx, r.get("link", ""))
                if m and urlparse(m.group(0)).path.strip("/").split("/")[0].lower() not in IGNORAR:
                    lst = redes.setdefault(rede, [])
                    if len(lst) < 2 and m.group(0) not in [x["url"] for x in lst]:
                        lst.append({"url": m.group(0), "origem": "busca"})
    row["redes"] = redes or None
    return row

def salvar(rows):
    if rows:
        sb("POST", "presenca_online?on_conflict=cnpj", rows, {"Prefer": "resolution=merge-duplicates,return=minimal"})

def main():
    empresas = listar("empresas?select=cnpj,razao_social,nome_fantasia,municipio,uf,cep&encontrado=eq.true"
                      "&situacao_cadastral=ilike.ATIVA&order=cnpj")
    prontos = {r["cnpj"] for r in listar("presenca_online?select=cnpj&order=cnpj")}
    faltam = [e for e in empresas if e["cnpj"] not in prontos and e.get("razao_social")]
    lote = faltam[:MAX_EMPRESAS]
    print(f"Empresas ativas: {len(empresas)}; já pesquisadas: {len(prontos)}; faltam: {len(faltam)}; nesta execução: {len(lote)}")
    buf, com_site = [], 0
    try:
        for i, e in enumerate(lote, 1):
            try:
                row = pesquisar(e)
            except Parar:
                raise
            except Exception as ex:
                print(f"Falha em {e['cnpj']}: {ex}"); continue
            com_site += bool(row["site_url"])
            buf.append(row)
            if len(buf) >= 10: salvar(buf); buf = []
            print(f"{i}/{len(lote)} {e['cnpj']}: site={row['site_url']} ({row['site_confianca']})")
            time.sleep(DELAY)
    except Parar as p:
        print("PARADO:", p)
    finally:
        salvar(buf)
    print(f"Concluído. Com site: {com_site} de {len(lote)}")

if __name__ == "__main__":
    main()
