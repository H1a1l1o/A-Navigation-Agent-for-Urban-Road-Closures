# 城市道路封闭导航智能体

运行环境为 Python 3.9 或以上，使用标准库。解压后在项目目录运行：

    python agent.py --out results
    python agent.py --demo 1

data 包含 Moving AI Lab 的柏林地图和场景文件，取自 DyMAB 镜像：
- https://movingai.com/benchmarks/mapf/
- https://github.com/amathsow/dymab/tree/main/maps/Berlin

代码按原场景文件顺序读取前 100 条起终点记录，每条独立执行。场景文件名虽含 random，实验过程没有随机抽样。封路按基线最短路上的固定索引设定，为模拟封路。trials.csv 保存每个任务及其封路边、预算与各策略的结果，summary.csv 按条件汇总。extra_moves 仅统计成功任务。


可视化需要额外安装 Pillow：

    python -m pip install Pillow
    python agent.py --out results --visualize

该命令重新运行实验并生成 results/experiment.png。图中上半部分为实际结果的到达率，下半部分重放第 1 个任务的三条封路条件，绘制基线路线、实际轨迹和封路位置。程序断言重放指标与该任务的 CSV 记录一致。图为仿真可视化输出。
