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
  const label =
    job.status === 'completed'
      ? `${counts.raw ?? '?'} detections → ${counts.clusters ?? '?'} tickets`
      : job.status === 'failed'
        ? 'Job failed'
        : `${job.status}… ${(job.progress_pct ?? 0).toFixed(0)}%`;

  return (
    <div style={{ margin: 12, padding: 10, border: '1px solid #e0e0e0', borderRadius: 6 }}>
      <div style={{ fontSize: 13 }}>
        <b>{job.job_id?.slice(0, 8)}</b> — {label}
      </div>
      <div style={{ height: 8, background: '#eee', borderRadius: 4, marginTop: 6 }}>
        <div
          style={{
            height: '100%', borderRadius: 4, background: '#2e7d32',
            width: `${job.status === 'completed' ? 100 : job.progress_pct ?? 0}%`,
            transition: 'width 0.5s',
          }}
        />
      </div>
    </div>
  );
}
