"""Change 1：humanize 拆除的回归测试。"""


def test_trigger_humanize_task_removed():
    """模块 A：trigger_humanize celery 任务应已从 app.tasks 删除。"""
    from app import tasks

    assert not hasattr(tasks, "trigger_humanize"), (
        "trigger_humanize 应已删除——humanize 场景已并入 generate，"
        "不再有独立的去AI味任务。"
    )


import inspect


def test_trigger_generate_does_not_call_humanize():
    """模块 A：trigger_generate 不再发起 humanize /chat 调用。"""
    from app import tasks

    src = inspect.getsource(tasks.trigger_generate)
    assert "humanize" not in src, (
        "trigger_generate 不应再包含任何 humanize 调用——生成完直接落库，"
        "去AI味要求已在 generate 提示词中。"
    )


def test_trigger_generate_still_triggers_reviews():
    """模块 A：删除 humanize 后，质量/合规评审仍被触发（基于 generate 原文）。"""
    from app import tasks

    src = inspect.getsource(tasks.trigger_generate)
    assert "trigger_quality_review" in src, "质量评审触发不应被误删"
    assert "trigger_compliance_review" in src, "合规评审触发不应被误删"
