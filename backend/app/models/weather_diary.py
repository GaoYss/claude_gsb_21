"""气象日志模型：按行政区记录每日实际天气，是养护记录天气核对的依据。"""

from ..constants import WEATHER, WEATHER_SOURCE
from ..extensions import db
from ..utils.dates import format_date, format_datetime
from ..utils.numbers import to_float
from .mixins import TimestampMixin


class WeatherDiary(TimestampMixin, db.Model):
    """某行政区某日的实际气象情况（人工登记或气象台批量导入）。"""

    __tablename__ = "weather_diary"
    __table_args__ = (
        db.UniqueConstraint("district", "diary_date", name="uq_weather_diary_district_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    district = db.Column(db.String(64), nullable=False, index=True)
    diary_date = db.Column(db.Date, nullable=False, index=True)
    weather = db.Column(db.String(16), nullable=False)
    rainfall_mm = db.Column(db.Numeric(8, 1, asdecimal=False))
    source = db.Column(db.String(16), nullable=False, default="manual")
    remark = db.Column(db.Text)

    @property
    def is_rainy(self):
        """记录天气为雨/雪，或有可测降雨量，即视为当日有降雨。"""

        if self.weather in {"rain", "snow"}:
            return True
        return self.rainfall_mm is not None and self.rainfall_mm > 0

    def to_dict(self, detail=False):
        data = {
            "id": self.id,
            "district": self.district,
            "diary_date": format_date(self.diary_date),
            "weather": self.weather,
            "weather_label": WEATHER.label(self.weather),
            "rainfall_mm": to_float(self.rainfall_mm),
            "is_rainy": self.is_rainy,
            "source": self.source,
            "source_label": WEATHER_SOURCE.label(self.source),
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }
        if detail:
            data["remark"] = self.remark
        return data
