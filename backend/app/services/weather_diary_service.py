"""气象日志业务逻辑与养护记录天气核对。"""

from datetime import timedelta

from sqlalchemy import or_

from ..constants import WEATHER
from ..errors import ConflictError, ValidationError
from ..extensions import db
from ..models import GreenSpace, MaintenanceRecord, MaintenanceTask, WeatherDiary
from ..models.mixins import utcnow
from ..utils.dates import format_date
from ..utils.sorting import parse_sort
from .base_service import BaseService

# 浇灌类作业在「降雨当天 + 雨后 N 天」内登记时提示
RECENT_RAIN_DAYS = 2

WATER_KEYWORDS = ("浇灌", "浇水", "灌水", "浇透", "喷淋", "洒水")
DRAINAGE_KEYWORDS = ("排涝", "排水", "抽积水")


def _rainy_condition():
    return or_(
        WeatherDiary.weather.in_(("rain", "snow")),
        WeatherDiary.rainfall_mm > 0,
    )


def _is_watering(task_type, work_content):
    """判断作业是否属于浇灌（排涝类不算，雨后排水反而是必要作业）。"""

    content = work_content or ""
    if task_type == "water":
        return not any(word in content for word in DRAINAGE_KEYWORDS)
    return any(word in content for word in WATER_KEYWORDS)


class WeatherDiaryService(BaseService):
    """实际气象日志的维护与查询。"""

    model = WeatherDiary
    label = "气象日志"
    code_field = None

    SORTABLE_FIELDS = {
        "diary_date": WeatherDiary.diary_date,
        "created_at": WeatherDiary.created_at,
    }

    # ------------------------------------------------------------ 写入
    @classmethod
    def prepare_instance(cls, instance, payload):
        district = payload.get("district", instance.district)
        diary_date = payload.get("diary_date", instance.diary_date)
        if district and diary_date:
            existing = (
                db.session.query(WeatherDiary)
                .filter(
                    WeatherDiary.district == district,
                    WeatherDiary.diary_date == diary_date,
                )
                .first()
            )
            if existing is not None and existing.id != instance.id:
                raise ConflictError(
                    f"{district} {format_date(diary_date)} 的气象日志已存在，请直接编辑原记录"
                )

    # ------------------------------------------------------------ 批量导入
    @classmethod
    def import_entries(cls, entries):
        """按（行政区 + 日期）做 upsert，单条失败不影响其余数据。"""

        if not isinstance(entries, list) or not entries:
            raise ValidationError("导入失败", details={"items": "请提供至少一条气象日志"})

        created, updated = 0, 0
        failed = []
        affected_dates = {}
        for index, raw in enumerate(entries):
            try:
                from ..schemas import validate_weather_diary

                data = validate_weather_diary(raw)
            except ValidationError as exc:
                failed.append({"index": index, "errors": exc.details})
                continue
            existing = (
                db.session.query(WeatherDiary)
                .filter(
                    WeatherDiary.district == data["district"],
                    WeatherDiary.diary_date == data["diary_date"],
                )
                .first()
            )
            if existing is None:
                db.session.add(WeatherDiary(**data))
                created += 1
            else:
                for field, value in data.items():
                    setattr(existing, field, value)
                updated += 1
            affected_dates.setdefault(data["district"], set()).add(data["diary_date"])
        db.session.flush()
        for district, dates in affected_dates.items():
            for diary_date in dates:
                cls.resync_records(district, diary_date)
        db.session.commit()
        return {"created": created, "updated": updated, "failed": failed}

    # ------------------------------------------------------------ 查询
    @classmethod
    def _apply_filters(cls, query, filters):
        district = (filters.get("district") or "").strip()
        if district:
            query = query.filter(WeatherDiary.district == district)
        if filters.get("weather"):
            query = query.filter(WeatherDiary.weather == filters["weather"])
        if filters.get("source"):
            query = query.filter(WeatherDiary.source == filters["source"])
        if filters.get("rainy"):
            query = query.filter(_rainy_condition())
        if filters.get("date_from"):
            query = query.filter(WeatherDiary.diary_date >= filters["date_from"])
        if filters.get("date_to"):
            query = query.filter(WeatherDiary.diary_date <= filters["date_to"])
        return query

    @classmethod
    def list_diaries(cls, filters, args):
        query = cls._apply_filters(db.session.query(WeatherDiary), filters)
        return query.order_by(
            parse_sort(args, cls.SORTABLE_FIELDS, WeatherDiary.diary_date.desc())
        )

    @classmethod
    def get_diary(cls, district, diary_date):
        return (
            db.session.query(WeatherDiary)
            .filter(WeatherDiary.district == district, WeatherDiary.diary_date == diary_date)
            .first()
        )

    @classmethod
    def recent_rain(cls, district, record_date, days=RECENT_RAIN_DAYS):
        """作业日期当天及之前 N 天内（含当天）的降雨日志，按日期升序。"""

        return (
            db.session.query(WeatherDiary)
            .filter(
                WeatherDiary.district == district,
                WeatherDiary.diary_date >= record_date - timedelta(days=days),
                WeatherDiary.diary_date <= record_date,
                _rainy_condition(),
            )
            .order_by(WeatherDiary.diary_date.asc())
            .all()
        )

    # ------------------------------------------------------------ 天气核对
    @classmethod
    def cross_check(cls, green_space_id, record_date, *, weather=None, task_id=None,
                    task_type=None, work_content=None):
        """核对某次养护作业的登记天气与实际气象，并给出浇灌提示。

        返回结构同时服务于表单预览接口与入库时的自动标注。
        """

        result = {
            "district": None,
            "record_date": format_date(record_date),
            "diary": None,
            "actual_weather": None,
            "actual_weather_label": None,
            "suggested_weather": None,
            "weather_match": "pending",
            "warnings": [],
            "conflict_note": None,
        }
        space = None
        if green_space_id:
            space = db.session.get(GreenSpace, green_space_id)
        elif task_id:
            task = db.session.get(MaintenanceTask, task_id)
            if task is not None:
                space = task.green_space
                green_space_id = task.green_space_id
                if task_type is None:
                    task_type = task.task_type
        if space is None or not record_date:
            return result
        result["district"] = space.district

        if task_type is None and task_id:
            task = db.session.get(MaintenanceTask, task_id)
            task_type = task.task_type if task else None

        diary = cls.get_diary(space.district, record_date)
        if diary is not None:
            result["diary"] = diary.to_dict(detail=True)
            result["actual_weather"] = diary.weather
            result["actual_weather_label"] = WEATHER.label(diary.weather)
            result["suggested_weather"] = diary.weather
            if not weather:
                result["weather_match"] = "pending"
            elif weather == diary.weather:
                result["weather_match"] = "consistent"
            else:
                result["weather_match"] = "mismatch"

        notes = []
        if diary is not None and weather and weather != diary.weather:
            notes.append(
                f"登记天气「{WEATHER.label(weather)}」与{space.district}"
                f"{format_date(record_date)}实际气象「{WEATHER.label(diary.weather)}」"
                "不一致，登记时已提示核对，按填报内容留存"
            )

        if _is_watering(task_type, work_content):
            rain_diaries = cls.recent_rain(space.district, record_date)
            if rain_diaries:
                rain_text = "、".join(
                    f"{format_date(item.diary_date)}（{WEATHER.label(item.weather)}"
                    + (f"，降雨量 {to_float_text(item.rainfall_mm)}mm" if item.rainfall_mm else "")
                    + "）"
                    for item in rain_diaries
                )
                warning = (
                    f"浇灌类作业登记时发现{rain_text}有降雨（降雨当天及雨后"
                    f"{RECENT_RAIN_DAYS} 天内），请核实是否确有必要浇灌"
                )
                result["warnings"].append(warning)
                notes.append(warning + "，仍保留登记")

        if diary is None:
            result["weather_match"] = "unavailable"
        result["conflict_note"] = "；".join(notes) if notes else None
        return result

    @classmethod
    def prepare_update(cls, instance, payload):
        setattr(instance, "_previous_key", (instance.district, instance.diary_date))
        cls.prepare_instance(instance, payload)

    @classmethod
    def after_create(cls, instance, payload):
        cls.resync_records(instance.district, instance.diary_date)

    @classmethod
    def after_update(cls, instance, payload):
        previous = getattr(instance, "_previous_key", None)
        if previous:
            cls.resync_records(*previous)
        cls.resync_records(instance.district, instance.diary_date)

    @classmethod
    def delete(cls, obj_id):
        # 先记录键值：flush 删除后实例属性可能已过期
        instance = cls.get(obj_id)
        district, diary_date = instance.district, instance.diary_date
        db.session.delete(instance)
        db.session.flush()
        cls.resync_records(district, diary_date)
        db.session.commit()
        return instance

    @classmethod
    def resync_records(cls, district, diary_date):
        """气象日志变动后回查相关养护记录。

        窗口取作业日期当天及其后 RECENT_RAIN_DAYS 天：补录某天的降雨日志后，
        之后两日内登记的浇灌记录也要补上雨后提示；删除日志则解除提示。
        """

        records = (
            db.session.query(MaintenanceRecord)
            .join(GreenSpace, GreenSpace.id == MaintenanceRecord.green_space_id)
            .filter(
                GreenSpace.district == district,
                MaintenanceRecord.record_date >= diary_date,
                MaintenanceRecord.record_date <= diary_date + timedelta(days=RECENT_RAIN_DAYS),
            )
            .all()
        )
        for record in records:
            cls.apply_check_to_record(
                record,
                {},
                task_id=record.task_id,
                green_space_id=record.green_space_id,
                record_date=record.record_date,
            )
        return len(records)

    @classmethod
    def apply_check_to_record(cls, instance, payload, *, task_id, green_space_id, record_date):
        """入库前把核对结论写到养护记录上（create/update 共用）。

        未填报天气但当日有气象日志时，自动按实际气象回填，保证登记天气与实际一致。
        """

        def _run():
            return cls.cross_check(
                green_space_id,
                record_date,
                weather=instance.weather,
                task_id=task_id,
                work_content=instance.work_content,
            )

        check = _run()
        if check["diary"] and not instance.weather:
            instance.weather = check["actual_weather"]
            check = _run()
        instance.weather_match = check["weather_match"]
        instance.weather_conflict_note = check["conflict_note"]
        instance.weather_checked_at = utcnow() if check["diary"] else None
        return check


def to_float_text(value):
    if value is None:
        return ""
    return f"{float(value):g}"
