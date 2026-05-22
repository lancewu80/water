import { useRef } from "react";
import "./SearchBox.css";

export default function SearchBox({ value, onChange, onSearch, loading, placeholder }) {
  const inputRef = useRef(null);

  const handleKey = (e) => {
    if (e.key === "Enter") onSearch();
  };

  const handleClear = () => {
    onChange("");
    inputRef.current?.focus();
  };

  return (
    <div className="search-wrap">
      <span className="search-icon">🔍</span>
      <input
        ref={inputRef}
        className="search-input"
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKey}
        placeholder={placeholder}
        disabled={loading}
      />
      {value && (
        <button className="clear-btn" onClick={handleClear} title="清除">
          ✕
        </button>
      )}
      <button
        className="search-btn"
        onClick={onSearch}
        disabled={loading || !value.trim()}
      >
        {loading ? "…" : "搜尋"}
      </button>
    </div>
  );
}
