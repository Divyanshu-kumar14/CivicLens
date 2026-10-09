export default function QueueActions({
  count,
  total,
  onSelectAll,
  onApprove,
  onDismiss,
  onExportSelected,
}) {
  return (
    <div className="cl-actions">
      <button className="btn-ghost" onClick={onSelectAll}>
        {count === total && total > 0 ? 'Clear' : 'Select All'} ({count}/{total})
      </button>
      <button className="btn-file" onClick={onApprove} disabled={count === 0}>
        Approve (A)
      </button>
      <button className="btn-dismiss" onClick={onDismiss} disabled={count === 0}>
        Dismiss (D)
      </button>
      <button className="btn-ghost" onClick={onExportSelected} disabled={count === 0}>
        Export Selected
      </button>
    </div>
  );
}
