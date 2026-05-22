import "./NewsCard.css";

function formatDate(dateStr) {
  if (!dateStr) return "";
  try {
    return new Date(dateStr).toLocaleDateString("zh-TW", {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
}

export default function NewsCard({ item }) {
  const { title, summary, url, source, date, image } = item;

  return (
    <a
      className="news-card"
      href={url}
      target="_blank"
      rel="noopener noreferrer"
    >
      {image && (
        <div className="news-img-wrap">
          <img
            className="news-img"
            src={image}
            alt={title}
            onError={(e) => { e.target.closest(".news-img-wrap").style.display = "none"; }}
          />
        </div>
      )}
      <div className="news-body">
        <div className="news-meta">
          {source && <span className="news-source">{source}</span>}
          {date   && <span className="news-date">{formatDate(date)}</span>}
        </div>
        <h3 className="news-title">{title}</h3>
        {summary && <p className="news-summary">{summary}</p>}
      </div>
      <div className="news-arrow">→</div>
    </a>
  );
}
