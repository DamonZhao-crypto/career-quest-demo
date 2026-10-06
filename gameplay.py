"""Practice difficulty, answer scaffolds and rewards from real saved results."""

import json

DIFFICULTIES = {
    "新手引导": {
        "description": "从日常经历开始，一次只问一件事，提供答题思路。",
        "question_rule": "面向首次求职者。一次只问一个基础问题，最多80字。可使用课程、练习、社团或生活经历，不假设有工作经验。不要术语堆叠、复杂案例或多重追问。压力面只练习温和的澄清，不施压。追问只补充一个具体细节。",
        "score_rule": "新手训练：重点看是否回应问题、说清本人做法和具体例子。课程、社团、个人练习与工作经历同样可作证据。不要求资深知识或量化业务结果；不因学生身份扣分。缺乏相关证据仍应指出，不得虚构高分。",
        "pace": "建议表达 30–60 秒，不限时",
    },
    "标准挑战": {
        "description": "围绕岗位与项目展开，练习具体证据和工作判断。",
        "question_rule": "常规岗位面试。每题一个核心问题，最多120字，结合已有经历提问，不假设不存在的项目。追问围绕一个实际缺口，不同时问多个子问题。",
        "score_rule": "标准训练：看岗位相关性、具体行动、证据与表达结构。依据用户实际背景评分，不以资深岗位标准要求初级候选人。",
        "pace": "建议表达 60–90 秒，不限时",
    },
    "进阶模拟": {
        "description": "增加方案取舍与情境追问，检验专业深度。",
        "question_rule": "进阶岗位模拟。每题一个核心问题，最多150字，可加入一个约束条件考察取舍与专业深度，不虚构候选人经历。压力面尖锐但尊重，不羞辱或诱导歧视。",
        "score_rule": "进阶训练：除相关性与证据外，关注方案取舍、风险边界与推理。说明缺失的证据，不用篇幅替代质量。",
        "pace": "建议表达 60–120 秒，不限时",
    },
}

STAGE_HINTS = (
    ("建立第一印象", "说明你是谁 → 举一个相关经历 → 说清为什么想做这个岗位。", "没有工作经历也可以讲课程、社团或个人练习。"),
    ("拿出专业证据", "项目目标是什么 → 你负责什么 → 如何完成 → 结果或收获是什么。", "只讲实际做过的部分；不懂的地方可以说明并给出学习办法。"),
    ("说明你的判断", "先澄清目标 → 说明可选做法 → 给出选择理由 → 说如何协作。", "可以从一次小组合作或任务分工讲起。"),
    ("稳定完成应对", "先确认问题 → 给出观点 → 补充依据 → 说明尚不确定的部分。", "允许停顿和思考；这里没有倒计时，也不要求马上回答。"),
)


def difficulty_config(name):
    return DIFFICULTIES.get(name, DIFFICULTIES["标准挑战"])


def reward_summary(history):
    """20 XP per completed stage; first pass +30 and first 85+ +10 per track.

    A track is job + difficulty + stage. Old records count as standard practice.
    Repeated result keys never grant additional XP, including after a page refresh.
    """
    xp = 0
    passed, excellent, seen, completed = set(), set(), set(), []
    for row in history:
        try:
            feedback = json.loads(row["feedback"]) if isinstance(row["feedback"], str) else row["feedback"]
        except (ValueError, TypeError):
            feedback = {}
        metadata = feedback.get("_quest", {}) if isinstance(feedback, dict) else {}
        result_key = metadata.get("result_key")
        if result_key and result_key in seen:
            continue
        if result_key:
            seen.add(result_key)
        completed.append(row)
        track = (row.get("job", ""), metadata.get("difficulty", "标准挑战"), row["stage"])
        xp += 20
        if row["passed"] and track not in passed:
            passed.add(track)
            xp += 30
        if row["score"] >= 85 and track not in excellent:
            excellent.add(track)
            xp += 10
    level = xp // 100 + 1
    badges = []
    if completed:
        badges.append("迈出第一步")
    if passed:
        badges.append("首关突破")
    if excellent:
        badges.append("精彩表达")
    tracks = {}
    for job, difficulty, stage in passed:
        tracks.setdefault((job, difficulty), set()).add(stage)
    from agents import STAGES
    if any(all(stage["name"] in names for stage in STAGES) for names in tracks.values()):
        badges.append("全线通关")
    if len(completed) >= 5:
        badges.append("持续练习")
    return {"xp": xp, "level": level, "level_xp": xp % 100,
            "next_xp": 100 - xp % 100, "badges": badges, "completed": len(completed)}
