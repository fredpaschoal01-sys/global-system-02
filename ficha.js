// Ficha da empresa: abas (Resumo, Site e redes, Sócios, Mensagem). Carregado depois do app.js.
(function () {
  const CSS = `#rows tr{cursor:pointer}#rows tr:hover td{background:#0f2133}
  .fo{position:fixed;inset:0;background:rgba(3,8,14,.8);display:flex;align-items:flex-start;justify-content:center;overflow:auto;padding:4vh 12px;z-index:50}
  .fi{background:var(--panel);border:1px solid var(--line);border-radius:16px;width:min(860px,100%);padding:20px}
  .fh{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.fh h3{margin:0;font-size:20px}.fh small{color:var(--muted)}
  .ft{display:flex;gap:6px;flex-wrap:wrap;margin:16px 0;border-bottom:1px solid var(--line);padding-bottom:10px}
  .ft button{background:var(--panel2);color:var(--text);border:0;border-radius:8px;padding:9px 12px;font-weight:700;cursor:pointer}
  .ft button.on{background:var(--orange);color:#101b29}
  .fb h4{margin:18px 0 6px;font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:1px}.fb p{margin:4px 0}
  .fb table{min-width:0}.fb textarea{width:100%;min-height:280px;background:#0b1725;color:var(--text);border:1px solid var(--line);border-radius:9px;padding:12px;font:inherit}
  .fr{display:grid;grid-template-columns:1fr 1fr;gap:10px}.fa{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
  .fb a.btn{text-decoration:none;display:inline-block}.fn{color:var(--muted);font-size:12px}
  @media(max-width:700px){.fr{grid-template-columns:1fr}}`;
  const st = document.createElement("style"); st.textContent = CSS; document.head.appendChild(st);

  const E = escapeHtml, D = digits, arr = (v) => (Array.isArray(v) ? v : []);
  const fmtCnpj = (c) => c.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5");
  const fone = (p) => p.length === 11 ? `(${p.slice(0,2)}) ${p.slice(2,7)}-${p.slice(7)}` : p.length === 10 ? `(${p.slice(0,2)}) ${p.slice(2,6)}-${p.slice(6)}` : p;
  const saudacao = () => { const h = new Date().getHours(); return h < 12 ? "Bom dia" : h < 18 ? "Boa tarde" : "Boa noite"; };
  const link = (u, t) => /^https?:\/\//i.test(u) ? `<a class="contact-link" target="_blank" rel="noopener noreferrer" href="${E(u)}">${E(t || u)}</a>` : E(u);
  const google = (q) => "https://www.google.com/search?q=" + encodeURIComponent(q);

  function telefones(b) {
    const out = new Map();
    const add = (t, o) => { let p = D(t); if (p.startsWith("55") && p.length > 11) p = p.slice(2); if (p.length < 10 || p.length > 11 || out.has(p)) return; out.set(p, o); };
    [b.telefone_1, b.telefone_2].forEach((t) => add(t, "cadastro (Receita)"));
    arr(b.site_whatsapp).forEach((t) => add(t, "WhatsApp do site"));
    arr(b.site_telefones).forEach((t) => add(t, "site"));
    return [...out].map(([p, o]) => ({ p, o, movel: p.length === 11 && p[2] === "9" }));
  }

  function modelos(c, nome, empresa) {
    const sd = saudacao(), eu = nome || "[seu nome]", emp = empresa || "[sua empresa]";
    const qtd = c.n === 1 ? "1 inscrição" : `${c.n} inscrições`, v = money(c.total);
    return {
      wa1: `${sd}! Aqui é ${eu}, da ${emp}. Falo com o responsável pela ${c.alvo}?\n\nConsultei a base pública de dívida ativa da PGFN e há ${qtd} em nome da empresa, somando cerca de ${v} (valor registrado na base, sujeito a atualização).\n\nAtuamos desde 2004 com soluções tributárias, como negociação e parcelamento, certidão, CAPAG e regularização de apontamentos. Posso avaliar, sem compromisso, se existe uma saída que faça sentido para vocês.\n\nPosso explicar em 2 minutos por aqui? Se preferir não receber nossas mensagens, é só avisar.`,
      fu: `${sd}! Passando para retomar minha mensagem sobre a situação da ${c.alvo} na PGFN. Sem compromisso: posso enviar um resumo curto do que costuma ser possível nesse tipo de caso, dependendo do enquadramento (parcelamento, negociação, certidão). Faz sentido eu enviar?\n\nSe não for o momento ou se preferir não receber contato, me avise que encerro por aqui.`,
      em: `Olá,\n\nMeu nome é ${eu}, da ${emp}. Escrevo ao responsável pela ${c.alvo} (CNPJ ${fmtCnpj(c.cnpj)}).\n\nAo consultar a base pública de dívida ativa da União (PGFN – Dados Abertos), identificamos ${qtd} em nome da empresa, somando aproximadamente ${v}. Esse é o valor registrado na base e pode ter sido atualizado, pago ou renegociado desde então.\n\nAtuamos desde 2004 com soluções tributárias, como negociação e parcelamento, emissão de certidão, CAPAG e regularização de apontamentos (CADIN, protesto, Serasa/SPC). Cada caso depende do enquadramento, e podemos fazer uma análise inicial sem compromisso.\n\nSe fizer sentido, basta responder este e-mail. Caso não queira receber novos contatos, avise e removeremos seu cadastro.\n\nAtenciosamente,\n${eu}\n${emp}`,
    };
  }

  const abas = {
    resumo(c) {
      const b = c.b, end = [b.logradouro && b.logradouro + (b.numero_endereco ? ", " + b.numero_endereco : ""), b.bairro, b.municipio_empresa && b.municipio_empresa + (b.uf_empresa ? "/" + b.uf_empresa : ""), b.cep].filter(Boolean).join(" - ");
      return `<h4>Empresa</h4><p><strong>${E(c.alvo)}</strong>${b.nome_fantasia ? " · " + E(b.nome_fantasia) : ""}</p>
      <p class="fn">CNPJ ${fmtCnpj(c.cnpj)} · ${E(b.situacao_cadastral || "situação cadastral n/d")} · ${E(b.porte || "porte n/d")}</p>
      <p>${E(b.atividade_principal || "")}</p><p>${E(end || "Endereço não localizado")}</p>
      <h4>Dívida ativa (PGFN)</h4><p><strong>${money(c.total)}</strong> em ${c.n} inscrição(ões) carregada(s)</p>
      <table><tbody>${c.rows.map((r) => `<tr><td>${E(r.natureza || "—")}</td><td>${E(r.situacao || "—")}</td><td>${money(r.valor_divida)}</td><td>${E(r.numero_inscricao || "")}</td></tr>`).join("")}</tbody></table>
      <p class="fn">Valores da base pública, sujeitos a atualização. Confirme a situação atual na fonte oficial antes da abordagem.</p>`;
    },
    site(c) {
      const b = c.b, q = c.alvo + " " + (b.municipio_empresa || "");
      const manual = `<div class="fa"><a class="btn btn-muted" target="_blank" rel="noopener noreferrer" href="${google(q)}">Buscar no Google</a><a class="btn btn-muted" target="_blank" rel="noopener noreferrer" href="${google(q + " instagram")}">Buscar Instagram</a><a class="btn btn-muted" target="_blank" rel="noopener noreferrer" href="${google(q + " facebook")}">Buscar Facebook</a></div>`;
      if (!b.presenca_consultada_em) return `<p>Ainda não pesquisado. Rode o workflow <strong>Pesquisar presença online</strong> em Actions, no GitHub.</p>${manual}`;
      const conf = { alta: "Confirmado: o CNPJ aparece no site", media: "Provável: nome e cidade conferem", baixa: "Conferir manualmente: pode ser outra empresa" }[b.site_confianca] || "";
      const redes = Object.entries(b.redes || {}).map(([k, l]) => `<p><strong>${E(k)}</strong>: ${arr(l).map((x) => link(x.url) + ` <span class="tag">${x.origem === "site" ? "do site" : "sugerida pela busca"}</span>`).join(" · ")}</p>`).join("");
      return `<h4>Site</h4>${b.site_url ? `<p>${link(b.site_url)} <span class="tag">${E(conf)}</span></p><p class="fn">${E(b.site_titulo || "")}</p>` : "<p>Nenhum site localizado.</p>"}
      <h4>Contatos encontrados no site</h4>
      <p>${arr(b.site_whatsapp).map((n) => link("https://wa.me/55" + D(n), "WhatsApp " + fone(D(n)))).join(" · ") || "Sem WhatsApp"}</p>
      <p>${arr(b.site_telefones).map((n) => E(fone(D(n)))).join(" · ") || "Sem telefone"}</p>
      <p>${arr(b.site_emails).map((m) => link("mailto:" + m, m)).join(" · ") || "Sem e-mail"}</p>
      <h4>Redes sociais</h4>${redes || "<p>Nenhuma rede localizada.</p>"}${manual}`;
    },
    socios(c) {
      const l = arr(c.b.socios).slice().sort((a, z) => /administrador/i.test(z.qualificacao || "") - /administrador/i.test(a.qualificacao || ""));
      if (!l.length) return "<p>Sócios não disponíveis para esta empresa.</p>";
      return `<h4>Quadro societário (Receita Federal)</h4>` + l.map((s) => { const q = (s.nome || "") + " " + c.alvo; return `<p><strong>${E(s.nome)}</strong> · ${E(s.qualificacao || "")}</p><div class="fa"><a class="btn btn-muted" target="_blank" rel="noopener noreferrer" href="https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(q)}">Buscar no LinkedIn</a><a class="btn btn-muted" target="_blank" rel="noopener noreferrer" href="${google(q)}">Buscar no Google</a></div>`; }).join("") + `<p class="fn">Dados pessoais públicos. Use apenas para contato profissional relacionado à empresa e respeite pedidos de não contato (LGPD).</p>`;
    },
    msg(c) {
      const tels = telefones(c.b), emails = arr([c.b.email, ...arr(c.b.site_emails)]).filter(Boolean);
      return `<div class="fr"><div><h4>Seu nome</h4><input id="m-nome"></div><div><h4>Sua empresa</h4><input id="m-emp"></div></div>
      <h4>Modelo</h4><select id="m-tipo"><option value="wa1">WhatsApp: 1º contato</option><option value="fu">WhatsApp: retomada (2 a 3 dias depois)</option><option value="em">E-mail</option></select>
      <h4>Mensagem (editável)</h4><textarea id="m-txt"></textarea>
      <h4>Enviar para</h4><select id="m-dest">${tels.map((t) => `<option value="wa:${t.p}">${fone(t.p)} · ${t.movel ? "celular" : "fixo"} · ${E(t.o)}</option>`).join("")}${emails.map((m) => `<option value="em:${E(m)}">${E(m)}</option>`).join("")}</select>
      <div class="fa"><button class="btn btn-outline" id="m-copiar">Copiar</button><button class="btn btn-outline" id="m-abrir">Abrir WhatsApp / E-mail</button></div>
      <p class="fn">O envio é sempre manual: o painel só abre a conversa com o texto pronto. Evite envio em massa (risco de bloqueio) e registre quem pedir para não ser contatado.</p>`;
    },
  };

  function ligarMsg(box, c) {
    const nome = box.querySelector("#m-nome"), emp = box.querySelector("#m-emp"), tipo = box.querySelector("#m-tipo"), txt = box.querySelector("#m-txt"), dest = box.querySelector("#m-dest");
    try { nome.value = localStorage.getItem("gs_nome") || ""; emp.value = localStorage.getItem("gs_emp") || ""; } catch (e) {}
    const gerar = () => { try { localStorage.setItem("gs_nome", nome.value); localStorage.setItem("gs_emp", emp.value); } catch (e) {} txt.value = modelos(c, nome.value.trim(), emp.value.trim())[tipo.value]; };
    [nome, emp, tipo].forEach((el) => el.addEventListener("input", gerar)); gerar();
    box.querySelector("#m-copiar").onclick = () => navigator.clipboard.writeText(txt.value);
    box.querySelector("#m-abrir").onclick = () => {
      const [k, v] = (dest.value || ":").split(/:(.*)/s);
      if (k === "wa") window.open("https://wa.me/55" + v + "?text=" + encodeURIComponent(txt.value), "_blank", "noopener");
      else if (k === "em") window.open("mailto:" + v + "?subject=" + encodeURIComponent("Regularização de débitos na PGFN – " + c.alvo) + "&body=" + encodeURIComponent(txt.value));
      else alert("Nenhum telefone ou e-mail disponível para esta empresa.");
    };
  }

  async function abrir(cnpj) {
    const ov = document.createElement("div"); ov.className = "fo";
    ov.innerHTML = `<div class="fi"><p>Carregando…</p></div>`; document.body.appendChild(ov);
    const fechar = () => { ov.remove(); document.removeEventListener("keydown", esc); }, esc = (e) => e.key === "Escape" && fechar();
    document.addEventListener("keydown", esc); ov.addEventListener("click", (e) => e.target === ov && fechar());
    const fi = ov.firstChild;
    try {
      const { data, error } = await client.from("painel_registros").select("*").eq("cnpj", cnpj).order("valor_divida", { ascending: false });
      if (error) throw error;
      if (!data || !data.length) throw new Error("Registro não encontrado.");
      const c = { b: data[0], rows: data, n: data.length, cnpj, total: data.reduce((s, r) => s + Number(r.valor_divida || 0), 0), alvo: data[0].razao_social || data[0].nome_devedor };
      fi.innerHTML = `<div class="fh"><div><h3>${E(c.alvo)}</h3><small>${fmtCnpj(cnpj)}</small></div><button class="btn btn-muted" id="f-x">Fechar</button></div>
        <div class="ft">${[["resumo", "Resumo"], ["site", "Site e redes"], ["socios", "Sócios"], ["msg", "Mensagem"]].map(([k, t], i) => `<button data-k="${k}" class="${i ? "" : "on"}">${t}</button>`).join("")}</div><div class="fb"></div>`;
      const corpo = fi.querySelector(".fb");
      const mostrar = (k) => { corpo.innerHTML = abas[k](c); if (k === "msg") ligarMsg(corpo, c); fi.querySelectorAll(".ft button").forEach((b) => b.classList.toggle("on", b.dataset.k === k)); };
      fi.querySelectorAll(".ft button").forEach((b) => (b.onclick = () => mostrar(b.dataset.k)));
      fi.querySelector("#f-x").onclick = fechar; mostrar("resumo");
    } catch (err) { fi.innerHTML = `<p>Não foi possível abrir a ficha: ${E(err.message || err)}</p><button class="btn btn-muted" id="f-x">Fechar</button>`; fi.querySelector("#f-x").onclick = fechar; }
  }

  document.getElementById("rows").addEventListener("click", (e) => {
    if (e.target.closest("a,button")) return;
    const tr = e.target.closest("tr"), m = tr && tr.textContent.match(/\d{14}/);
    if (m) abrir(m[0]);
  });
})();
