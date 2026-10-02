# One-time setup

About 20 minutes, once per computer. After this, a week's newsletter is: drop the
pieces in the folder, ask Claude for "this week's MTVA and YTVA newsletters", read the
test emails, say when to send.

## 1. Install

```bash
claude plugin marketplace add yehudaseif/mtva-claude-skills
claude plugin install tva-newsletter@mtva-skills
pip3 install pillow
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

Constant Contact's API has no way to upload images, so the photos are put somewhere
public and the email links to them. Recommended: a Cloudflare R2 bucket (free at this volume).

1. Cloudflare dashboard → **R2** → **Create bucket** `tva-newsletter`.
2. Bucket → **Settings** → **Public access** → enable the **r2.dev subdomain**. Copy the
   `https://pub-….r2.dev` URL into `public_base_url`.
3. R2 → **Manage API tokens** → **Create API token** → permission **Object Read & Write**,
   only this bucket. Copy the **Access Key ID** and **Secret Access Key** into the config,
   and the **Account ID** (R2 overview page) into `account_id`.

No Cloudflare? Set `"image_host": {"type": "manual"}`. Each week the script then puts
the resized photos in `out/img/`; upload them to the Constant Contact Library, paste
each file's URL into `out/upload-urls.json`, and run it again. It works, but it is the
slow part — R2 makes it automatic.

## 5. Test it

```bash
python3 new_week.py --date <next Friday>
```
Put one paragraph and one photo in the MTVA folder and ask Claude to build the MTVA
newsletter and send you a test. Check it on your phone.

## What stays manual, on purpose

Scheduling the real send. Claude creates the draft and sends tests; a person reads
the test and gives the send time. `cc.py schedule` refuses to run without `--confirm`.
