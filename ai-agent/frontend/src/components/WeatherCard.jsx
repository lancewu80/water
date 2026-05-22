import "./WeatherCard.css";

function WindLevel(speed) {
  if (speed < 5)  return "微風";
  if (speed < 15) return "輕風";
  if (speed < 30) return "中風";
  if (speed < 50) return "強風";
  return "暴風";
}

function HumidityLabel(h) {
  if (h < 30) return "乾燥";
  if (h < 60) return "舒適";
  if (h < 80) return "偏濕";
  return "潮濕";
}

export default function WeatherCard({ data }) {
  const {
    city, country, temperature, feels_like,
    humidity, wind_speed, precipitation, condition, emoji,
  } = data;

  const tempColor =
    temperature >= 35 ? "#ef4444" :
    temperature >= 28 ? "#f97316" :
    temperature >= 20 ? "#3b82f6" :
    "#06b6d4";

  return (
    <div className="weather-card">
      {/* 城市 & 天氣狀況 */}
      <div className="weather-top">
        <div>
          <div className="weather-city">{city}</div>
          {country && <div className="weather-country">{country}</div>}
          <div className="weather-condition">{emoji} {condition}</div>
        </div>
        <div className="weather-temp" style={{ color: tempColor }}>
          {temperature}
          <span className="weather-temp-unit">°C</span>
        </div>
      </div>

      {/* 細節指標 */}
      <div className="weather-stats">
        <div className="stat">
          <span className="stat-icon">🌡️</span>
          <div>
            <div className="stat-label">體感溫度</div>
            <div className="stat-value">{feels_like} °C</div>
          </div>
        </div>
        <div className="stat">
          <span className="stat-icon">💧</span>
          <div>
            <div className="stat-label">相對濕度</div>
            <div className="stat-value">{humidity}% <small>{HumidityLabel(humidity)}</small></div>
          </div>
        </div>
        <div className="stat">
          <span className="stat-icon">💨</span>
          <div>
            <div className="stat-label">風速</div>
            <div className="stat-value">{wind_speed} km/h <small>{WindLevel(wind_speed)}</small></div>
          </div>
        </div>
        <div className="stat">
          <span className="stat-icon">🌂</span>
          <div>
            <div className="stat-label">降水量</div>
            <div className="stat-value">{precipitation} mm</div>
          </div>
        </div>
      </div>

      <div className="weather-source">
        資料來源：Open-Meteo（即時）
      </div>
    </div>
  );
}
