import "./WebResultCard.css";

export default function WebResultCard({ item }) {
  const { title, summary, url, source } = item;

  return (
    <div className="web-card">
      <div className="web-source-row">
        <span className="web-favicon">
          {source ? (
            <img
              src={`https://www.google.com/s2/favicons?domain=${source}&sz=16`}
              alt=""
              width={16}
              height={16}
              onError={(e) => { e.target.style.display = "none"; }}
            />
          ) : "🌐"}
        </span>
        <span className="web-domain">{source || "網路來源"}</span>
      </div>

      <a
        className="web-title"
        href={url}
        target="_blank"
        rel="noopener noreferrer"
      >
        {title}
      </a>

      <div className="web-url">{url}</div>

      {summary && <p className="web-summary">{summary}</p>}
    </div>
  );
}
