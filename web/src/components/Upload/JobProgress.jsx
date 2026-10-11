import { useEffect } from 'react';
import { Card } from '../ui/card.jsx';
import { Progress } from '../ui/primitives.jsx';

// Queued -> Processing -> N detections -> M tickets. Polls GET /jobs/{id} every 2s.
// Premium skin: glass card + animated progress. Polling logic untouched.
export default function JobProgress({ job, fetchJob, onUpdate, onDone }) {
  useEffect(() => {
    if (!job || job.status === 'completed' || job.status === 'failed') return;
    const timer = setInterval(async () => {
      try {
        const fresh = await fetchJob(job.job_id);
        onUpdate(fresh);
        if (fresh.status === 'completed' || fresh.status === 'failed') onDone(fresh);
      } catch {
        /* keep polling through transient errors */
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [job?.job_id, job?.status]);

  if (!job) return null;
  const counts = job.counts || {};
  const pct = job.status === 'completed' ? 100 : Math.round(job.progress_pct ?? 0);
  const label =
    job.status === 'completed'
      ? `${counts.raw ?? '?'} detections → ${counts.clusters ?? '?'} tickets`
      : job.status === 'failed'
        ? 'Job failed'
        : `${job.status}… ${pct}%`;

  return (
    <Card className="mx-3.5 mb-3.5 p-3.5 text-[13px] tabular-nums">
      <div><b className="font-display">{job.job_id?.slice(0, 8)}</b> — {label}</div>
      <Progress value={pct / 100} className="mt-2" />
    </Card>
  );
}
