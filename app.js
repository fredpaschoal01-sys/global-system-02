// Configure com a URL do projeto e a chave anon/public do Supabase.
// Nunca use a chave service_role neste arquivo.
const SUPABASE_URL = "https://gjluwjfcqdkucbncztqg.supabase.co";
const SUPABASE_ANON_KEY = "sb_publishable_QReQLEEm-8xApUS_rF8b1g_6RDstoAb";
const PAGE_SIZE = 25;
let page = 0, allRows = [];

const $ = (id) => document.getElementById(id);
const money = (v) => Number(v || 0).toLocaleString("pt-BR",{style:"currency",currency:"BRL",maximumFractionDigits:2});
const digits = (v) => String(v || "").replace(/\D/g,"");

function setupClient(){
  if(!window.supabase || SUPABASE_URL.includes("_AQUI") || SUPABASE_ANON_KEY.includes("_AQUI")){
    $("connection").textContent = "Configure URL e chave pública do Supabase";
    return null;
  }
  $("connection").textContent = "Conectando ao Supabase";
  return window.supabase.createClient(SUPABASE_URL,SUPABASE_ANON_KEY);
}
const client = setupClient();

async function loadRows(){
  if(!client){$("connection").textContent="Configure o Supabase em app.js.";return;}
  const {data:sessionData}=await client.auth.getSession();
  if(!sessionData.session){$("loginBox").hidden=false;$("appContent").hidden=true;$("connection").textContent="Aguardando login";return;}
  $("loginBox").hidden=true;$("appContent").hidden=false;
  $("connection").textContent = "Carregando dados";
  const {data,error}=await client.from("painel_registros").select("*").order("valor_divida",{ascending:false}).range(0,4999);
  if(error){$("connection").textContent="Erro ao consultar banco";$("rows").innerHTML=`<tr><td colspan="5" class="empty">${escapeHtml(error.message)}</td></tr>`;return;}
  allRows=data||[];
  $("connection").textContent="Conectado";
  $("total").textContent=allRows.length.toLocaleString("pt-BR");
  $("companies").textContent=new Set(allRows.map(x=>x.cnpj).filter(Boolean)).size.toLocaleString("pt-BR");
  $("amount").textContent=money(allRows.reduce((s,x)=>s+Number(x.valor_divida||0),0));
  $("lastUpdate").textContent=allRows.length?new Date(Math.max(...allRows.map(x=>new Date(x.importado_em||0).getTime()))).toLocaleDateString("pt-BR"):"—";
  fillFilters(); render();
}
function fillFilters(){
  const statuses=[...new Set(allRows.map(x=>x.situacao).filter(Boolean))].sort();
  const natures=[...new Set(allRows.map(x=>x.natureza).filter(Boolean))].sort();
  $("status").innerHTML='<option value="">Todas as situações</option>'+statuses.map(x=>`<option>${escapeHtml(x)}</option>`).join("");
  $("nature").innerHTML='<option value="">Todas as naturezas</option>'+natures.map(x=>`<option>${escapeHtml(x)}</option>`).join("");
}
function filtered(){
  const q=$("search").value.toLowerCase().trim();
  return allRows.filter(x=>(!q||[x.nome_devedor,x.razao_social,x.nome_fantasia,x.cnpj].some(v=>String(v||"").toLowerCase().includes(q)))&&(!$("status").value||x.situacao===$("status").value)&&(!$("nature").value||x.natureza===$("nature").value));
}
const fmtPhone=(p)=>p.length===11?`(${p.slice(0,2)}) ${p.slice(2,7)}-${p.slice(7)}`:p.length===10?`(${p.slice(0,2)}) ${p.slice(2,6)}-${p.slice(6)}`:p;
function contactCell(x){
  const parts=[];
  [x.telefone_1,x.telefone_2].forEach(t=>{
    const p=digits(t); if(p.length<10)return;
    const mobile=p.length===11&&p[2]==="9";
    parts.push(`<a class="contact-link" target="_blank" rel="noopener" href="${mobile?"https://wa.me/55"+p:"tel:+55"+p}">${mobile?"WhatsApp ":""}${fmtPhone(p)}</a>`);
  });
  if(x.email)parts.push(`<a class="contact-link" href="mailto:${escapeHtml(x.email)}">${escapeHtml(x.email)}</a>`);
  return parts.length?parts.join("<br>"):"<span class='tag'>Contato não localizado</span>";
}
function companyCell(x){
  const nome=x.razao_social||x.nome_devedor||"Devedor não identificado";
  const fant=x.nome_fantasia?" · "+x.nome_fantasia:"";
  const end=[x.logradouro&&(x.logradouro+(x.numero_endereco?", "+x.numero_endereco:"")),x.bairro,x.municipio_empresa&&(x.municipio_empresa+(x.uf_empresa?"/"+x.uf_empresa:""))].filter(Boolean).join(" - ");
  const so=Array.isArray(x.socios)&&x.socios.length?"Sócios: "+x.socios.slice(0,3).map(s=>s.nome).join(", ")+(x.socios.length>3?` +${x.socios.length-3}`:""):"";
  return `<strong>${escapeHtml(nome)}</strong><small>${escapeHtml(x.cnpj||"CNPJ não disponível")}${escapeHtml(fant)}</small>`+(end?`<small>${escapeHtml(end)}</small>`:"")+(so?`<small>${escapeHtml(so)}</small>`:"");
}
function render(){
  const rows=filtered(), start=page*PAGE_SIZE, slice=rows.slice(start,start+PAGE_SIZE);
  $("count").textContent=`${rows.length.toLocaleString("pt-BR")} registros`;
  $("rows").innerHTML=slice.length?slice.map(x=>`<tr><td>${companyCell(x)}</td><td>${escapeHtml(x.natureza||"Não informado")}</td><td><span class="tag">${escapeHtml(x.situacao||"Não informada")}</span></td><td>${money(x.valor_divida)}</td><td>${contactCell(x)}</td></tr>`).join(""):'<tr><td colspan="5" class="empty">Nenhum registro encontrado com esses filtros.</td></tr>';
  $("prev").disabled=page===0;$("next").disabled=start+PAGE_SIZE>=rows.length;
}
function escapeHtml(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
["search","status","nature"].forEach(id=>$(id).addEventListener(id==="search"?"input":"change",()=>{page=0;render();}));
$("refresh").addEventListener("click",loadRows);
$("clear").addEventListener("click",()=>{$("search").value="";$("status").value="";$("nature").value="";page=0;render();});
$("prev").addEventListener("click",()=>{page=Math.max(0,page-1);render();});
$("next").addEventListener("click",()=>{page++;render();});
loadRows();

$("login").addEventListener("click", async ()=>{
  $("loginError").textContent="";
  if(!client){$("loginError").textContent="Configure primeiro o Supabase em app.js.";return;}
  const {error}=await client.auth.signInWithPassword({email:$("email").value,password:$("password").value});
  if(error){$("loginError").textContent=error.message;return;}
  await loadRows();
});
