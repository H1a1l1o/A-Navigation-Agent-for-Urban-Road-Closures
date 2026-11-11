"""Render actual evaluation rows and a replayed path with Pillow."""
import ast
from pathlib import Path


def render(rows, data, output):
    from PIL import Image, ImageDraw, ImageFont
    from agent import load_map, plan, run, summarize

    image = Image.new("RGB", (1800, 1400), "white")
    draw = ImageDraw.Draw(image)
    def font(size):
        candidates = [Path("C:/Windows/Fonts/simsun.ttc"),
                      Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]
        for path in candidates:
            if path.exists():
                return ImageFont.truetype(str(path), size)
        return ImageFont.load_default()
    def text(x, y, value, size=28, fill="#233549"):
        draw.text((x, y), str(value), font=font(size), fill=fill)
    text(65, 35, "柏林道路导航实验  100 个任务 × 3 种封路条件 × 4 种策略", 37)
    text(65, 95, "仿真实验运行结果  四邻接广度优先搜索  固定封路规则", 27)
    summary = summarize(rows)
    colors = ["#6d8094", "#d48b2c", "#237eae", "#589747"]
    policies = ["fixed", "reactive", "memory", "oracle"]
    text(65, 165, "任务到达率（%）", 32)
    for i, level in enumerate((0, 1, 3)):
        group = [r for r in summary if r["closures"] == level]
        for j, row in enumerate(group):
            x = 150 + i * 490 + j * 87
            height = 2.3 * 100 * row["successes"] / row["tasks"]
            draw.rectangle((x, 500-height, x+62, 500), fill=colors[j])
            text(x, 460-height, f'{row["successes"]}%', 23)
        text(210+i*490, 520, f"{level} 条封路", 26)
    for j, policy in enumerate(policies):
        x = 180+j*380
        draw.rectangle((x, 585, x+25, 610), fill=colors[j])
        text(x+38, 580, {"fixed":"固定路线", "reactive":"即时重规划", "memory":"带记忆重规划", "oracle":"全知最短路"}[policy], 27)

    example = next(r for r in rows if r["scenario"] == 1 and r["closures"] == 3 and r["policy"] == "memory")
    start, goal, blocked = example["start"], example["goal"], set(example["edges"])
    graph = load_map(data / "Berlin_1_256.map")
    baseline = plan(graph, start, goal, set())
    optimal = plan(graph, start, goal, blocked)
    trajectory = [start]
    replay = run(graph, start, goal, blocked, baseline, optimal,
                 "memory", example["budget"], trajectory=trajectory)
    assert all(replay[k] == example[k] for k in replay)
    all_points = [*trajectory, *baseline, start, goal]
    xmin = max(0, min(x for x,y in all_points)-8)
    ymin = max(0, min(y for x,y in all_points)-8)
    xmax = min(255, max(x for x,y in all_points)+8)
    ymax = min(255, max(y for x,y in all_points)+8)
    scale = min(850/(xmax-xmin+1), 620/(ymax-ymin+1))
    ox, oy = 65, 720
    def point(p):
        return ox+(p[0]-xmin+.5)*scale, oy+(p[1]-ymin+.5)*scale
    for y in range(ymin, ymax+1):
        for x in range(xmin, xmax+1):
            if (x,y) not in graph:
                px,py=point((x,y))
                draw.rectangle((px-scale/2,py-scale/2,px+scale/2,py+scale/2),fill="#b9c0c7")
    draw.line([point(p) for p in [start,*baseline]], fill="#d48b2c", width=4)
    draw.line([point(p) for p in trajectory], fill="#237eae", width=3)
    for a,b in blocked:
        ax,ay=point(a)
        bx,by=point(b)
        cx,cy=(ax+bx)/2,(ay+by)/2
        draw.line((cx-7,cy-7,cx+7,cy+7), fill="#c22f34", width=4)
        draw.line((cx-7,cy+7,cx+7,cy-7), fill="#c22f34", width=4)
    for p, label, color in ((start,"起","#20743d"),(goal,"终","#8a258a")):
        px,py=point(p)
        draw.ellipse((px-7,py-7,px+7,py+7),fill=color)
        text(px+10,py-25,label,25,color)
    text(65, 660, "任务 1  带记忆重规划  三条封路  局部地图", 29)
    text(1010, 725, "依据实验记录重放的运行结果", 31)
    for y, line in enumerate([
        f"起点 {start}  终点 {goal}",
        f"到达成功  动作预算 {example['budget']}",
        f"尝试 {replay['attempts']} 次  受阻 {replay['hits']} 次",
        f"成功移动 {replay['moves']} 步  最短距离 {len(optimal)} 步",
        "橙色  初始规划路线",
        "蓝色  实际执行路线",
        "红叉  模拟封闭路段",
        "灰色  地图障碍物",
        "起  起点    终  终点",
        "重放指标已与实验记录核对"]):
        text(1010, 790+y*49, line, 26)
    output.mkdir(parents=True, exist_ok=True)
    image.save(output / "experiment.png")

