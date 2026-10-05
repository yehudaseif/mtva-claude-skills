# One-time setup

About 20 minutes, once per computer. After this, a week's newsletter is: drop the
pieces in the folder, ask Claude for "this week's MTVA and YTVA newsletters", read the
test emails, say when to send.

## 1. Install

```bash
claude plugin marketplace add yehudaseif/mtva-claude-skills
claude plugin install tva-newsletter@mtva-skills
pip3 install pillow tzdata   # tzdata: needed on Windows for the send-time conversion
```
(Or, from the zip: unzip it into `~/.claude/skills/` so you have
`~/.claude/skills/tva-newsletter/SKILL.md`.)

Python 3.9 or newer is needed (`python3 --version`).

## 2. Config file

```bash
mkdir -p ~/.config/tva-newsletter
cp config.example.json ~/.config/tva-newsletter/config.json
```
Then fill in the two sections below. The file holds keys: keep it on this computer,
never commit or email it.

## 3. Constant Contact API key (the `constant_contact` section)

Constant Contact's API cannot be used without a registered "application". It is free:

1. Sign in at <https://app.constantcontact.com/pages/dma/portal/> (the developer portal)
   with the Constant Contact login that sends the newsletters.
2. **New Application** → name it `TVA Newsletter` → flow: **Proof Key for Code
   Exchange (PKCE)** (no client secret). Refresh tokens: **Rotating** is the only choice
   with PKCE; the script saves each new token automatically. Log into the portal while
   the **Bnei Akiva of the US & Canada** workspace is selected: a new app is limited to
   the account you are in.
3. **Edit** the app → pencil next to the redirect URI → `http://localhost:8766/callback`
   → Confirm → **Save**. (If something else on the computer already uses port 8766,
   pick another port and use it in both the portal and `redirect_uri` in the config.)
4. Copy the **API Key** into `client_id` in the config.

Then connect, and copy the sender and recipient lists from last week's real emails:

```bash
cd ~/.claude/plugins/marketplaces/mtva-skills/plugins/tva-newsletter/skills/tva-newsletter/scripts   # or wherever the skill lives
python3 cc.py auth            # a browser window opens: sign in and Allow
python3 cc.py recent          # last 45 days of campaigns, to see their names
python3 cc.py inherit mtva --match "MTVA"
python3 cc.py inherit ytva --match "YTVA"
```
`inherit` copies From name, From address, Reply-to and the contact lists from the newest
**sent** campaign whose name contains the match text. Check what it printed. If the
lists are wrong, run `python3 cc.py lists` and edit `contact_list_ids` in the config by hand.

## 4. Photo hosting (the `image_host` section)

Constant Contact's API cannot upload images, so the photos go to a Cloudflare R2 bucket
and the email links to them. **This is already set up** for TVA: bucket `tva-newsletter`
in Cloudflare account `yehudaseif@gmail.com`, served at `https://img.mtvaisrael.org`.
A new computer only needs the upload key (Access Key ID + Secret Access Key) in its
config — ask for it, or create a new one:

1. Cloudflare dashboard → **R2 Object Storage** → **Manage API Tokens** →
   **Create Account API token** → **Object Read & Write** → **Apply to specific buckets
   only: tva-newsletter** → Create.
2. Copy the **Access Key ID** and **Secret Access Key** (shown once) into
   `image_host` in the config:
   ```json
   "image_host": {"type": "r2", "account_id": "b86ed1a6b67e0a04c58667cf5ef15dc0",
     "bucket": "tva-newsletter", "access_key_id": "…", "secret_access_key": "…",
     "public_base_url": "https://img.mtvaisrael.org", "prefix": "newsletter"}
   ```
Never email the secret in plain text; share it through a password manager.

How it was built, for the record: R2 enabled on the account; bucket created; Settings →
Custom Domains → `img.mtvaisrael.org` (Cloudflare adds the CNAME itself). Right after
enabling R2 the upload endpoint refused TLS for ~5 minutes until its certificate
was issued — a handshake failure on first use is that, not bad keys.

No key at all? `"image_host": {"type": "manual"}` still works: upload `out/img/` to the
Constant Contact Library (SKILL.md section 5b) and paste the URLs into
`out/upload-urls.json`.

## 5. Test it

```bash
python3 new_week.py --date <next Friday>
```
Put one paragraph and one photo in the MTVA folder and ask Claude to build the MTVA
newsletter and send you a test. Check it on your phone.

## What stays manual, on purpose

Scheduling the real send. Claude creates the draft and sends tests; a person reads
the test and gives the send time. `cc.py schedule` refuses to run without `--confirm`.
