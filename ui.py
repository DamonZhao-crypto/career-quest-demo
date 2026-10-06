"""Native Streamlit presentation components for the interview workspace."""

import json
from pathlib import Path

import streamlit as st

from agents import PASS_SCORE, QUESTIONS_PER_STAGE, STAGES
from storage import delete_history, get_history
from gameplay import DIFFICULTIES, STAGE_HINTS, difficulty_config, reward_summary
QUEST_VERSION = 2

STAGE_TITLES = ("初识之门", "专业试炼", "协作议事厅", "应变终章")
STAGE_ROLES = ("HR 面试官", "专业面试官", "用人主管", "压力面试官")
STAGE_ICONS = ("waving_hand", "construction", "groups", "shield")
STAGE_DESCRIPTIONS = (
    "表达与动机，建立清晰的职业叙述。",
    "项目与技能，呈现具体的专业证据。",
    "协作与判断，说明你的工作思路。",
    "澄清与应变，练习稳定的临场表达。",
)


def navigate(page):
    """A callback runs before widgets are recreated on the next rerun."""
    st.session_state.workspace_page = page


def render_brand():
    assets = Path(__file__).with_name("assets")
    st.logo(str(assets / "brand.svg"), size="large", icon_image=str(assets / "mark.svg"))


def render_intro():
    st.caption("CAREER QUEST / 职业挑战地图")
    st.title("把面试练习，变成一次闯关。")
    st.write("遇见四位面试官，解锁你的职业路线。从新手引导开始，每次表达都有成长。")
    st.image(str(Path(__file__).with_name("assets") / "quest-map.svg"), width="stretch")
    columns = st.columns(3, gap="medium")
    for column, label, value in zip(columns, ("挑战关卡", "每轮任务", "通关目标"),
                                    (len(STAGES), len(STAGES) * QUESTIONS_PER_STAGE, PASS_SCORE)):
        column.metric(label, value, border=True)


def render_training_plan():
    with st.container(border=True):
        st.subheader("四关职业冒险")
        st.caption("完成当前关卡，下一位面试官才会登场。")
        for index, (title, description) in enumerate(zip(STAGE_TITLES, STAGE_DESCRIPTIONS)):
            st.markdown(f":material/{STAGE_ICONS[index]}: **0{index + 1} · {title}**")
            st.caption(STAGE_ROLES[index])
            st.caption(description)
        st.caption(f"每阶段 {QUESTIONS_PER_STAGE} 题 · 支持针对回答追问")
    with st.container(border=True):
        st.markdown(":material/stars: **完成任务，积累经验。**")
        st.caption("完成一关 +20 XP；同岗位、同难度、同关首次通关额外 +30 XP，首次达到 85 分额外 +10 XP。每 100 XP 升一级。")
        st.caption("经验与称号记录练习投入，不代表职业资格。")


def render_stage_route(game):
    columns = st.columns(len(STAGES), gap="small")
    for index, (column, title) in enumerate(zip(columns, STAGE_TITLES)):
        completed = index < game["stage_index"] or (
            index == game["stage_index"] and game["stage_result"]
            and game["stage_result"]["passed"]
        )
        with column.container(border=True):
            st.caption(f"关卡 0{index + 1} · {STAGE_ROLES[index]}")
            st.markdown(f":material/{STAGE_ICONS[index]}:")
            st.markdown(f"**{title}**")
            if completed:
                st.badge("已通关", color="green", icon=":material/check:")
            elif index == game["stage_index"]:
                st.badge("当前挑战" if not game["stage_result"] else "可重试", color="violet", icon=":material/flag:")
            else:
                st.badge("待解锁", color="gray", icon=":material/lock:")


def render_rewards(player_id):
    summary = reward_summary(get_history(player_id) if player_id else [])
    with st.container(border=True):
        with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
            st.markdown(f":material/stars: **练习者 Lv.{summary['level']}**")
            st.badge(f"{summary['xp']} XP", color="violet")
        st.progress(summary["level_xp"] / 100, text=f"再积累 {summary['next_xp']} XP 升级")
        if summary["badges"]:
            with st.container(horizontal=True):
                for badge in summary["badges"]:
                    st.badge(badge, color="orange", icon=":material/military_tech:")
        else:
            st.caption("完成第一关，解锁「迈出第一步」成就。")
        with st.expander("经验与成就规则"):
            st.caption("完成一关 +20 XP；同岗位、同难度、同关首次通关 +30 XP；首次 85 分 +10 XP。重试仍可获得完成经验，刷新页面不会重复奖励。旧记录按标准挑战计入。")
            st.caption("首关突破：任一关通关；精彩表达：任一关达到 85 分；全线通关：同岗位、同难度的四关均通关；持续练习：累计完成五次关卡。")
    return summary


def render_mission(game):
    index = game["stage_index"]
    mission, outline, note = STAGE_HINTS[index]
    mode = game.get("difficulty", "标准挑战")
    with st.container(border=True):
        st.markdown(f":material/flag: **本关任务 · {mission}**")
        st.caption(f"{mode} · {difficulty_config(mode)['pace']} · 两题均分 {PASS_SCORE} 分解锁下一关")
        with st.expander("答题思路卡", expanded=mode == "新手引导", icon=":material/lightbulb:"):
            st.write(outline)
            st.caption(note)
            st.caption("思路卡帮助组织真实经历。使用它不会扣分，回答长短也不直接决定得分。")


def render_feedback(feedback):
    with st.container(border=True):
        st.subheader("成长补给" if feedback else "面试补给站")
        if feedback:
            st.metric("回答得分", feedback["score"], help="由模型给出的练习参考评分。")
            for label, field in (("表现优势", "strength"), ("改进方向", "gap"), ("下一步练习", "training_task")):
                st.markdown(f"**{label}**")
                st.write(feedback[field])
        else:
            st.markdown("**先给结论，再说明理由。**")
            st.caption("用具体经历支撑观点，说明你做了什么，以及带来了怎样的结果。")
            st.markdown("**问题不清楚时，可以先澄清。**")
            st.caption("自然地表达思考过程，不必追求背诵式的标准答案。")


def render_profile(profile):
    with st.expander("本轮候选人画像", icon=":material/person:"):
        st.write(profile["summary"])
        st.caption("已识别技能")
        st.write("、".join(profile["skills"]) or "将通过本轮面试进一步了解。")
        st.caption("待深入了解")
        st.write("、".join(profile["gaps"]) or "将结合回答生成追问。")


def render_history(player_id, compact=False):
    history = get_history(player_id) if player_id else []
    if compact:
        with st.container(border=True):
            with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
                st.subheader("最近训练")
                st.button("查看全部", icon=":material/arrow_forward:",
                          on_click=navigate, args=("成长记录",), key="view_history")
            if history:
                for row in reversed(history[-3:]):
                    st.write(f"{row['created_at'][:10]}  ·  {row['stage']}  ·  {row['score']} 分")
            else:
                st.caption("完成第一个面试阶段后，这里会出现你的训练记录。")
        return

    if not history:
        with st.container(border=True):
            st.subheader("你的第一步，从一次练习开始。")
            st.write("当前存档还没有训练记录。完成一个面试阶段，即可查看得分和改进建议。")
            st.button("前往面试工作台", type="primary", icon=":material/arrow_forward:",
                      on_click=navigate, args=("面试工作台",))
        return

    render_rewards(player_id)
    tracks = sorted({(row.get("job", "—"), json.loads(row["feedback"]).get("_quest", {}).get("difficulty", "标准挑战"))
                     for row in history})
    selected_track = st.selectbox("复盘路线（岗位 / 难度）", tracks,
                                   format_func=lambda item: f"{item[0]} · {item[1]}", key="report_track")
    all_history = history
    history = [row for row in history if (row.get("job", "—"),
               json.loads(row["feedback"]).get("_quest", {}).get("difficulty", "标准挑战")) == selected_track]
    latest_by_stage = {row["stage"]: row for row in history}
    passed_stages = len({row["stage"] for row in history if row["passed"]})
    columns = st.columns(3)
    columns[0].metric("已完成练习", len(history), border=True)
    columns[1].metric("练习平均分", round(sum(row["score"] for row in history) / len(history)), border=True)
    columns[2].metric("已通关阶段", f"{passed_stages} / {len(STAGES)}", border=True)
    with st.container(border=True):
        st.subheader("每一次练习，都有迹可循。")
        st.caption("按完成顺序展示阶段得分。不同岗位、难度和阶段的评分不能直接等同，趋势仅作复盘参考。")
        st.line_chart({"阶段得分": [row["score"] for row in history]},
                      x_label="训练记录", y_label="得分")

    if all(stage["name"] in latest_by_stage for stage in STAGES):
        with st.container(border=True):
            st.subheader("个人成长报告")
            for stage in STAGES:
                row = latest_by_stage[stage["name"]]
                feedback = json.loads(row["feedback"])
                st.markdown(f"**{row['stage']} · {row['score']} 分**")
                st.write(feedback["gap"])
            weakest = min(latest_by_stage.values(), key=lambda row: row["score"])
            suggestion = json.loads(weakest["feedback"])["training_task"]
            st.markdown("**下一次，优先练习**")
            st.write(f"{weakest['stage']}：{suggestion}")

    with st.container(border=True):
        with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
            st.subheader("训练明细")
            report = {"player_id": player_id, "results": all_history}
            st.download_button("导出记录", icon=":material/download:",
                               data=json.dumps(report, ensure_ascii=False, indent=2),
                               file_name="career_quest_report.json", mime="application/json")
        rows = [{"日期（UTC）": row["created_at"][:10], "目标岗位": row.get("job", "—"),
                 "难度": json.loads(row["feedback"]).get("_quest", {}).get("difficulty", "标准挑战"),
                 "面试阶段": row["stage"], "得分": row["score"],
                 "结果": "已通关" if row["passed"] else "待提升"} for row in reversed(history[-20:])]
        st.dataframe(rows, hide_index=True, width="stretch")
        st.caption("显示当前路线最近 20 条记录；导出文件包含该存档的全部路线。评分仅供训练参考。")
    with st.expander("管理此存档", icon=":material/settings:"):
        st.caption("删除后无法恢复。此操作仅删除当前存档的成长记录。")
        confirmed = st.checkbox("我确认删除此存档的全部成长记录", key=f"delete_confirm_{player_id}")
        if st.button("删除成长记录", icon=":material/delete:", disabled=not confirmed):
            delete_history(player_id)
            st.rerun()


def render_help(recognition_location, public_demo=False):
    st.caption("职业准备 / 使用说明")
    st.title("准备好，开始一次真实的练习。")
    st.write("一轮训练包含四个面试阶段。用你的经历作答，让反馈成为下一次练习的起点。")
    for number, title, description in (
        ("01", "创建挑战", "填写目标岗位与经历，选择新手引导、标准挑战或进阶模拟。首次练习推荐新手引导。"),
        ("02", "完成面试", "阅读问题，或播放已启用的面试官语音。允许浏览器使用麦克风，再录音回答。"),
        ("03", "确认与提交", "点击识别录音，检查转写文字。必要时修改，然后提交评分。也可以直接输入文字回答。"),
        ("04", "解锁与成长", f"每关 {QUESTIONS_PER_STAGE} 题，平均分达到 {PASS_SCORE} 分解锁下一关。未通关可重试，没有生命值扣除。完成关卡即可积累经验、等级与成就。"),
    ):
        with st.container(border=True):
            st.subheader(f"{number} · {title}")
            st.write(description)
    with st.expander("关于语音与数据", icon=":material/info:"):
        st.write(f"录音由{recognition_location}的开源 Whisper 转成文字。首次识别需要下载并加载模型。")
        st.write("清晰优先使用 small 模型，首次下载约 486 MB；速度优先使用 base。可以填写专业词汇，并在提交前核对人名、术语、数字和否定词。轻声回答被漏掉时，可关闭静音过滤重试。")
        st.write("标出的片段只是模型不确定性提示，并非错误判定。没有提示也可能识别错；可回听录音与编辑文字。")
        st.write("简历和回答文字会交给所选文字模型分析。建议使用脱敏简历，不填写无关的个人信息。")
        st.write("公开体验版按会话隔离成长记录，关闭或刷新会话前请导出记录。暂不支持跨会话找回，服务器重建也可能清空记录。" if public_demo
                 else "存档编号用于查找记录，不是账号登录。请妥善保管自己的编号。")
        st.caption("面试评分用于练习反馈，不作为招聘或录用依据。")
    st.button("开始练习", type="primary", icon=":material/arrow_forward:",
              on_click=navigate, args=("面试工作台",))
