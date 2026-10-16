import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timezone
from urllib.parse import quote

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field

router = APIRouter()
SESSION_TTL = 12 * 60 * 60
REPO = "rsever-source/mobilrs"
BRANCH = "cloud-run-migration"
RAW = "https://raw.githubusercontent.com/" + REPO + "/" + BRANCH + "/"
API = "https://api.github.com/repos/" + REPO
LIVE_NEWS = os.environ.get("LIVE_NEWS_URL", "https://mobilrs-test-ltiv3pox5q-ew.a.run.app/api/news")


def _admin_password():
    return os.environ.get("ADMIN_PASSWORD", "")


def _session_signature(expiry, nonce):
    secret = _admin_password()
    if not secret:
        return ""
    payload = expiry + "." + nonce
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def _cookie_session(request):
    token = request.cookies.get("eng_admin_session", "")
    try:
        expiry, nonce, signature = token.split(".", 2)
        if int(expiry) < int(time.time()) or len(nonce) > 128:
            return False
        expected = _session_signature(expiry, nonce)
        return bool(expected) and hmac.compare_digest(signature, expected)
    except (ValueError, TypeError):
        return False


def _require_session(request):
    if not _cookie_session(request):
        raise HTTPException(401, "Oturum açılması gerekiyor.")
    return True


def _set_session(response):
    expiry = str(int(time.time()) + SESSION_TTL)
    nonce = secrets.token_urlsafe(24)
    signature = _session_signature(expiry, nonce)
    response.set_cookie(
        "eng_admin_session", expiry + "." + nonce + "." + signature,
        max_age=SESSION_TTL, httponly=True, secure=True, samesite="strict", path="/admin"
    )


def _clear_session(response):
    response.delete_cookie("eng_admin_session", path="/admin", secure=True, httponly=True, samesite="strict")


def _origin_guard(request):
    origin = request.headers.get("origin", "").rstrip("/")
    host = request.headers.get("host", "").split(":", 1)[0].lower()
    # Accept the production domain and same-origin requests to a Cloud Run
    # tagged URL used for safe testing. Never trust an unrelated Origin.
    allowed_host = host == "engelli.me" or host.endswith(".a.run.app")
    if not allowed_host or origin != "https://" + host:
        raise HTTPException(403, "İstek kaynağı doğrulanamadı.")


def _json_from_raw(path):
    response = requests.get(RAW + path, timeout=(4, 12), headers={"Cache-Control": "no-cache"})
    response.raise_for_status()
    return response.json()


class PasswordLogin(BaseModel):
    password: str = Field(min_length=1, max_length=256)


LOGIN_HTML = r'''<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive"><title>Engelli.me yönetim girişi</title>
<style nonce="{nonce}">
*{{box-sizing:border-box}}body{{margin:0;background:#f3f6fa;color:#172033;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;min-height:100vh;display:grid;place-items:center;padding:20px}}
main{{width:min(100%,420px);background:white;border:1px solid #e1e7ef;border-radius:20px;padding:26px;box-shadow:0 12px 36px #15223a12}}
h1{{font-size:22px;margin:0 0 8px}}p{{color:#647084;font-size:14px;line-height:1.5}}label{{display:block;font-weight:650;font-size:14px;margin:18px 0 7px}}
input,button{{width:100%;padding:13px 14px;border-radius:10px;font:inherit}}input{{border:1px solid #cbd4e1}}button{{border:0;background:#155eef;color:white;font-weight:700;margin-top:12px;cursor:pointer}}#msg{{min-height:22px;color:#a32020;font-size:13px}}.brand{{font-weight:850;color:#155eef;margin-bottom:22px}}.brand span{{color:#172033}}
</style></head><body><main><div class="brand">Engelli<span>.me</span></div><h1>Haber raporu</h1>
<p>Bu alan yalnızca yetkili yönetici içindir.</p>
<form id="passwordForm"><label for="password">Yönetici parolası</label><input id="password" type="password" autocomplete="current-password" required maxlength="256"><button type="submit">Giriş yap</button></form>
<p id="msg" role="status"></p></main>
<script nonce="{nonce}">
const msg=document.getElementById('msg');
document.getElementById('passwordForm').addEventListener('submit',async e=>{{e.preventDefault();msg.textContent='';try{{const r=await fetch('/admin/api/login/password',{{method:'POST',credentials:'same-origin',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{password:document.getElementById('password').value}})}});const j=await r.json().catch(()=>({{}}));if(!r.ok)throw Error(j.detail||'Giriş başarısız');location.href='/admin/haber-durumu'}}catch(err){{msg.textContent=err.message}}}});
</script></body></html>'''

DASHBOARD_HTML = r'''<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive"><title>Engelli.me haber durumu</title>
<style nonce="{nonce}">
*{{box-sizing:border-box}}body{{margin:0;background:#f3f6fa;color:#172033;font-family:system-ui,-apple-system,"Segoe UI",sans-serif}}main{{max-width:1180px;margin:auto;padding:20px}}
header{{display:flex;gap:14px;align-items:center;justify-content:space-between;flex-wrap:wrap;margin-bottom:20px}}h1{{font-size:24px;margin:0}}.muted{{color:#657187;font-size:13px}}button,input{{font:inherit;border-radius:10px;padding:10px 13px}}button{{border:0;background:#155eef;color:white;font-weight:700;cursor:pointer}}button.secondary{{background:#e8eef8;color:#1c355d}}.cards{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}}.card,section{{background:#fff;border:1px solid #e1e7ef;border-radius:14px;padding:16px;min-width:0}}.report-summary-cards{{grid-template-columns:repeat(4,minmax(0,1fr))}}.report-summary-cards .card{{min-height:104px}}.report-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:14px;align-items:stretch}}.report-grid section{{margin-top:0}}.report-grid #pendingNewsSection,.report-grid #sourceErrorsSection{{grid-column:1/-1}}.report-grid #systemErrorsSection{{min-width:0;min-height:104px;overflow:auto}}.card small{{display:block;color:#657187}}.card strong{{display:block;font-size:21px;margin-top:7px;overflow-wrap:anywhere}}section{{margin-top:14px}}h2{{font-size:17px;margin:0 0 12px}}.status{{font-weight:750}}.good{{color:#16803c}}.bad{{color:#b42318}}.warn{{color:#9a6700}}.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{padding:9px;border-bottom:1px solid #e8edf3;text-align:left;vertical-align:top}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;background:#f7f9fc;padding:12px;border-radius:8px;max-height:560px;overflow:auto}}.row{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}}input[type=search]{{border:1px solid #cbd4e1;min-width:200px;flex:1}}details{{border-bottom:1px solid #e8edf3;padding:10px 0}}summary{{cursor:pointer;font-weight:650}}.report-item{{border-bottom:1px solid #e8edf3;padding:12px 0}}.report-item:last-child{{border-bottom:0}}h3{{font-size:14px;margin:14px 0 8px}}a{{color:#155eef;overflow-wrap:anywhere}}.pill{{display:inline-block;padding:3px 8px;border-radius:999px;background:#edf2f8;font-size:12px}}#message{{min-height:18px;margin:8px 0;color:#526174;font-size:13px}}@media(max-width:760px){{main{{padding:14px}}.cards{{grid-template-columns:repeat(2,minmax(0,1fr))}}.report-summary-cards{{grid-template-columns:repeat(2,minmax(0,1fr))}}.grid2{{grid-template-columns:1fr}}.report-grid{{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}}.report-grid section{{padding:12px}}h1{{font-size:20px}}}}
</style></head><body><main>
<header><div><div class="muted">Engelli.me / Özel yönetim</div><h1>Haber sistemi durum raporu</h1><div class="muted" id="lastChecked">Henüz kontrol edilmedi</div></div><div class="row"><button id="refresh">Güncelle</button><button class="secondary" id="logout">Çıkış</button></div></header>
<p id="message" role="status">Mevcut kayıtlar yükleniyor…</p>
<div class="cards">
<div class="card"><small>Son tarama adayı</small><strong id="candidateCount">—</strong><div class="muted">Son kayıtlı tarama</div></div>
<div class="card"><small>Workflow hatası</small><strong id="workflowErrorStatus">Kontrol yok</strong></div>
</div>
<section><h2>Haber işlem özeti</h2><div class="cards report-summary-cards">
<div class="card"><small>Yayımlanan</small><strong id="published">—</strong></div>
<div class="card"><small>Tekrar / daha önce işlenmiş</small><strong id="duplicates">—</strong></div>
<div class="card"><small>Filtreyle elenen</small><strong id="rejected">—</strong></div>
<div class="card"><small>Kararı netleşmeyen aday</small><strong id="pending">—</strong></div>
<div class="card"><small>Gemini red</small><strong id="geminiRejectedCount">0</strong></div>
<div class="card"><small>Gemini tekrar</small><strong id="geminiDuplicatesCount">0</strong></div>
<div class="card" id="systemErrorsCard" hidden><small>Haber işleme sorunları</small><strong id="systemErrorsCount">0</strong></div>
</div><p class="muted">Bu sayılar son taramanın kayıtlarından hesaplanır.</p></section>
<div class="report-grid">
<section id="pendingNewsSection"><h2>Bekleyen haberler</h2><div id="pendingNews" class="muted">Yükleniyor…</div></section>
<section id="sourceErrorsSection"><h2>Haber kaynaklarına erişim ve okuma sorunları</h2><div id="sourceErrors" class="muted"></div></section>
<section id="systemErrorsSection" hidden><h2>Haber işleme sorunları (Gemini ve diğer işlemler)</h2><div id="systemErrors" class="muted"></div></section>
</div>

</main>
<script nonce="{nonce}">
let state=null;
function el(id){{return document.getElementById(id)}}
function safeText(v){{return v===null||v===undefined?'—':String(v)}}
function node(tag,text,cls){{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n}}
function counts(log){{const last=(log.news_runs||[]).slice(-1)[0]||{{}};const out={{published:0,duplicates:0,rejected:0,pending:0}};for(const c of (last.candidates||[])){{const s=String(c.status||'').toLowerCase(),d=String(c.decision||'').toLowerCase();if(s==='published'||c.publish===true||d==='publish')out.published++;else if(c.duplicate===true||d==='duplicate'||s.includes('duplicate'))out.duplicates++;else if(d==='reject'||c.publish===false||s==='rejected')out.rejected++;else out.pending++}}const f=last.filter_diagnostics?.counts||{{}};out.duplicates=Math.max(out.duplicates,Number(f.duplicate_in_this_run||0)+Number(f.url_seen_within_7_days||0)+Number(f.already_published||0));out.rejected=Math.max(out.rejected,Number(f.older_than_7_days||0)+Number(f.missing_date||0)+Number(f.future_date||0));out.pending=Math.max(out.pending,Number(f.pending_unknown_or_expired_date||0));return out}}
function render(data){{state=data;const log=data.log||{{}};const runs=log.news_runs||[];const last=runs[runs.length-1]||{{}};const cs=counts(log);
 const checkedAt=data.checked_at?new Date(data.checked_at):null;
 const localCheckedAt=checkedAt&&!Number.isNaN(checkedAt.getTime())
  ?new Intl.DateTimeFormat('tr-TR',{timeZone:'Europe/Istanbul',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).format(checkedAt)+' (Türkiye saati)'
  :safeText(data.checked_at);
 el('lastChecked').textContent='Kontrol zamanı: '+localCheckedAt;
 el('candidateCount').textContent=safeText(last.candidates?.length??last.filter_diagnostics?.counts?.accepted_as_candidate);
 renderWorkflowError(log);
 el('published').textContent=cs.published;el('duplicates').textContent=cs.duplicates;el('rejected').textContent=cs.rejected;el('pending').textContent=cs.pending;
 renderPendingNews(data.news_pending||[],log);
 renderGeminiDecisions(log);
 renderErrors(data);
}}
function renderWorkflowError(log){{
 const statusEl=el('workflowErrorStatus');
 if(!Array.isArray(log.system_incidents)){{
  statusEl.textContent='Kontrol yok';
  statusEl.className='warn';
  return;
 }}
 const active=(log.system_incidents||[]).filter(item=>{{
  const component=String(item.component||'');
  return item.status!=='resolved'&&(component.startsWith('workflow:')||component==='news-workflow-stale');
 }});
 if(active.some(item=>item.component==='news-workflow-stale')){{
  statusEl.textContent='Akış durdu';
  statusEl.className='bad';
 }}else if(active.length){{
  statusEl.textContent='Hata var';
  statusEl.className='bad';
 }}else{{
  statusEl.textContent='Hata yok';
  statusEl.className='good';
 }}
}}
function renderGeminiDecisions(log){{
 const rejected=[];const duplicates=[];const seenRejected=new Set();const seenDuplicates=new Set();
 const runs=log.news_runs||[];
 const latestRun=runs.length?runs[runs.length-1]:null;
 for(const c of (latestRun?.candidates||[])){{
  const decision=String(c.decision||'').toLowerCase();
  const status=String(c.status||'').toLowerCase();
  const isDuplicate=c.duplicate===true||decision==='duplicate'||status.includes('duplicate');
  const isRejected=!isDuplicate&&(decision==='reject'||status==='rejected');
  if(!isDuplicate&&!isRejected)continue;
  const key=String(c.url||c.title||'')+'|'+(isDuplicate?'duplicate':'reject');
  const target=isDuplicate?duplicates:rejected;const seen=isDuplicate?seenDuplicates:seenRejected;
  if(seen.has(key))continue;seen.add(key);target.push(key);
 }}
 el('geminiRejectedCount').textContent=String(rejected.length);
 el('geminiDuplicatesCount').textContent=String(duplicates.length);
}}
function pendingAttemptInfo(item,log){{
 const attempts=[];
 for(const run of (log.news_runs||[])){{
  for(const candidate of (run.candidates||[])){{
   if(candidate.url===item.url&&candidate.status==='not_processed')attempts.push({{run_at:run.run_at,error:candidate.error}});
  }}
 }}
 const latest=attempts[attempts.length-1];
 if(attempts.length>1)return {{label:'Tekrar başarısız oldu',detail:'Yeniden denendi; raporda '+attempts.length+' başarısız deneme kayıtlı.'+(latest?.run_at?' Son deneme: '+latest.run_at:''),count:attempts.length}};
 if(attempts.length===1)return {{label:'Bekliyor',detail:'İlk deneme başarısız oldu; yeniden denenmesi bekleniyor.'+(latest?.run_at?' Son deneme: '+latest.run_at:''),count:1}};
 return {{label:'Bekliyor',detail:'Deneme geçmişi raporda bulunamadı; yeniden deneme sonucu doğrulanamıyor.',count:0}};
}}
function renderPendingNews(items,log){{
 const root=el('pendingNews');root.replaceChildren();
 if(!items.length){{root.appendChild(node('div','Bekleyen haber yok. Başarıyla işlenen haberler bu listeden otomatik kaldırılır.','muted'));return}}
 for(const item of items){{
  const wrap=node('div',undefined,'report-item');
  wrap.appendChild(node('strong',item.title||'Başlıksız haber'));
  const info=pendingAttemptInfo(item,log);
  wrap.appendChild(node('div',info.label,info.count>1?'status bad':'status warn'));
  wrap.appendChild(node('div',info.detail,'muted'));
  if(item.url){{const a=node('a',item.url);a.href=item.url;a.target='_blank';a.rel='noopener noreferrer';wrap.appendChild(node('div',undefined,'muted')).appendChild(a)}}
  root.appendChild(wrap);
 }}
}}
function renderErrorItems(targetId,items){{
 const root=el(targetId);root.replaceChildren();
 const section=el(targetId+'Section');
 if(section)section.hidden=targetId!=='sourceErrors'&&!items.length;
 if(!items.length){{if(targetId==='sourceErrors')root.appendChild(node('div','Kayıtlı haber kaynağı hatası yok.','muted'));return}}
 for(const item of items.slice(-12).reverse()){{
  const wrap=node('div',undefined,'report-item');
  wrap.appendChild(node('strong',item.title||item.name||item.component||'Hata'));
  if(item.when)wrap.appendChild(node('div',item.when,'muted'));
  if(item.details)wrap.appendChild(node('div',item.details));
  if(item.urls&&item.urls.length){{
   const list=node('ul');list.style.paddingLeft='20px';
   for(const detail of item.urls){{
    const li=node('li');const a=node('a',detail.title||detail.url||'Detay sayfası');
    if(detail.url){{a.href=detail.url;a.target='_blank';a.rel='noopener noreferrer'}}
    li.appendChild(a);
    if(detail.reason)li.appendChild(node('div',detail.reason,'muted'));
    list.appendChild(li);
   }}
   wrap.appendChild(node('div','Tarihi okunamayan detay sayfaları: '+item.urls.length,'muted'));
   wrap.appendChild(list);
  }}
  root.appendChild(wrap);
 }}
}}
function readableError(value){{
 const raw=String(value||'');
 if(/ReadTimeout|read timed out|timed out.*read timeout|timeout/i.test(raw))return 'Kaynak bağlantısı zaman aşımına uğradı.';
 return raw||'Hata ayrıntısı kaydedilmemiş.';
}}
function readableGeminiError(value){{
 const raw=String(value||'');
 if(/ReadTimeout|read timed out|timed out.*read timeout/i.test(raw))return 'Gemini yanıt vermedi (60 sn zaman aşımı); haber işlenemedi.';
 if(/503|service unavailable/i.test(raw))return 'Gemini geçici olarak hizmet vermedi; haber işlenemedi.';
 if(/429|rate.?limit/i.test(raw))return 'Gemini istek sınırına takıldı; haber işlenemedi.';
 return raw||'Hata ayrıntısı kaydedilmemiş.';
}}
function retryStatusForTitle(title,pendingTitles){{
 const found=pendingTitles.find(t=>title&&title.startsWith(t+':'));
 if(found)return 'Durum: Haber bekleyenler listesinde; yeniden denenmek üzere bekliyor.';
 return 'Durum: Haber güncel bekleyenler listesinde görünmüyor; yeniden deneneceği doğrulanamadı.';
}}
function renderErrors(data){{
 const runs=(data.log?.news_runs||[]).slice(-1);
 const sourceErrors=[];
 const systemErrors=[];
 const pendingByUrl=new Set((data.news_pending||[]).map(item=>item.url).filter(Boolean));
 const pendingTitles=(data.news_pending||[]).map(item=>String(item.title||'')).filter(Boolean);
 for(const run of runs){{
  for(const err of (run.source_errors||[])){{
   const diagnostic=(run.source_diagnostics||{{}})[err.source]||{{}};
   sourceErrors.push({{title:err.source||'Bilinmeyen kaynak',when:'Tarama: '+safeText(run.run_at),details:readableError(err.error||'Kaynak hatası ayrıntısı kaydedilmemiş.'),urls:diagnostic.missing_date_items||[]}});
  }}
  // Haber bazlı işlem hataları ayrı hata listesinde tekrarlanmaz; bekleyen haberler bölümünde yalnızca haber gösterilir.
 }}
 for(const incident of (data.log?.system_incidents||[])){{
  const component=String(incident.component||'');
  const isSource=component.startsWith('news-source:');
  if(isSource&&incident.status!=='resolved'){{
   sourceErrors.push({{title:component.slice('news-source:'.length)||'Bilinmeyen kaynak',when:'İlk görülme: '+safeText(incident.first_seen)+' · Durum: açık',details:readableError(incident.details)}});
  }}else if(!isSource&&incident.status!=='resolved'){{
   const isNewsItem=component.startsWith('news-item:');
   const incidentDetails=String(incident.details||'');
   if(isNewsItem)continue;
   systemErrors.push({{title:component||'Sistem hatası',when:'İlk görülme: '+safeText(incident.first_seen),details:readableGeminiError(incidentDetails)}});
  }}
 }}
 for(const job of (data.actions?.jobs||[])){{
  for(const step of (job.steps||[])){{
   if(step.conclusion==='failure')systemErrors.push({{title:(job.name||'GitHub Actions')+' — '+(step.name||'Başarısız adım'),when:'Son iş akışı: '+safeText(data.actions?.created_at),details:'GitHub Actions adımı başarısız tamamlandı.'}});
  }}
 }}
 for(const err of (data.errors||[]))systemErrors.push({{title:'Rapor verisi okunamadı',details:err}});
 renderErrorItems('sourceErrors',sourceErrors);
 renderErrorItems('systemErrors',systemErrors);
 el('systemErrorsCount').textContent=String(systemErrors.length);
 el('systemErrorsCard').hidden=systemErrors.length===0;
}}
async function api(url,body){{const r=await fetch(url,{{method:body?'POST':'GET',credentials:'same-origin',headers:body?{{'Content-Type':'application/json'}}:{{}},body:body?JSON.stringify(body):undefined,cache:'no-store'}});const j=await r.json().catch(()=>({{}}));if(!r.ok)throw Error(j.detail||'İstek başarısız');return j}}
async function refresh(){{el('message').textContent='Durum bilgisi yükleniyor…';el('refresh').disabled=true;try{{const data=await api('/admin/api/status');render(data);el('message').textContent='Durum bilgisi güncellendi.'}}catch(e){{el('message').textContent=e.message}}finally{{el('refresh').disabled=false}}}}
function decode(s){{s=s.replace(/-/g,'+').replace(/_/g,'/');const raw=atob(s+'='.repeat((4-s.length%4)%4));return Uint8Array.from(raw,c=>c.charCodeAt(0))}}
function encode(buf){{return btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'')}}
async function post(url,data){{const r=await fetch(url,{{method:'POST',credentials:'same-origin',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(data)}});const j=await r.json().catch(()=>({{}}));if(!r.ok)throw Error(j.detail||'İşlem başarısız');return j}}
el('refresh').addEventListener('click',refresh);el('logout').addEventListener('click',async()=>{{try{{await post('/admin/api/logout',{{}})}}finally{{location.href='/admin/haber-durumu'}}}});

refresh();
</script></body></html>'''

@router.get("/admin/haber-durumu", response_class=HTMLResponse)
async def admin_page(request: Request):
    nonce = request.state.csp_nonce
    html = DASHBOARD_HTML if _cookie_session(request) else LOGIN_HTML
    html = html.replace("{nonce}", nonce).replace("{{", "{").replace("}}", "}")
    return HTMLResponse(html, headers={"X-Robots-Tag": "noindex, nofollow, noarchive", "Cache-Control": "no-store"})


@router.post("/admin/api/login/password")
async def admin_password_login(request: Request, body: PasswordLogin):
    _origin_guard(request)
    password = _admin_password()
    if not password:
        raise HTTPException(503, "Yönetici parolası Secret Manager üzerinden yapılandırılmalı.")
    if not hmac.compare_digest(body.password, password):
        raise HTTPException(401, "Parola hatalı.")
    response = JSONResponse({"ok": True})
    _set_session(response)
    return response


@router.post("/admin/api/logout")
async def admin_logout(request: Request):
    _origin_guard(request)
    response = JSONResponse({"ok": True})
    _clear_session(response)
    return response


@router.get("/admin/api/status")
def admin_status(request: Request):
    _require_session(request)
    checked_at = datetime.now(timezone.utc).isoformat()
    result = {
        "checked_at": checked_at,
        "actions": {},
        "log": {},
        "live_api": {"ok": False, "error": None, "updated_at": None, "item_count": 0, "missing_from_live": []},
    }
    errors = []
    try:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "engellime-admin-status"}
        github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if github_token:
            headers["Authorization"] = "Bearer " + github_token
        response = requests.get(API + "/actions/workflows/news-cron.yml/runs?per_page=1", headers=headers, timeout=(5, 20))
        response.raise_for_status()
        runs = response.json().get("workflow_runs", [])
        if runs:
            run = runs[0]
            result["actions"] = {
                "id": run.get("id"), "name": run.get("name"), "status": run.get("conclusion") or run.get("status"),
                "created_at": run.get("created_at"), "updated_at": run.get("updated_at"),
                "html_url": run.get("html_url"), "head_branch": run.get("head_branch"), "head_sha": run.get("head_sha"),
                "event": run.get("event"), "run_number": run.get("run_number"),
            }
            if run.get("id"):
                try:
                    jobs_response = requests.get(API + "/actions/runs/" + str(run["id"]) + "/jobs?per_page=100", headers=headers, timeout=(4, 10))
                    jobs_response.raise_for_status()
                    result["actions"]["jobs"] = [
                        {"name": j.get("name"), "conclusion": j.get("conclusion"), "status": j.get("status"),
                         "steps": [{"name": s.get("name"), "conclusion": s.get("conclusion"), "number": s.get("number")} for s in j.get("steps", [])]}
                        for j in jobs_response.json().get("jobs", [])
                    ]
                except Exception as exc:
                    result["actions"]["jobs_error"] = str(exc)
        else:
            errors.append("GitHub Actions için çalışma kaydı bulunamadı.")
    except Exception as exc:
        errors.append("GitHub Actions okunamadı: " + str(exc))
    try:
        result["log"] = _json_from_raw("news_ai_log.json")
        if not isinstance(result["log"], dict):
            raise ValueError("Log JSON nesnesi değil.")
    except Exception as exc:
        errors.append("Haber işlem logu okunamadı: " + str(exc))
    try:
        expected = _json_from_raw("news.json")
        expected_items = [
            i for i in expected.get("items", [])[:10]
            if str(i.get("url", "")).startswith(("https://", "http://")) and i.get("id")
        ]
        result["news_pending"] = [
            {"title": str(i.get("title") or "Başlıksız haber"), "url": str(i.get("url") or "")}
            for i in expected.get("pending", []) if isinstance(i, dict)
        ]
        result["live_api"].update({
            "check_method": "browser_http",
            "expected_count": len(expected_items),
            "expected_items": [
                {"id": str(i.get("id")), "title": i.get("title"), "url": i.get("url")}
                for i in expected_items
            ],
        })
    except Exception as exc:
        result["live_api"]["error"] = "Beklenen haber listesi okunamadı: " + str(exc)
        errors.append("Beklenen haber listesi okunamadı: " + str(exc))
    result["errors"] = errors
    return JSONResponse(result, headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow, noarchive"})


@router.get("/admin/robots.txt", include_in_schema=False)
async def admin_robots():
    return Response("User-agent: *\nDisallow: /\n", media_type="text/plain",
                    headers={"X-Robots-Tag": "noindex, nofollow, noarchive", "Cache-Control": "no-store"})
