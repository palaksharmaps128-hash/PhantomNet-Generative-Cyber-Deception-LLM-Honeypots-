"""Blind manual realism rating of LLM answers from two models.

Run after:
    python evaluate.py --model gemini-3.1-flash-lite --tag final
    python evaluate.py --model gemini-3.5-flash --tag final
Then:
    python rate.py
"""
import csv
import os
import random
import statistics

FILES = {
    "gemini-3.1-flash-lite": "evaluation/results_gemini-3.1-flash-lite_final.csv",
    "gemini-3.5-flash": "evaluation/results_gemini-3.5-flash_final.csv",
}
COUNT = 8
OUT = "evaluation/manual_ratings.csv"


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ask_rating(label):
    while True:
        value = input(f"Rate answer {label} (1-5): ").strip()
        if value in {"1", "2", "3", "4", "5"}:
            return int(value)
        print("Please type a number from 1 to 5.")


names = list(FILES)
runs = {n: {(r["scenario"], r["command"]): r for r in load(p)} for n, p in FILES.items()}
first, second = names
candidates = [
    key for key, r in runs[first].items()
    if r["source"] == "llm" and key[0] != "safety"
    and key in runs[second] and runs[second][key]["source"] == "llm"
]
step = max(1, len(candidates) // COUNT)
chosen = candidates[::step][:COUNT]

print("Blind rating: you do not see which model wrote which answer.")
print("1 = clearly fake or wrong")
print("3 = plausible, but something looks odd")
print("5 = looks exactly like a real Ubuntu server\n")

rng = random.Random(2026)
ratings = []
for i, key in enumerate(chosen, 1):
    order = [first, second]
    rng.shuffle(order)
    print("=" * 60)
    print(f"Command {i}/{len(chosen)}:  {key[1]}")
    for label, model in zip("AB", order):
        print(f"--- Answer {label} ---")
        print(runs[model][key]["output_full"][:700] or "(empty)")
    for label, model in zip("AB", order):
        ratings.append({"command": key[1], "model": model, "rating": ask_rating(label)})
    print()

os.makedirs("evaluation", exist_ok=True)
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["command", "model", "rating"])
    w.writeheader()
    w.writerows(ratings)

print("=" * 60)
print("Average realism rating (1-5):")
for n in names:
    vals = [r["rating"] for r in ratings if r["model"] == n]
    print(f"  {n}: {statistics.mean(vals):.2f}  ({len(vals)} ratings)")
print(f"\nSaved: {OUT}")