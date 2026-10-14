import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timezone
from urllib.parse import quote

import redis
import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import options_to_json
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

router = APIRouter()
PREFIX = "engellime:admin:"
SESSION_TTL = 7 * 24 * 60 * 60
CHALLENGE_TTL = 5 * 60
REPO = "rsever-source/mobilrs"
BRANCH = "cloud-run-migration"
RAW = "https://raw.githubusercontent.com/" + REPO + "/" + BRANCH + "/"
API = "https://api.github.com/repos/" + REPO
LIVE_NEWS = "https://engelli.me/api/news"


def _redis():
    url = os.environ.get("REDIS_URL", "").strip()
    if not url:
        raise HTTPException(503, "Yönetim paneli için REDIS_URL yapılandırılmalı.")
    try:
        client = redis.from_url(url, decode_responses=True, socket_connect_timeout=3, socket_timeout=5)
        client.ping()
        return client
    except Exception:
        raise HTTPException(503, "Yönetim panelinin kalıcı oturum deposuna ulaşılamıyor.")


def _rp_id():
    return os.environ.get("ADMIN_PASSKEY_RP_ID", "engelli.me").strip()


def _origin():
    return os.environ.get("ADMIN_PASSKEY_ORIGIN", "https://engelli.me").strip().rstrip("/")


def _password_ok(password):
    stored = os.environ.get("ADMIN_PASSWORD_HASH", "")
    # Format: pbkdf2_sha256$iterations$salt_hex$digest_hex
    try:
        algorithm, rounds, salt_hex, digest_hex = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds)
        ).hex()
        return hmac.compare_digest(digest, digest_hex)
    except Exception:
        return False


def _cookie_session(request):
    token = request.cookies.get("eng_admin_session", "")
    if not token or len(token) > 128:
        return None
    try:
        r = _redis()
        if r.get(PREFIX + "session:" + token) == "1":
            r.expire(PREFIX + "session:" + token, SESSION_TTL)
            return token
    except HTTPException:
        return None
    return None


def _require_session(request):
    token = _cookie_session(request)
    if not token:
        raise HTTPException(401, "Oturum açılması gerekiyor.")
    return token


def _set_session(response):
    token = secrets.token_urlsafe(32)
    _redis().setex(PREFIX + "session:" + token, SESSION_TTL, "1")
    response.set_cookie(
        "eng_admin_session", token, max_age=SESSION_TTL, httponly=True,
        secure=True, samesite="strict", path="/admin"
    )


def _clear_session(response, request):
    token = request.cookies.get("eng_admin_session", "")
    if token and len(token) <= 128:
        try:
            _redis().delete(PREFIX + "session:" + token)
        except HTTPException:
            pass
    response.delete_cookie("eng_admin_session", path="/admin", secure=True, httponly=True, samesite="strict")


def _json_from_raw(path):
    response = requests.get(RAW + path, timeout=(4, 12), headers={"Cache-Control": "no-cache"})
    response.raise_for_status()
    return response.json()


def _passkey_records(r):
    result = []
    for key in r.scan_iter(match=PREFIX + "credential:*", count=100):
        value = r.get(key)
        if value:
            try:
                result.append(json.loads(value))
            except Exception:
                continue
    return result


def _challenge_key(token, purpose):
    return PREFIX + "challenge:" + purpose + ":" + token


def _store_challenge(purpose, challenge):
    token = secrets.token_urlsafe(24)
    _redis().setex(
        _challenge_key(token, purpose),
        CHALLENGE_TTL,
        base64.urlsafe_b64encode(challenge).decode("ascii").rstrip("="),
    )
    return token


def _take_challenge(token, purpose):
    if not token or len(token) > 128:
        raise HTTPException(400, "Doğrulama süresi doldu. Yeniden deneyin.")
    r = _redis()
    key = _challenge_key(token, purpose)
    value = r.get(key)
    r.delete(key)
    if not value:
        raise HTTPException(400, "Doğrulama süresi doldu. Yeniden deneyin.")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _origin_guard(request):
    origin = request.headers.get("origin", "").rstrip("/")
    if origin != _origin():
        raise HTTPException(403, "İstek kaynağı doğrulanamadı.")


class PasswordLogin(BaseModel):
    password: str


class CeremonyStart(BaseModel):
    ceremony: str = "login"


class CeremonyFinish(BaseModel):
    ceremony_token: str
    credential: dict


LOGIN_HTML = r'''<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive"><title>Engelli.me yönetim girişi</title>
<style nonce="{nonce}">
*{{box-sizing:border-box}}body{{margin:0;background:#f3f6fa;color:#172033;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;min-height:100vh;display:grid;place-items:center;padding:20px}}
main{{width:min(100%,420px);background:white;border:1px solid #e1e7ef;border-radius:20px;padding:26px;box-shadow:0 12px 36px #15223a12}}
h1{{font-size:22px;margin:0 0 8px}}p{{color:#647084;font-size:14px;line-height:1.5}}label{{display:block;font-weight:650;font-size:14px;margin:18px 0 7px}}
input,button{{width:100%;padding:13px 14px;border-radius:10px;font:inherit}}input{{border:1px solid #cbd4e1}}button{{border:0;background:#155eef;color:white;font-weight:700;margin-top:12px;cursor:pointer}}button.secondary{{background:#eef3ff;color:#174ea6}}#msg{{min-height:22px;color:#a32020;font-size:13px}}.brand{{font-weight:850;color:#155eef;margin-bottom:22px}}.brand span{{color:#172033}}
</style></head><body><main><div class="brand">Engelli<span>.me</span></div><h1>Haber yönetim paneli</h1>
<p>Bu alan yalnızca yetkili yönetici içindir. iPhone’da Face ID destekli Passkey ile veya yedek parolayla giriş yapın.</p>
<button id="passkey" class="secondary" type="button">Passkey ile giriş yap</button>
<form id="passwordForm"><label for="password">Yedek parola</label><input id="password" type="password" autocomplete="current-password" required maxlength="256"><button type="submit">Giriş yap</button></form>
<p id="msg" role="status"></p></main>
<script nonce="{nonce}">
const msg=document.getElementById('msg');
function b64decode(s){{s=s.replace(/-/g,'+').replace(/_/g,'/');const raw=atob(s+'='.repeat((4-s.length%4)%4));return Uint8Array.from(raw,c=>c.charCodeAt(0))}}
function b64encode(buf){{return btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'')}}
async function post(url,data){{const r=await fetch(url,{{method:'POST',credentials:'same-origin',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(data)}});const j=await r.json().catch(()=>({{}}));if(!r.ok)throw Error(j.detail||'İşlem başarısız');return j}}
document.getElementById('passwordForm').addEventListener('submit',async e=>{{e.preventDefault();msg.textContent='';try{{await post('/admin/api/login/password',{{password:document.getElementById('password').value}});location.href='/admin/haber-durumu'}}catch(err){{msg.textContent=err.message}}}});
document.getElementById('passkey').addEventListener('click',async()=>{{msg.textContent='';try{{const start=await post('/admin/api/passkey/start',{{ceremony:'login'}});const opts=start.options;opts.challenge=b64decode(opts.challenge);if(opts.allowCredentials)opts.allowCredentials=opts.allowCredentials.map(x=>({{...x,id:b64decode(x.id)}}));const cred=await navigator.credentials.get({{publicKey:opts}});const credential={{id:cred.id,rawId:b64encode(cred.rawId),type:cred.type,response:{{authenticatorData:b64encode(cred.response.authenticatorData),clientDataJSON:b64encode(cred.response.clientDataJSON),signature:b64encode(cred.response.signature),userHandle:cred.response.userHandle?b64encode(cred.response.userHandle):null}},clientExtensionResults:cred.getClientExtensionResults()}};await post('/admin/api/passkey/finish',{{ceremony_token:start.ceremony_token,credential}});location.href='/admin/haber-durumu'}}catch(err){{msg.textContent=err.message||'Passkey doğrulanamadı'}}}});
</script></body></html>'''


DASHBOARD_HTML = r'''<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive"><title>Engelli.me haber durumu</title>
<style nonce="{nonce}">
*{{box-sizing:border-box}}body{{margin:0;background:#f3f6fa;color:#172033;font-family:system-ui,-apple-system,"Segoe UI",sans-serif}}main{{max-width:1180px;margin:auto;padding:20px}}
header{{display:flex;gap:14px;align-items:center;justify-content:space-between;flex-wrap:wrap;margin-bottom:20px}}h1{{font-size:24px;margin:0}}.muted{{color:#657187;font-size:13px}}button,input{{font:inherit;border-radius:10px;padding:10px 13px}}button{{border:0;background:#155eef;color:white;font-weight:700;cursor:pointer}}button.secondary{{background:#e8eef8;color:#1c355d}}.cards{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}}.card,section{{background:#fff;border:1px solid #e1e7ef;border-radius:14px;padding:16px;min-width:0}}.card small{{display:block;color:#657187}}.card strong{{display:block;font-size:21px;margin-top:7px;overflow-wrap:anywhere}}section{{margin-top:14px}}h2{{font-size:17px;margin:0 0 12px}}.status{{font-weight:750}}.good{{color:#16803c}}.bad{{color:#b42318}}.warn{{color:#9a6700}}.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{padding:9px;border-bottom:1px solid #e8edf3;text-align:left;vertical-align:top}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;background:#f7f9fc;padding:12px;border-radius:8px;max-height:560px;overflow:auto}}.row{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}}input[type=search]{{border:1px solid #cbd4e1;min-width:200px;flex:1}}details{{border-bottom:1px solid #e8edf3;padding:10px 0}}summary{{cursor:pointer;font-weight:650}}.pill{{display:inline-block;padding:3px 8px;border-radius:999px;background:#edf2f8;font-size:12px}}#message{{min-height:18px;margin:8px 0;color:#526174;font-size:13px}}@media(max-width:760px){{main{{padding:14px}}.cards{{grid-template-columns:repeat(2,minmax(0,1fr))}}.grid2{{grid-template-columns:1fr}}h1{{font-size:20px}}}}
</style></head><body><main>
<header><div><div class="muted">Engelli.me / Özel yönetim</div><h1>Haber sistemi durum raporu</h1><div class="muted" id="lastChecked">Henüz kontrol edilmedi</div></div><div class="row"><button id="refresh">Güncelle</button><button class="secondary" id="register">Bu cihazda Passkey kaydet</button><button class="secondary" id="logout">Çıkış</button></div></header>
<p id="message" role="status">Mevcut kayıtlar yükleniyor…</p>
<div class="cards">
<div class="card"><small>Son GitHub Actions</small><strong id="runStatus">—</strong><div class="muted" id="runTime"></div></div>
<div class="card"><small>Canlı API</small><strong id="apiStatus">—</strong><div class="muted" id="apiTime"></div></div>
<div class="card"><small>Son tarama adayı</small><strong id="candidateCount">—</strong><div class="muted">Son kayıtlı tarama</div></div>
<div class="card"><small>Sistem olayı</small><strong id="incidentCount">—</strong><div class="muted">Kayıtlı olayların tamamı</div></div>
</div>
<section><h2>Haber işlem özeti</h2><div class="cards">
<div class="card"><small>Yayımlanan</small><strong id="published">—</strong></div>
<div class="card"><small>Tekrar / daha önce işlenmiş</small><strong id="duplicates">—</strong></div>
<div class="card"><small>Filtreyle elenen</small><strong id="rejected">—</strong></div>
<div class="card"><small>Bekleyen / belirsiz</small><strong id="pending">—</strong></div>
</div><p class="muted">Sayılar yalnızca mevcut logda açıkça bulunan durum alanlarından hesaplanır; eksik bilgiler tahmin edilmez.</p></section>
<div class="grid2"><section><h2>Son tarama ve kaynak teşhisleri</h2><div id="sources"></div></section><section><h2>Son çalıştırma ayrıntıları</h2><div id="runDetails"></div></section></div>
<section><h2>Tüm haber işlem kayıtları</h2><div class="row"><input id="search" type="search" placeholder="Kayıtlarda ara…"><span class="muted" id="logMeta"></span></div><div id="runs"></div></section>
<section><h2>Tüm sistem olayları</h2><div id="incidents"></div></section>
<section><h2>Canlı API karşılaştırması</h2><div id="apiDetails"></div></section>
<section><h2>Ham log verisi (tüm alanlar)</h2><div class="row"><button class="secondary" id="download">JSON olarak dışa aktar</button></div><pre id="rawLog">—</pre></section>
</main>
<script nonce="{nonce}">
let state=null;
function el(id){{return document.getElementById(id)}}
function safeText(v){{return v===null||v===undefined?'—':String(v)}}
function node(tag,text,cls){{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n}}
function pretty(v){{return JSON.stringify(v,null,2)}}
function details(title,value){{const d=node('details'),s=node('summary',title),p=node('pre',pretty(value));d.append(s,p);return d}}
function addJsonList(target,items,titleFn){{target.replaceChildren();if(!Array.isArray(items)||!items.length){{target.append(node('p','Kayıt bulunamadı.','muted'));return}}items.forEach((item,i)=>target.append(details(titleFn(item,i),item)))}}
function formatDate(v){{if(!v)return 'Tarih yok';const d=new Date(v);return Number.isNaN(d.getTime())?String(v):d.toLocaleString('tr-TR')}}
function counts(log){{const out={{published:0,duplicates:0,rejected:0,pending:0}};for(const run of (log.news_runs||[])){{for(const c of (run.candidates||[])){{const s=String(c.status||'').toLowerCase();if(s==='published'||c.publish===true)out.published++;else if(c.duplicate===true||s.includes('duplicate'))out.duplicates++;else if(s==='pending'||s==='pending_review')out.pending++;else if(c.publish===false||s==='rejected')out.rejected++}}}}const f=(log.news_runs||[]).slice(-1)[0]?.filter_diagnostics?.counts||{{}};out.duplicates=Math.max(out.duplicates,Number(f.duplicate_in_this_run||0)+Number(f.url_seen_within_7_days||0)+Number(f.already_published||0));out.rejected=Math.max(out.rejected,Number(f.older_than_7_days||0)+Number(f.missing_date||0)+Number(f.future_date||0)+Number(f.pending_unknown_or_expired_date||0));return out}}
function render(data){{state=data;const log=data.log||{{}};const runs=log.news_runs||[];const last=runs[runs.length-1]||{{}};const cs=counts(log);
el('lastChecked').textContent='Kontrol zamanı: '+formatDate(data.checked_at);el('runStatus').textContent=data.actions?.status||'Bilinmiyor';el('runTime').textContent=formatDate(data.actions?.created_at);el('apiStatus').textContent=data.live_api?.ok?'Çalışıyor':'Kontrol başarısız';el('apiStatus').className=data.live_api?.ok?'good':'bad';el('apiTime').textContent=data.live_api?.updated_at?'Güncelleme: '+formatDate(data.live_api.updated_at):safeText(data.live_api?.error);el('candidateCount').textContent=safeText(last.candidates?.length??last.filter_diagnostics?.counts?.accepted_as_candidate);el('incidentCount').textContent=String((log.system_incidents||[]).length);el('published').textContent=cs.published;el('duplicates').textContent=cs.duplicates;el('rejected').textContent=cs.rejected;el('pending').textContent=cs.pending;
el('runDetails').replaceChildren(details('Son tarama kaydının tüm alanları',last),details('En son GitHub Actions bilgisi',data.actions||{{}}));
const sources=last.source_diagnostics||{{}};el('sources').replaceChildren();if(!Object.keys(sources).length)el('sources').append(node('p','Kaynak teşhisi bulunamadı.','muted'));Object.entries(sources).forEach(([name,v])=>{{const d=node('details'),s=node('summary',name),p=node('pre',pretty(v));d.append(s,p);el('sources').append(d)}});
addJsonList(el('runs'),runs.slice().reverse(),(r,i)=>formatDate(r.run_at)+' · '+safeText(r.model)+' · '+((r.candidates||[]).length)+' aday');addJsonList(el('incidents'),(log.system_incidents||[]).slice().reverse(),(r)=>formatDate(r.updated_at||r.created_at||r.last_seen||r.first_seen)+' · '+safeText(r.component)+' · '+safeText(r.status));
el('apiDetails').replaceChildren(details('Canlı API yanıtı ve karşılaştırma',data.live_api||{{}}));el('rawLog').textContent=pretty(log);el('logMeta').textContent=runs.length+' tarama kaydı · '+(log.system_incidents||[]).length+' sistem olayı';applySearch()}}
function applySearch(){{const q=el('search').value.trim().toLocaleLowerCase('tr');el('runs').querySelectorAll('details').forEach(d=>d.style.display=!q||d.textContent.toLocaleLowerCase('tr').includes(q)?'':'none');el('incidents').querySelectorAll('details').forEach(d=>d.style.display=!q||d.textContent.toLocaleLowerCase('tr').includes(q)?'':'none')}}
async function api(url,body){{const r=await fetch(url,{{method:body?'POST':'GET',credentials:'same-origin',headers:body?{{'Content-Type':'application/json'}}:{{}},body:body?JSON.stringify(body):undefined,cache:'no-store'}});const j=await r.json().catch(()=>({{}}));if(!r.ok)throw Error(j.detail||'İstek başarısız');return j}}
async function refresh(){{el('message').textContent='GitHub Actions, loglar ve canlı API kontrol ediliyor…';el('refresh').disabled=true;try{{render(await api('/admin/api/status'));el('message').textContent='Kontrol tamamlandı. Yeni tarama başlatılmadı.'}}catch(e){{el('message').textContent=e.message}}finally{{el('refresh').disabled=false}}}}
function decode(s){{s=s.replace(/-/g,'+').replace(/_/g,'/');const raw=atob(s+'='.repeat((4-s.length%4)%4));return Uint8Array.from(raw,c=>c.charCodeAt(0))}}
function encode(buf){{return btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'')}}
async function post(url,data){{const r=await fetch(url,{{method:'POST',credentials:'same-origin',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(data)}});const j=await r.json().catch(()=>({{}}));if(!r.ok)throw Error(j.detail||'İşlem başarısız');return j}}
el('refresh').addEventListener('click',refresh);el('search').addEventListener('input',applySearch);el('logout').addEventListener('click',async()=>{{try{{await post('/admin/api/logout',{{}})}}finally{{location.href='/admin/haber-durumu'}}}});
el('register').addEventListener('click',async()=>{{try{{const start=await post('/admin/api/passkey/register/start',{{}});const o=start.options;o.challenge=decode(o.challenge);o.user.id=decode(o.user.id);if(o.excludeCredentials)o.excludeCredentials=o.excludeCredentials.map(x=>({{...x,id:decode(x.id)}}));const c=await navigator.credentials.create({{publicKey:o}});const credential={{id:c.id,rawId:encode(c.rawId),type:c.type,response:{{attestationObject:encode(c.response.attestationObject),clientDataJSON:encode(c.response.clientDataJSON),transports:c.response.getTransports?c.response.getTransports():[]}},clientExtensionResults:c.getClientExtensionResults()}};await post('/admin/api/passkey/register/finish',{{ceremony_token:start.ceremony_token,credential}});el('message').textContent='Passkey kaydedildi. Bu cihazda biyometrik doğrulama kullanabilirsiniz.'}}catch(e){{el('message').textContent=e.message||'Passkey kaydedilemedi'}}}});
el('download').addEventListener('click',()=>{{const blob=new Blob([pretty(state?.log||{{}})],{{type:'application/json;charset=utf-8'}});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='news_ai_log.json';a.click();URL.revokeObjectURL(url)}});
refresh();
</script></body></html>'''


@router.get("/admin/haber-durumu", response_class=HTMLResponse)
async def admin_page(request: Request):
    nonce = request.state.csp_nonce
    if _cookie_session(request):
        html = DASHBOARD_HTML.replace("{nonce}", nonce).replace("{{", "{").replace("}}", "}")
    else:
        html = LOGIN_HTML.replace("{nonce}", nonce).replace("{{", "{").replace("}}", "}")
    return HTMLResponse(html, headers={"X-Robots-Tag": "noindex, nofollow, noarchive", "Cache-Control": "no-store"})


@router.post("/admin/api/login/password")
async def admin_password_login(request: Request, body: PasswordLogin):
    _origin_guard(request)
    await _rate_login(request)
    if not os.environ.get("ADMIN_PASSWORD_HASH") or not _password_ok(body.password):
        raise HTTPException(401, "Parola hatalı veya yedek giriş yapılandırılmamış.")
    response = JSONResponse({"ok": True})
    _set_session(response)
    return response


async def _rate_login(request):
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if not ip:
        ip = request.client.host if request.client else "unknown"
    r = _redis()
    key = PREFIX + "login-attempts:" + hashlib.sha256(ip.encode()).hexdigest()
    attempts = r.incr(key)
    if attempts == 1:
        r.expire(key, 300)
    if attempts > 8:
        raise HTTPException(429, "Çok fazla giriş denemesi. 5 dakika sonra tekrar deneyin.")


@router.post("/admin/api/passkey/start")
async def passkey_login_start(request: Request, body: CeremonyStart):
    _origin_guard(request)
    r = _redis()
    credentials = _passkey_records(r)
    if not credentials:
        raise HTTPException(400, "Henüz Passkey kaydedilmemiş. Yedek parolayla giriş yapıp bu cihazı kaydedin.")
    options = generate_authentication_options(
        rp_id=_rp_id(),
        allow_credentials=[
            PublicKeyCredentialDescriptor(id=base64.urlsafe_b64decode(c["credential_id"] + "=" * (-len(c["credential_id"]) % 4)))
            for c in credentials
        ],
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    token = _store_challenge("login", options.challenge)
    return {"ceremony_token": token, "options": json.loads(options_to_json(options))}


@router.post("/admin/api/passkey/finish")
async def passkey_login_finish(request: Request, body: CeremonyFinish):
    _origin_guard(request)
    challenge = _take_challenge(body.ceremony_token, "login")
    credential_id = body.credential.get("id") or body.credential.get("rawId")
    if not credential_id:
        raise HTTPException(400, "Passkey kimliği eksik.")
    r = _redis()
    key = PREFIX + "credential:" + credential_id
    raw = r.get(key)
    if not raw:
        raise HTTPException(401, "Bu Passkey kayıtlı değil.")
    record = json.loads(raw)
    try:
        verification = verify_authentication_response(
            credential=body.credential,
            expected_challenge=challenge,
            expected_rp_id=_rp_id(),
            expected_origin=_origin(),
            credential_public_key=base64.urlsafe_b64decode(record["public_key"] + "=" * (-len(record["public_key"]) % 4)),
            credential_current_sign_count=int(record.get("sign_count", 0)),
            require_user_verification=True,
        )
    except Exception:
        raise HTTPException(401, "Passkey doğrulanamadı.")
    record["sign_count"] = verification.new_sign_count
    r.set(key, json.dumps(record))
    response = JSONResponse({"ok": True})
    _set_session(response)
    return response


@router.post("/admin/api/passkey/register/start")
async def passkey_register_start(request: Request):
    _origin_guard(request)
    _require_session(request)
    r = _redis()
    credentials = _passkey_records(r)
    options = generate_registration_options(
        rp_id=_rp_id(),
        rp_name="Engelli.me Haber Yönetimi",
        user_id=b"engellime-admin",
        user_name="engellime-admin",
        user_display_name="Engelli.me yöneticisi",
        exclude_credentials=[
            PublicKeyCredentialDescriptor(id=base64.urlsafe_b64decode(c["credential_id"] + "=" * (-len(c["credential_id"]) % 4)))
            for c in credentials
        ],
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
    )
    token = _store_challenge("register", options.challenge)
    return {"ceremony_token": token, "options": json.loads(options_to_json(options))}


@router.post("/admin/api/passkey/register/finish")
async def passkey_register_finish(request: Request, body: CeremonyFinish):
    _origin_guard(request)
    _require_session(request)
    challenge = _take_challenge(body.ceremony_token, "register")
    try:
        verification = verify_registration_response(
            credential=body.credential,
            expected_challenge=challenge,
            expected_rp_id=_rp_id(),
            expected_origin=_origin(),
            require_user_verification=True,
        )
    except Exception:
        raise HTTPException(400, "Passkey kaydı doğrulanamadı.")
    credential_id = base64.urlsafe_b64encode(verification.credential_id).decode("ascii").rstrip("=")
    record = {
        "credential_id": credential_id,
        "public_key": base64.urlsafe_b64encode(verification.credential_public_key).decode("ascii").rstrip("="),
        "sign_count": verification.sign_count,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _redis().set(PREFIX + "credential:" + credential_id, json.dumps(record))
    return {"ok": True}


@router.post("/admin/api/logout")
async def admin_logout(request: Request):
    _origin_guard(request)
    response = JSONResponse({"ok": True})
    _clear_session(response, request)
    return response


@router.get("/admin/api/status")
async def admin_status(request: Request):
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
        response = requests.get(API + "/actions/workflows/news-cron.yml/runs?per_page=1", headers=headers, timeout=(4, 12))
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
        live_response = requests.get(LIVE_NEWS, timeout=(4, 12), headers={"Cache-Control": "no-cache"})
        live_response.raise_for_status()
        live = live_response.json()
        if not isinstance(live, dict) or not isinstance(live.get("items"), list):
            raise ValueError("Canlı API yanıt biçimi beklenenden farklı.")
        result["live_api"].update({
            "ok": True, "http_status": live_response.status_code, "updated_at": live.get("updated_at"),
            "item_count": len(live["items"]), "items": live["items"],
        })
        try:
            expected = _json_from_raw("news.json")
            expected_items = [i for i in expected.get("items", [])[:10] if str(i.get("url", "")).startswith(("https://", "http://")) and i.get("id")]
            live_ids = {str(i.get("id")) for i in live["items"] if i.get("id")}
            result["live_api"]["expected_count"] = len(expected_items)
            result["live_api"]["missing_from_live"] = [
                {"id": i.get("id"), "title": i.get("title"), "url": i.get("url")}
                for i in expected_items if str(i["id"]) not in live_ids
            ]
        except Exception as exc:
            result["live_api"]["comparison_error"] = str(exc)
    except Exception as exc:
        result["live_api"]["error"] = str(exc)
        errors.append("Canlı API okunamadı: " + str(exc))
    result["errors"] = errors
    return JSONResponse(result, headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow, noarchive"})


@router.get("/admin/robots.txt", include_in_schema=False)
async def admin_robots():
    return Response("User-agent: *\nDisallow: /\n", media_type="text/plain",
                    headers={"X-Robots-Tag": "noindex, nofollow, noarchive", "Cache-Control": "no-store"})
