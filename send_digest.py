import os, smtplib, pandas as pd
from email.mime.text import MIMEText
from dotenv import load_dotenv
load_dotenv()

FILE = "jobs.xlsx"
MIN_SCORE = 7

def to_num(x):
    s, num = str(x).strip(), ""
    for c in s:
        if c.isdigit(): num += c
        elif num: break
    return int(num) if num else 0

def fmt_salary(r):
    lo, hi = r.get("salary_min"), r.get("salary_max")
    try:
        lo, hi = int(lo), int(hi)
        return f"${lo:,} – ${hi:,}"
    except (ValueError, TypeError):
        return "Not listed"

def build_html(df):
    rows = ""
    for _, r in df.iterrows():
        rows += f"""
        <div style="margin-bottom:14px;padding:12px;border-left:5px solid #2e7d32;background:#f5f8f5;font-family:Arial">
          <div style="font-size:16px"><b>{r['score']}/10 — {r['title']}</b> @ {r['company']}</div>
          <div style="color:#666">{r['location']}</div>
          <div style="color:#1a5e1a"><b>Salary:</b> {fmt_salary(r)}</div>
          <div style="margin:6px 0"><i>{r['reason']}</i></div>
          <div><b>Tip:</b> {r['tip']}</div>
          <a href="{r['url']}">View / Apply &rarr;</a>
        </div>"""
    return f"<h2 style='font-family:Arial'>Your PM matches this week ({len(df)})</h2>{rows}"

def send(html, count):
    msg = MIMEText(html, "html")
    msg["Subject"] = f"Your weekly PM jobs — {count} new matches"
    msg["From"] = os.getenv("GMAIL_ADDRESS")
    msg["To"]   = os.getenv("EMAIL_TO")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(os.getenv("GMAIL_ADDRESS"), os.getenv("GMAIL_APP_PASSWORD"))
        s.send_message(msg)

def main():
    df = pd.read_excel(FILE)
    if "Emailed" not in df.columns:
        df["Emailed"] = "No"
    df["Emailed"] = df["Emailed"].fillna("No")
    df["score_num"] = df["score"].apply(to_num)

    mask = ((df["score_num"] >= MIN_SCORE) &
            (df["Applied"].astype(str).str.lower() != "yes") &
            (df["Emailed"].astype(str).str.lower() != "yes"))
    picks = df[mask].sort_values("score_num", ascending=False)

    if picks.empty:
        print("No new matches to email this week.")
        return

    send(build_html(picks), len(picks))
    df.loc[mask, "Emailed"] = "Yes"                 # remember what we sent
    df.drop(columns=["score_num"]).to_excel(FILE, index=False)
    print(f"Emailed you {len(picks)} new matches and marked them Emailed.")

if __name__ == "__main__":
    main()