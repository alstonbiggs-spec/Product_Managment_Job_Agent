import os, pandas as pd
from dotenv import load_dotenv
import anthropic

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
FILE = "jobs.xlsx"
MODEL = "claude-haiku-4-5-20251001"

resume = open("resume.txt", encoding="utf-8").read()

def score_job(row):
    prompt = f"""You are a career coach scoring how well a job fits a candidate.

RULES:
- Score 1-10 (10 = perfect fit).
- If the job requires far MORE years of experience or seniority than the
  candidate has, score it LOW (1-4) even if the skills match, and name the gap.
- Reward strong overlap in skills, industry, and seniority level.

CANDIDATE RESUME:
{resume}

JOB:
Title: {row['title']}
Company: {row['company']}
Location: {row['location']}
Description: {row.get('description', '')}

Respond on ONE line, using | as separators, EXACTLY like this:
SCORE|REASON (max 20 words)|TIP to tailor the application (max 20 words)"""
    msg = client.messages.create(
        model=MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()

def main():
    df = pd.read_excel(FILE)
    for col in ["score", "reason", "tip"]:
        if col not in df.columns:
            df[col] = ""
    # force these to text columns so we can write string values into them
    df[["score", "reason", "tip"]] = df[["score", "reason", "tip"]].astype("object")

    for i, row in df.iterrows():
        val = str(df.at[i, "score"]).strip().lower()
        if val not in ("", "nan"):
            continue  # already scored — skip to save money
        try:
            out = score_job(row)
            parts = [p.strip() for p in out.split("|")]
            df.at[i, "score"]  = parts[0] if len(parts) > 0 else ""
            df.at[i, "reason"] = parts[1] if len(parts) > 1 else out
            df.at[i, "tip"]    = parts[2] if len(parts) > 2 else ""
            print(f"{parts[0]:>4}  {row['title']} @ {row['company']}")
        except Exception as e:
            print(f"Error on {row['title']}: {e}")
    df.to_excel(FILE, index=False)
    print("\nDone. Open jobs.xlsx to see score, reason, and tip columns.")

if __name__ == "__main__":
    main()