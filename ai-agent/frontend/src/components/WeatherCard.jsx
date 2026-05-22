import "./WeatherCard.css";

const WEEKDAYS = ["週日", "週一", "週二", "週三", "週四", "週五", "週六"];

function WindLevel(speed) {
  if (speed == null) return "—";
  if (speed < 5)  return "微風";
  if (speed < 15) return "輕風";
  if (speed < 30) return "中風";
  if (speed < 50) return "強風";
  return "暴風";
}

function HumidityLabel(h) {
  if (h == null) return "—";
  if (h < 30) return "乾燥";
  if (h < 60) return "舒適";
  if (h < 80) return "偏濕";
  return "潮濕";
}

function tempColor(t) {
  if (t == null) return "#64748b";
  if (t >= 35) return "#ef4444";
  if (t >= 30) return "#f97316";
  if (t >= 25) return "#eab308";
  if (t >= 20) return "#3b82f6";
  return "#06b6d4";
}

// ── 多天預報表格 ────────────────────────────────────────────────
function ForecastGrid({ city, country, date_label, forecast }) {
  // 計算溫度範圍（給色條用）
  const allMax = forecast.map(d => d.temp_max).filter(Boolean);
  const allMin = forecast.map(d => d.temp_min).filter(Boolean);
  const rangeMax = Math.max(...allMax);
  const rangeMin = Math.min(...allMin);
  const rangeSpan = rangeMax - rangeMin || 1;

  return (
    <div className="weather-card weather-forecast-multi">
      {/* 標題 */}
      <div className="forecast-header">
        <div>
          <div className="weather-city">{city}</div>
          {country && <div className="weather-country">{country}</div>}
        </div>
        <div className="label-week">📅 {date_label}</div>
      </div>

      {/* 預報列表 */}
      <div className="forecast-grid">
        {forecast.map((day, i) => {
          const d     = new Date(day.date + "T12:00:00");
          const wday  = WEEKDAYS[d.getDay()];
          const mmdd  = `${d.getMonth() + 1}/${d.getDate()}`;
          const isToday = i === 0;

          // 溫度色條位置
          const barLeft  = ((day.temp_min - rangeMin) / rangeSpan) * 100;
          const barWidth = ((day.temp_max - day.temp_min) / rangeSpan) * 100;

          return (
            <div key={day.date} className={`forecast-row ${isToday ? "forecast-today" : ""}`}>
              {/* 日期 */}
              <div className="fc-day">
                <span className="fc-wday">{isToday ? "今天" : wday}</span>
                <span className="fc-date">{mmdd}</span>
              </div>

              {/* 天氣 emoji + 狀況 */}
              <div className="fc-cond">
                <span className="fc-emoji">{day.emoji}</span>
                <span className="fc-label">{day.condition}</span>
              </div>

              {/* 降雨機率 */}
              <div className="fc-rain">
                {day.precip_prob != null
                  ? <span style={{ color: day.precip_prob >= 50 ? "#3b82f6" : "#94a3b8" }}>
                      💧{day.precip_prob}%
                    </span>
                  : "—"}
              </div>

              {/* 溫度色條 */}
              <div className="fc-temp-bar-wrap">
                <span className="fc-temp-min" style={{ color: tempColor(day.temp_min) }}>
                  {day.temp_min}°
                </span>
                <div className="fc-temp-bar-track">
                  <div
                    className="fc-temp-bar-fill"
                    style={{
                      left:  `${barLeft}%`,
                      width: `${barWidth}%`,
                      background: `linear-gradient(to right, ${tempColor(day.temp_min)}, ${tempColor(day.temp_max)})`,
                    }}
                  />
                </div>
                <span className="fc-temp-max" style={{ color: tempColor(day.temp_max) }}>
                  {day.temp_max}°
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="weather-source">資料來源：Open-Meteo・日預報</div>
    </div>
  );
}

// ── 單日天氣卡（今天 / 明天）───────────────────────────────────
export default function WeatherCard({ data }) {
  // 有 forecast 陣列 → 多天預報
  if (data.forecast) {
    return <ForecastGrid {...data} />;
  }

  const {
    city, country, temperature, temp_min, feels_like,
    humidity, wind_speed, precipitation, condition, emoji,
    date_label,
  } = data;

  const isTomorrow = date_label?.includes("明天");

  return (
    <div className={`weather-card ${isTomorrow ? "weather-forecast" : ""}`}>
      {/* 日期標籤 */}
      {date_label && (
        <div className={`weather-date-label ${isTomorrow ? "label-tomorrow" : "label-today"}`}>
          {isTomorrow ? "📅 明天預報" : "🕐 即時天氣"}
          <span className="weather-date-time">
            {date_label.replace(/今天|明天/, "").replace(/[（）()]/g, "")}
          </span>
        </div>
      )}

      <div className="weather-top">
        <div>
          <div className="weather-city">{city}</div>
          {country && <div className="weather-country">{country}</div>}
          <div className="weather-condition">{emoji} {condition}</div>
        </div>
        <div className="weather-temp-group">
          <div className="weather-temp" style={{ color: tempColor(temperature) }}>
            {temperature}<span className="weather-temp-unit">°C</span>
          </div>
          {temp_min != null && (
            <div className="weather-temp-min">最低 {temp_min}°C</div>
          )}
        </div>
      </div>

      <div className="weather-stats">
        <div className="stat">
          <span className="stat-icon">🌡️</span>
          <div>
            <div className="stat-label">體感溫度</div>
            <div className="stat-value">{feels_like != null ? `${feels_like} °C` : "—"}</div>
          </div>
        </div>
        <div className="stat">
          <span className="stat-icon">💧</span>
          <div>
            <div className="stat-label">相對濕度</div>
            <div className="stat-value">
              {humidity != null ? `${humidity}% ` : "—"}
              {humidity != null && <small>{HumidityLabel(humidity)}</small>}
            </div>
          </div>
        </div>
        <div className="stat">
          <span className="stat-icon">💨</span>
          <div>
            <div className="stat-label">風速</div>
            <div className="stat-value">
              {wind_speed != null ? `${wind_speed} km/h ` : "—"}
              <small>{WindLevel(wind_speed)}</small>
            </div>
          </div>
        </div>
        <div className="stat">
          <span className="stat-icon">🌂</span>
          <div>
            <div className="stat-label">降水量</div>
            <div className="stat-value">{precipitation != null ? `${precipitation} mm` : "—"}</div>
          </div>
        </div>
      </div>

      <div className="weather-source">
        資料來源：Open-Meteo・{isTomorrow ? "日預報" : "即時觀測"}
      </div>
    </div>
  );
}
