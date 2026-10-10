import { useEffect } from 'react';

// Queued -> Processing -> N detections -> M tickets. Polls GET /jobs/{id} every 2s.
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
    <div className="cl-job">
      <div><b>{job.job_id?.slice(0, 8)}</b> — {label}</div>
      <div className="cl-jobbar">
        <div style={{ transform: `scaleX(${pct / 100})` }} />
      </div>
    </div>
  );
}
