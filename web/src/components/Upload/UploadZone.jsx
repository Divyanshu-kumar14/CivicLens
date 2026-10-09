import { useRef, useState } from 'react';

const MAX_BYTES = 2 * 1024 ** 3; // 2GB, mirrors API intake limit

// Drag-and-drop for .mp4 + .csv/.srt. Validates, then hands files up.
export default function UploadZone({ onSubmit, busy }) {
  const [video, setVideo] = useState(null);
  const [gps, setGps] = useState(null);
  const [error, setError] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  const pick = (files) => {
    setError('');
    for (const f of files) {
      if (f.size > MAX_BYTES) {
        setError(`${f.name}: exceeds 2GB limit`);
        return;
      }
      if (/\.(mp4|mov|avi|mkv)$/i.test(f.name)) setVideo(f);
      else if (/\.(csv|srt)$/i.test(f.name)) setGps(f);
      else {
        setError(`${f.name}: need .mp4 video or .csv/.srt GPS`);
        return;
      }
    }
  };

  const submit = () => {
    if (!video) {
      setError('A video file is required (GPS optional).');
      return;
    }
    onSubmit({ video, gps });
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => { e.preventDefault(); setDragOver(false); pick(e.dataTransfer.files); }}
      onClick={() => inputRef.current?.click()}
      style={{
        border: `2px dashed ${dragOver ? '#2e7d32' : '#ccc'}`,
        borderRadius: 8, padding: 20, margin: 12, textAlign: 'center',
        background: dragOver ? '#f1f8e9' : '#fafafa', cursor: 'pointer',
      }}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".mp4,.mov,.avi,.mkv,.csv,.srt"
        style={{ display: 'none' }}
        onChange={(e) => pick(e.target.files)}
      />
      <div>Drop <b>.mp4</b> + <b>.csv/.srt</b> here, or click to browse</div>
      <div style={{ fontSize: 13, marginTop: 8 }}>
        {video ? `🎬 ${video.name}` : 'no video yet'}
        {gps ? ` · 📍 ${gps.name}` : ' · GPS optional'}
      </div>
      {error && <div style={{ color: '#E53935', fontSize: 13 }}>{error}</div>}
      <button
        className="btn-file"
        style={{ marginTop: 10, padding: '8px 16px', borderRadius: 6, border: 'none', cursor: 'pointer' }}
        disabled={busy || !video}
        onClick={(e) => { e.stopPropagation(); submit(); }}
      >
        {busy ? 'Uploading…' : 'Start job'}
      </button>
    </div>
  );
}
