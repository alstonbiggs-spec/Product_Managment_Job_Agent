import os, re, html, requests, pandas as pd
from dotenv import load_dotenv
load_dotenv()

APP_ID  = os.getenv("ADZUNA_APP_ID")
APP_KEY = os.getenv("ADZUNA_APP_KEY")
FILE = "jobs.xlsx"

# ---- ADZUNA (broad Texas search) ----
LOCATIONS = ["Austin", "Dallas", "Fort Worth"]
RADIUS_KM = 40

# ---- TARGET COMPANY BOARDS ----  ("greenhouse" | "lever" | "ashby", "token")
COMPANIES = [
    ("greenhouse", "cloudflare"),
    ("greenhouse", "appliedintuition"),
    ("greenhouse", "brex"),
    ("greenhouse", "databricks"),
    ("greenhouse", "datadog"),
    ("greenhouse", "figma"),
    ("greenhouse", "asana"),
    ("greenhouse", "affirm"),
    ("greenhouse", "andurilindustries"),
    ("greenhouse", "vannevarlabs"),
    ("lever", "palantir"),
    ("lever", "shieldai"),
    ("ashby", "Saronic"),
    ("ashby", "Ramp"),
    ("ashby", "plaid"),
]

TX_KEYWORDS = ["tx", "texas", "austin", "dallas", "fort worth",
               "houston", "san antonio", "round rock"]
COMPANY_LOC = TX_KEYWORDS + ["remote"]      # target companies: TX or remote
TITLE_KEYWORDS = ["product manager", "product management", "strategy", "product owner", "pm", "program manager", "program management"]

def is_pm(title):     return any(k in (title or "").lower() for k in TITLE_KEYWORDS)
def ok_loc(loc):      return any(k in (loc or "").lower() for k in COMPANY_LOC)
def strip_html(t):    return re.sub(r"<[^>]+>", " ", html.unescape(t or "")).strip()[:1500]

def get_adzuna_jobs(what="product manager", locations=LOCATIONS, radius_km=RADIUS_KM):
    jobs, seen = [], set()
    for where in locations:
        url = "https://api.adzuna.com/v1/api/jobs/us/search/1"
        params = {"app_id": APP_ID, "app_key": APP_KEY, "what": what,
                  "where": where, "distance": radius_km,
                  "results_per_page": 50, "max_days_old": 5}
        for r in requests.get(url, params=params).json().get("results", []):
            link = r["redirect_url"]
            if link in seen: continue
            seen.add(link)
            jobs.append({"title": r["title"], "company": r["company"]["display_name"],
                         "location": r["location"]["display_name"],
                         "salary_min": r.get("salary_min"), "salary_max": r.get("salary_max"),
                         "description": r.get("description",""), "url": link})
    return jobs

def get_greenhouse_jobs(token):
    r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true", timeout=20)
    if r.status_code != 200:
        print(f"  greenhouse/{token}: no data ({r.status_code})"); return []
    out = [{"title": j["title"], "company": token.title(),
            "location": j.get("location",{}).get("name",""),
            "salary_min": None, "salary_max": None,
            "description": strip_html(j.get("content","")), "url": j["absolute_url"]}
           for j in r.json().get("jobs", [])
           if is_pm(j["title"]) and ok_loc(j.get("location",{}).get("name",""))]
    print(f"  greenhouse/{token}: {len(out)} PM jobs")
    return out

def get_lever_jobs(token):
    r = requests.get(f"https://api.lever.co/v0/postings/{token}?mode=json", timeout=20)
    if r.status_code != 200:
        print(f"  lever/{token}: no data ({r.status_code})"); return []
    out = [{"title": j["text"], "company": token.title(),
            "location": j.get("categories",{}).get("location",""),
            "salary_min": None, "salary_max": None,
            "description": (j.get("descriptionPlain","") or "")[:1500], "url": j["hostedUrl"]}
           for j in r.json()
           if is_pm(j.get("text","")) and ok_loc(j.get("categories",{}).get("location",""))]
    print(f"  lever/{token}: {len(out)} PM jobs")
    return out

def get_ashby_jobs(token):
    r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{token}", timeout=20)
    if r.status_code != 200:
        print(f"  ashby/{token}: no data ({r.status_code})"); return []
    out = []
    for j in r.json().get("jobs", []):
        loc = j.get("location", "")
        if is_pm(j.get("title","")) and ok_loc(loc):
            desc = j.get("descriptionPlain") or strip_html(j.get("descriptionHtml",""))
            out.append({"title": j.get("title",""), "company": token.capitalize(),
                        "location": loc, "salary_min": None, "salary_max": None,
                        "description": (desc or "")[:1500],
                        "url": j.get("jobUrl") or j.get("applyUrl","")})
    print(f"  ashby/{token}: {len(out)} PM jobs")
    return out

def get_company_jobs():
    jobs = []
    print("Checking target company boards...")
    fn = {"greenhouse": get_greenhouse_jobs, "lever": get_lever_jobs, "ashby": get_ashby_jobs}
    for platform, token in COMPANIES:
        try: jobs += fn[platform](token)
        except Exception as e: print(f"  {platform}/{token}: error {e}")
    return jobs

def save_new_jobs(jobs):
    new = pd.DataFrame(jobs)
    if os.path.exists(FILE):
        old = pd.read_excel(FILE)
        truly_new = new[~new["url"].isin(old["url"])].copy()
        combined = pd.concat([old, new]).drop_duplicates(subset="url", keep="first")
    else:
        truly_new = new.copy(); combined = new.copy()
    if "Applied" not in combined.columns: combined["Applied"] = "No"
    combined["Applied"] = combined["Applied"].fillna("No")
    combined.to_excel(FILE, index=False)
    return truly_new

if __name__ == "__main__":
    jobs = get_adzuna_jobs() + get_company_jobs()
    print(f"\nFetched {len(jobs)} jobs total")
    new_jobs = save_new_jobs(jobs)
    print(f"{len(new_jobs)} were NEW and saved to {FILE}")