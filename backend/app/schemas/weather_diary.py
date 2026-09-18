"""气象日志校验规则。"""

from ..constants import WEATHER, WEATHER_SOURCE
from ..errors import ValidationError
from ..utils.dates import parse_date
from .common import PayloadValidator


def validate_weather_diary(payload):
    return (
        PayloadValidator(payload)
        .string("district", "行政区", required=True, max_length=64)
        .date("diary_date", "日期", required=True)
        .enum("weather", "实际天气", group=WEATHER, required=True)
        .number("rainfall_mm", "降雨量", min_value=0, max_value=2000)
        .enum("source", "数据来源", group=WEATHER_SOURCE, default="manual")
        .text("remark", "备注", max_length=500)
        .done()
    )


def validate_weather_check(payload):
    """养护记录表单实时核对入参：绿地 + 日期必填，其余可选。"""

    validator = (
        PayloadValidator(payload)
        .integer("green_space_id", "所属绿地", min_value=1)
        .integer("task_id", "关联任务", min_value=1)
        .date("record_date", "养护日期", required=True)
        .enum("weather", "天气", group=WEATHER)
        .text("work_content", "作业内容", max_length=4000)
        .done()
    )
    if not validator.get("green_space_id") and not validator.get("task_id"):
        raise ValidationError("核对失败", details={"green_space_id": "请先选择所属绿地或关联任务"})
    return validator

