#!/usr/bin/env python3
"""Constant Contact v3 client for the weekly newsletter. Stdlib only.

One-time:
  python3 cc.py auth                         # browser sign-in, stores a refresh token
  python3 cc.py inherit mtva --match MTVA    # copy sender + lists from last week's real MTVA email
  python3 cc.py inherit ytva --match YTVA

Weekly (after render.py has written out/email.html + out/meta.json):
  python3 cc.py draft  WEEK/MTVA             # create (or update) the draft campaign
  python3 cc.py test   WEEK/MTVA             # test-send to the program's test_recipients
  python3 cc.py schedule WEEK/MTVA --at "2026-10-09 14:00" --confirm   # Jerusalem time
  python3 cc.py status WEEK/MTVA             # draft / scheduled / sent, and when
  python3 cc.py unschedule WEEK/MTVA         # pull back a scheduled send so it can be edited

Helpers: whoami | lists | recent [--days N]

Config: ~/.config/tva-newsletter/config.json   Tokens: ~/.config/tva-newsletter/cc_tokens.json
"""
import argparse, base64, datetime as dt, hashlib, http.server, json, os, secrets, sys, threading, time
import urllib.error, urllib.parse, urllib.request, webbrowser
from pathlib import Path
from zoneinfo import ZoneInfo

CFG_DIR = Path.home() / ".config" / "tva-newsletter"
CONFIG, TOKENS = CFG_DIR / "config.json", CFG_DIR / "cc_tokens.json"
AUTHZ = "https://authz.constantcontact.com/oauth2/default/v1"
API = "https://api.cc.email/v3"
SCOPES = "account_read contact_data campaign_data offline_access"
# Constant Contact's edge rejects Python's default User-Agent with a 403 ("error code: 1010").
UA = "tva-newsletter/0.2 (+https://github.com/yehudaseif/mtva-claude-skills)"


def load_cfg():
    if not CONFIG.exists():
        sys.exit(f"No config at {CONFIG}. See SETUP.md.")
    return json.load(open(CONFIG))


def save_cfg(cfg):
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))


def save_tokens(t):
    t["obtained_at"] = int(time.time())
    TOKENS.write_text(json.dumps(t, indent=2))
    os.chmod(TOKENS, 0o600)


# ---------------------------------------------------------------- auth (PKCE)
def cmd_auth(cfg, a):
    cc = cfg["constant_contact"]
    redirect = cc.get("redirect_uri", "http://localhost:8766/callback")
    port = urllib.parse.urlparse(redirect).port or 80
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    url = f"{AUTHZ}/authorize?" + urllib.parse.urlencode({
        "client_id": cc["client_id"], "redirect_uri": redirect, "response_type": "code", "scope": SCOPES,
        "state": state, "code_challenge": challenge, "code_challenge_method": "S256"})
    got = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Constant Contact connected. You can close this tab.")

        def log_message(self, *args):
            pass

    srv = http.server.HTTPServer(("localhost", port), H)
    threading.Thread(target=srv.handle_request, daemon=True).start()
    print(f"Opening the Constant Contact sign-in page. If it does not open, visit:\n{url}\n", flush=True)
    webbrowser.open(url)
    for _ in range(300):
        if got:
            break
        time.sleep(1)
    if got.get("state") != state or "code" not in got:
        sys.exit(f"Sign-in did not complete: {got or 'timed out'}")
    tok = post_form(f"{AUTHZ}/token", {"client_id": cc["client_id"], "redirect_uri": redirect, "code": got["code"],
                                        "code_verifier": verifier, "grant_type": "authorization_code"})
    save_tokens(tok)
    print("Connected.", whoami(cfg))


def post_form(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json", "User-Agent": UA})
    try:
        return json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        sys.exit(f"token request failed {e.code}: {e.read().decode()[:400]}")


def access_token(cfg):
    if not TOKENS.exists():
        sys.exit("Not connected to Constant Contact. Run: python3 cc.py auth")
    t = json.load(open(TOKENS))
    if time.time() < t["obtained_at"] + t.get("expires_in", 0) - 300:
        return t["access_token"]
    cc = cfg["constant_contact"]
    new = post_form(f"{AUTHZ}/token", {"client_id": cc["client_id"], "refresh_token": t["refresh_token"],
                                        "grant_type": "refresh_token",
                                        "redirect_uri": cc.get("redirect_uri", "http://localhost:8766/callback")})
    new.setdefault("refresh_token", t["refresh_token"])
    save_tokens(new)
    return new["access_token"]


def api(cfg, method, path, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {access_token(cfg)}", "Accept": "application/json",
                                          "Content-Type": "application/json", "User-Agent": UA})
    try:
        r = urllib.request.urlopen(req, timeout=60)
        raw = r.read()
        return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} -> {e.code}: {e.read().decode()[:600]}")


# ---------------------------------------------------------------- helpers
def whoami(cfg):
    s = api(cfg, "GET", "/account/summary")
    return f"{s.get('organization_name')} ({s.get('contact_email')})"


def primary_activity(cfg, campaign_id):
    c = api(cfg, "GET", f"/emails/{campaign_id}")
    return next(x["campaign_activity_id"] for x in c["campaign_activities"] if x["role"] == "primary_email")


def recent(cfg, days=45):
    after = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    out, path = [], f"/emails?limit=50&after_date={urllib.parse.quote(after)}"
    while path:
        r = api(cfg, "GET", path)
        out += r.get("campaigns", [])
        nxt = r.get("_links", {}).get("next", {}).get("href")
        path = nxt.replace("/v3", "", 1) if nxt else None
    return sorted(out, key=lambda c: c.get("updated_at", ""), reverse=True)


def week_dir(p):
    d = Path(p).resolve()
    meta = d / "out" / "meta.json"
    if not meta.exists():
        sys.exit(f"{meta} not found: run render.py on this folder's issue first")
    return d, json.load(open(meta))


# ---------------------------------------------------------------- commands
def cmd_whoami(cfg, a):
    print(whoami(cfg))


def cmd_lists(cfg, a):
    r = api(cfg, "GET", "/contact_lists?limit=500&include_membership_count=active")
    for l in r.get("lists", []):
        print(f"{l['list_id']}  {l.get('membership_count', '?'):>6}  {l['name']}")


def cmd_recent(cfg, a):
    for c in recent(cfg, a.days):
        print(f"{c.get('updated_at', '')[:16]}  {c.get('current_status', ''):<10} {c['campaign_id']}  {c['name']}")


def cmd_inherit(cfg, a):
    """Copy sender, reply-to and recipient lists from the newest sent campaign whose name matches."""
    cands = [c for c in recent(cfg, a.days) if a.match.lower() in c["name"].lower() and c.get("current_status") in ("Done", "DONE", "Sent", "SENT")]
    if not cands:
        sys.exit(f"No sent campaign in the last {a.days} days with {a.match!r} in its name. Try: cc.py recent")
    c = cands[0]
    act = api(cfg, "GET", f"/emails/activities/{primary_activity(cfg, c['campaign_id'])}")
    p = cfg.setdefault("programs", {}).setdefault(a.program, {})
    for k in ("from_name", "from_email", "reply_to_email", "contact_list_ids", "segment_ids", "physical_address_in_footer"):
        if act.get(k):
            p[k] = act[k]
    p.setdefault("test_recipients", [])
    save_cfg(cfg)
    print(f"inherited from {c['name']!r} ({c.get('updated_at', '')[:10]}):")
    print(json.dumps({k: p.get(k) for k in ("from_name", "from_email", "reply_to_email", "contact_list_ids", "segment_ids")}, indent=2))


def cmd_draft(cfg, a):
    d, meta = week_dir(a.folder)
    html = (d / "out" / "email.html").read_text(encoding="utf-8")
    p = cfg["programs"][meta["program"].lower()]
    camp_f = d / "out" / "campaign.json"
    if camp_f.exists():  # re-render after edits: update the same draft, never create a duplicate
        camp = json.load(open(camp_f))
        act = api(cfg, "GET", f"/emails/activities/{camp['activity_id']}")
        if act.get("current_status", "").upper() not in ("DRAFT", "ERROR"):
            sys.exit(f"Campaign is {act.get('current_status')}. If it is SCHEDULED, run `cc.py unschedule` first "
                     "(with the user's OK), edit, test, and schedule again. A SENT campaign cannot be changed.")
        act.update({"html_content": html, "subject": meta["subject"], "preheader": meta["preheader"]})
        api(cfg, "PUT", f"/emails/activities/{camp['activity_id']}", act)
        log = d / "changes.md"
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"- {dt.datetime.now().strftime('%a %d %b %H:%M')} draft updated by {os.environ.get('USER', '?')}\n")
        print(f"updated draft {camp['name']!r} (same campaign; nothing was sent)")
        return
    name = meta["campaign_name"]
    body = {"name": name, "email_campaign_activities": [{
        "format_type": 5, "from_name": p["from_name"], "from_email": p["from_email"],
        "reply_to_email": p["reply_to_email"], "subject": meta["subject"], "preheader": meta["preheader"],
        "html_content": html}]}
    if p.get("physical_address_in_footer"):
        body["email_campaign_activities"][0]["physical_address_in_footer"] = p["physical_address_in_footer"]
    try:
        c = api(cfg, "POST", "/emails", body)
    except RuntimeError as e:
        if "409" not in str(e) and "name" not in str(e).lower():
            raise
        body["name"] = f"{name} {dt.datetime.now().strftime('%H%M')}"
        c = api(cfg, "POST", "/emails", body)
    aid = next(x["campaign_activity_id"] for x in c["campaign_activities"] if x["role"] == "primary_email")
    act = api(cfg, "GET", f"/emails/activities/{aid}")
    if p.get("segment_ids"):
        act["segment_ids"] = p["segment_ids"]
    else:
        act["contact_list_ids"] = p["contact_list_ids"]
    api(cfg, "PUT", f"/emails/activities/{aid}", act)
    camp = {"name": body["name"], "campaign_id": c["campaign_id"], "activity_id": aid, "created": dt.datetime.now().isoformat(timespec="seconds")}
    camp_f.write_text(json.dumps(camp, indent=2))
    print(f"draft created: {camp['name']!r}\n  campaign {c['campaign_id']}\n  recipients: {act.get('segment_ids') or act.get('contact_list_ids')}")
    print("  find it under Campaigns in the Bnei Akiva of the US & Canada workspace (app.constantcontact.com/home -> Hub dropdown)")


def cmd_test(cfg, a):
    d, meta = week_dir(a.folder)
    camp = json.load(open(d / "out" / "campaign.json"))
    to = a.to or cfg["programs"][meta["program"].lower()].get("test_recipients", [])
    if not to:
        sys.exit("No recipients: pass --to or set test_recipients in the config")
    for i in range(0, len(to), 5):
        api(cfg, "POST", f"/emails/activities/{camp['activity_id']}/tests",
            {"email_addresses": to[i:i + 5], "personal_message": f"Test of {camp['name']}"})
    print(f"test sent to {', '.join(to)}")


def cmd_schedule(cfg, a):
    d, meta = week_dir(a.folder)
    camp = json.load(open(d / "out" / "campaign.json"))
    if a.at == "now":
        when = "0"
    else:
        local = dt.datetime.strptime(a.at, "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("Asia/Jerusalem"))
        if local < dt.datetime.now(dt.timezone.utc):
            sys.exit(f"{a.at} Jerusalem time is in the past")
        when = local.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    act = api(cfg, "GET", f"/emails/activities/{camp['activity_id']}")
    lists = act.get("segment_ids") or act.get("contact_list_ids")
    print(f"campaign:   {camp['name']}\nsubject:    {act.get('subject')}\nrecipients: {lists}\nsend at:    {a.at} (Asia/Jerusalem) = {when}")
    if not a.confirm:
        sys.exit("Not scheduled. Re-run with --confirm once a person has approved the final test email.")
    api(cfg, "POST", f"/emails/activities/{camp['activity_id']}/schedules", {"scheduled_date": when})
    camp["scheduled"] = {"at_local": a.at, "utc": when, "by": os.environ.get("USER", "")}
    (d / "out" / "campaign.json").write_text(json.dumps(camp, indent=2))
    print("SCHEDULED.")


def cmd_status(cfg, a):
    d, meta = week_dir(a.folder)
    camp = json.load(open(d / "out" / "campaign.json"))
    act = api(cfg, "GET", f"/emails/activities/{camp['activity_id']}")
    sched = api(cfg, "GET", f"/emails/activities/{camp['activity_id']}/schedules")
    when = ", ".join(x.get("scheduled_date", "") for x in sched) if isinstance(sched, list) else ""
    print(f"{camp['name']}: {act.get('current_status')}" + (f", scheduled for {when} (UTC)" if when else ""))


def cmd_unschedule(cfg, a):
    d, meta = week_dir(a.folder)
    camp = json.load(open(d / "out" / "campaign.json"))
    act = api(cfg, "GET", f"/emails/activities/{camp['activity_id']}")
    if act.get("current_status", "").upper() != "SCHEDULED":
        sys.exit(f"Not scheduled (status {act.get('current_status')}); nothing to undo.")
    api(cfg, "DELETE", f"/emails/activities/{camp['activity_id']}/schedules")
    camp.pop("scheduled", None)
    (d / "out" / "campaign.json").write_text(json.dumps(camp, indent=2))
    print(f"Unscheduled {camp['name']!r}. It is a draft again; it will NOT send until scheduled again with --confirm.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("auth")
    sp.add_parser("whoami")
    sp.add_parser("lists")
    r = sp.add_parser("recent"); r.add_argument("--days", type=int, default=45)
    i = sp.add_parser("inherit"); i.add_argument("program", choices=["mtva", "ytva"]); i.add_argument("--match", required=True); i.add_argument("--days", type=int, default=60)
    d = sp.add_parser("draft"); d.add_argument("folder")
    t = sp.add_parser("test"); t.add_argument("folder"); t.add_argument("--to", nargs="*")
    st = sp.add_parser("status"); st.add_argument("folder")
    u = sp.add_parser("unschedule"); u.add_argument("folder")
    s = sp.add_parser("schedule"); s.add_argument("folder"); s.add_argument("--at", required=True, help='"YYYY-MM-DD HH:MM" Jerusalem time, or "now"'); s.add_argument("--confirm", action="store_true")
    a = ap.parse_args()
    CFG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_cfg()
    try:
        globals()["cmd_" + a.cmd](cfg, a)
    except RuntimeError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
