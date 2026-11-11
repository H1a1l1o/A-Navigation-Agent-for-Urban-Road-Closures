"""Evaluate navigation with fixed disruptions on a Moving AI benchmark."""
import argparse
import csv
from collections import deque
from itertools import islice
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
POLICIES = ("fixed", "reactive", "memory", "oracle")
LEVELS = (0, 1, 3)


def edge(a, b):
    return (a, b) if a < b else (b, a)


def load_map(path):
    lines = path.read_text().splitlines()
    height, width = (int(lines[i].split()[1]) for i in (1, 2))
    grid = lines[4:]
    if lines[3] != "map" or len(grid) != height or any(len(row) != width for row in grid):
        raise ValueError("Invalid Moving AI map dimensions")
    free = {(x, y) for y, row in enumerate(grid) for x, c in enumerate(row) if c in ".GS"}
    return {p: tuple((p[0] + dx, p[1] + dy) for dx, dy in ((1,0),(0,1),(-1,0),(0,-1))
                     if (p[0] + dx, p[1] + dy) in free) for p in free}


def plan(graph, start, goal, blocked):
    queue = deque([start])
    parent = {start: None}
    while queue:
        point = queue.popleft()
        if point == goal:
            route = []
            while parent[point] is not None:
                route.append(point)
                point = parent[point]
            return route[::-1]
        for nxt in graph[point]:
            if nxt not in parent and (not blocked or edge(point, nxt) not in blocked):
                parent[nxt] = point
                queue.append(nxt)
    return None


def run(graph, start, goal, blocked, baseline, optimal, policy, budget, trace=False, trajectory=None):
    position = start
    route = deque(optimal if policy == "oracle" else baseline)
    known = set()
    plans = {}
    attempts = hits = 0
    while route and attempts < budget:
        nxt = route.popleft()
        attempts += 1
        attempted = edge(position, nxt)
        failed = attempted in blocked
        if trace:
            print(attempts, position, nxt, "blocked" if failed else "open")
        if not failed:
            position = nxt
            if trajectory is not None:
                trajectory.append(position)
            continue
        hits += 1
        if policy == "fixed":
            break
        if policy == "reactive":
            known.clear()
        known.add(attempted)
        key = position, frozenset(known)
        if key not in plans:
            plans[key] = plan(graph, position, goal, known)
        route = deque(plans[key] or [])
    return dict(success=int(position == goal), attempts=attempts, hits=hits, moves=attempts-hits)


def evaluate(data, demo):
    graph = load_map(data / "Berlin_1_256.map")
    rows, skipped = [], []
    with (data / "Berlin_1_256-random-1.scen").open() as f:
        next(f)
        for number, line in enumerate(islice(f, 100), 1):
            if demo is not None and number != demo:
                continue
            _, _, _, _, x, y, gx, gy, _ = line.split()
            start, goal = (int(x), int(y)), (int(gx), int(gy))
            baseline = plan(graph, start, goal, set())
            if baseline is None or len(baseline) < 4:
                skipped.append(number)
                continue
            length = len(baseline)
            route = [start, *baseline]
            links = [edge(a, b) for a, b in zip(route, route[1:])]
            triple = [links[length * k // 4] for k in (1, 2, 3)]
            largest = plan(graph, start, goal, set(triple))
            if largest is None:
                skipped.append(number)
                continue
            budget = 2 * length + 20
            cases = [(set(), baseline), ({triple[1]}, plan(graph, start, goal, {triple[1]})),
                     (set(triple), largest)]
            for level, (blocked, optimal) in zip(LEVELS, cases):
                for policy in POLICIES:
                    if demo is not None:
                        print(f"scenario={number} closures={level} policy={policy} budget={budget}")
                    result = run(graph, start, goal, blocked, baseline, optimal,
                                 policy, budget, trace=demo is not None)
                    rows.append(dict(scenario=number, start=start, goal=goal,
                                     closures=level, edges=sorted(blocked), policy=policy,
                                     baseline=length, optimal=len(optimal), budget=budget, **result))
    return rows, skipped


def summarize(rows):
    summary = []
    for level in LEVELS:
        for policy in POLICIES:
            group = [r for r in rows if r["closures"] == level and r["policy"] == policy]
            successes = [r for r in group if r["success"]]
            summary.append(dict(
                closures=level, policy=policy, successes=len(successes), tasks=len(group),
                mean_hits=round(sum(r["hits"] for r in group) / len(group), 3),
                mean_attempts=round(sum(r["attempts"] for r in group) / len(group), 3),
                extra_moves=round(sum(r["moves"] - r["optimal"] for r in successes)
                                  / len(successes), 3) if successes else ""))
    return summary


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--out", type=Path, default=Path("results"))
    parser.add_argument("--demo", type=int, metavar="SCENARIO")
    parser.add_argument("--visualize", action="store_true", help="Save experiment.png (requires Pillow)")
    args = parser.parse_args()
    rows, skipped = evaluate(args.data, args.demo)
    if not rows:
        parser.error("No eligible scenarios")
    if args.demo is None:
        args.out.mkdir(parents=True, exist_ok=True)
        write_csv(args.out / "trials.csv", rows)
        write_csv(args.out / "summary.csv", summarize(rows))
    if args.visualize:
        from visualize import render
        render(rows, args.data, args.out)
    print(f"Runs: {len(rows)}; excluded scenario rows: {skipped}")


if __name__ == "__main__":
    main()

