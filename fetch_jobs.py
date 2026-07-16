import os, requests, pandas as pd
from dotenv import load_dotenv
load_dotenv()

APP_ID  = os.getenv("ADZUNA_APP_ID")
APP_KEY = os.getenv("ADZUNA_APP_KEY")
FILE = "jobs.xlsx"

# ---- EDIT THESE TWO LINES ----
LOCATIONS = ["Austin", "Dallas", "Fort Worth"]   # center cities
RADIUS_KM = 40                                    # ~25 miles around each
# -------------------------------

def get_adzuna_jobs(what="product manager", locations=LOCATIONS, radius_km=RADIUS_KM):
    jobs, seen = [], set()
    for where in locations:
        url = "https://api.adzuna.com/v1/api/jobs/us/search/1"
        params = {"app_id": APP_ID, "app_key": APP_KEY,
                  "what": what, "where": where, "distance": radius_km,
                  "results_per_page": 50, "max_days_old": 5}
        data = requests.get(url, params=params).json()
        for r in data.get("results", []):
            link = r["redirect_url"]
            if link in seen:
                continue           # skip jobs that overlap between city circles
            seen.add(link)
            jobs.append({
                "title": r["title"],
                "company": r["company"]["display_name"],
                "location": r["location"]["display_name"],
                "salary_min": r.get("salary_min"),
                "salary_max": r.get("salary_max"),
                "description": r.get("description", ""),
                "url": link,
            })
    return jobs

def save_new_jobs(jobs):
    new = pd.DataFrame(jobs)
    if os.path.exists(FILE):
        old = pd.read_excel(FILE)
        truly_new = new[~new["url"].isin(old["url"])].copy()
        combined = pd.concat([old, new]).drop_duplicates(subset="url", keep="first")
    else:
        truly_new = new.copy()
        combined = new.copy()
    if "Applied" not in combined.columns:
        combined["Applied"] = "No"
    combined["Applied"] = combined["Applied"].fillna("No")
    combined.to_excel(FILE, index=False)
    return truly_new

if __name__ == "__main__":
    jobs = get_adzuna_jobs()
    print(f"Fetched {len(jobs)} jobs across {len(LOCATIONS)} areas")
    new_jobs = save_new_jobs(jobs)
    print(f"{len(new_jobs)} were NEW and saved to {FILE}")