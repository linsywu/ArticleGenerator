"""Change 1：humanize 拆除的回归测试。"""


def test_trigger_humanize_task_removed():
    """模块 A：trigger_humanize celery 任务应已从 app.tasks 删除。"""
    from app import tasks

    assert not hasattr(tasks, "trigger_humanize"), (
        "trigger_humanize 应已删除——humanize 场景已并入 generate，"
        "不再有独立的去AI味任务。"
    )
