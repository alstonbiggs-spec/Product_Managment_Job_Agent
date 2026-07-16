import subprocess, sys

for script in ["fetch_jobs.py", "score_jobs.py"]:
    print(f"\n=== Running {script} ===")
    subprocess.run([sys.executable, script], check=True)

print("\nDaily pull done — jobs saved and scored.")