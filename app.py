import os
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, render_template, redirect, url_for, session, request
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv

from pattern import as_block
from news_gen import build_video

BASE_DIR = Path(__file__).parent
load_dotenv()  # loads FLASK_SECRET_KEY / GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET from .env

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")
oauth = OAuth(app)

# Use Google's OpenID discovery doc so Authlib knows token/userinfo/jwks endpoints
oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

def _ist_now_str():
    now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
    return now_ist.strftime("%a, %d %b %Y, %I:%M:%S %p IST")

@app.route("/")
def home():
    user = session.get("user")
    if not user:
        return render_template("index.html")
    return render_template(
        "logged_in.html",
        user=user,
        ist_time=_ist_now_str(),
        pattern_lines=None,
        video_url=None,
    )

@app.route("/login")
def login():
    redirect_uri = url_for("auth_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route("/auth/callback")
def auth_callback():
    # Exchanges code for tokens and validates ID token using jwks from discovery
    token = oauth.google.authorize_access_token()

    # Prefer user info from token if present; otherwise call Google's userinfo endpoint
    userinfo = token.get("userinfo")
    if not userinfo:
        resp = oauth.google.get("https://openidconnect.googleapis.com/v1/userinfo")
        userinfo = resp.json()

    session["user"] = {
        "name": userinfo.get("name"),
        "email": userinfo.get("email"),
        "picture": userinfo.get("picture"),
    }
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))

# Phase 2 (≤1 year path): Printing Design
@app.route("/pattern", methods=["POST"])
def pattern():
    if "user" not in session:
        return redirect(url_for("home"))
    try:
        n = int(request.form.get("lines", 1))
    except ValueError:
        n = 1
    n = min(max(n, 1), 100)  # clamp to 1..100
    block = as_block(n)
    return render_template(
        "logged_in.html",
        user=session["user"],
        ist_time=_ist_now_str(),
        pattern_lines=block,
        video_url=None,
    )

# Phase 2 (experienced): News Video Generator
@app.route("/generate", methods=["POST"])
def generate_video():
    if "user" not in session:
        return redirect(url_for("home"))

    files = request.files.getlist("media")[:5]
    if not files:
        return redirect(url_for("home"))

    uploads = BASE_DIR / "uploads"
    uploads.mkdir(exist_ok=True)
    saved = []
    for f in files:
        if not f.filename:
            continue
        p = uploads / f.filename
        f.save(p)
        saved.append(p)

    headline = request.form.get("headline") or "Breaking: Today’s top story"
    narration = (
        f"Good evening. Here are the top highlights. {headline}. "
        f"This report contains {len(saved)} items."
    )

    out_dir = BASE_DIR / "static" / "outputs"
    mp4 = build_video(saved, out_dir, headline=headline, narration=narration)
    rel = f"/static/outputs/{mp4.name}"

    return render_template(
        "logged_in.html",
        user=session["user"],
        ist_time=_ist_now_str(),
        pattern_lines=None,
        video_url=rel,
    )

if __name__ == "__main__":
    app.run(debug=True)
