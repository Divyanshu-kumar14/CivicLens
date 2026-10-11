import { useRef, useState } from 'react';
import { Camera, FileVideo, MapPin, Satellite, ScanEye, TicketCheck } from 'lucide-react';
import { PipelineBeam } from '../ui/beam.jsx';
import { Card } from '../ui/card.jsx';
import { ShimmerButton } from '../ui/magic.jsx';

const MAX_BYTES = 2 * 1024 ** 3; // 2GB, mirrors API intake limit

// Drag-and-drop for .mp4 + .csv/.srt. Validates, then hands files up.
// Premium skin: glass dropzone + AnimatedBeam pipeline strip showing
// Scout → Vision → Triage → Filed before the user ever uploads.
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
    <div className="p-3.5">
      <Card className="mb-3 p-4">
        <div className="mb-1 text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-500">How a route becomes tickets</div>
        <PipelineBeam
          steps={[
            { icon: <Camera size={17} />, label: 'Scout', sub: '.mp4 + GPS', accent: '#3ae2ff' },
            { icon: <ScanEye size={17} />, label: 'Vision', sub: 'OpenCV+YOLO', accent: '#ffb020' },
            { icon: <Satellite size={17} />, label: 'Triage', sub: 'dedup+score', accent: '#a78bfa' },
            { icon: <TicketCheck size={17} />, label: 'Filed', sub: 'export CSV', accent: '#34d399' },
          ]}
        />
      </Card>
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload route video and GPS"
        onKeyDown={(e) => { if (e.key === 'Enter') inputRef.current?.click(); }}
        className={`cursor-pointer rounded-2xl border-2 border-dashed p-8 text-center backdrop-blur-xl transition-all duration-200 ${
          dragOver
            ? 'border-emerald-400/70 bg-emerald-400/8 scale-[1.01]'
            : 'border-white/12 bg-[rgba(15,18,24,0.72)] hover:border-white/25'
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); pick(e.dataTransfer.files); }}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".mp4,.mov,.avi,.mkv,.csv,.srt"
          style={{ display: 'none' }}
          onChange={(e) => pick(e.target.files)}
        />
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-slate-200">
          <FileVideo size={20} />
        </div>
        <div className="text-sm text-slate-100"><b>Drop .mp4 + .csv/.srt here</b>, or click to browse</div>
        <div className="mt-2 flex items-center justify-center gap-2 text-[13px] tabular-nums text-slate-400">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
            <FileVideo size={13} /> {video ? video.name : 'No video yet'}
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
            <MapPin size={13} /> {gps ? gps.name : 'GPS optional'}
          </span>
        </div>
        {error && <div className="mt-2 text-[13px] text-[#ff7a7a]" role="alert">{error}</div>}
        <div className="mt-4">
          <ShimmerButton
            disabled={busy || !video}
            onClick={(e) => { e.stopPropagation(); submit(); }}
          >
            {busy ? 'Uploading…' : 'Start job'}
          </ShimmerButton>
        </div>
      </div>
    </div>
  );
}
