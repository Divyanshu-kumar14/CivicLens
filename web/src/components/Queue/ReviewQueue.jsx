import QueueActions from './QueueActions.jsx';
import SeverityBar from '../Ticket/SeverityBar.jsx';

// Amber (pending) ticket table: sorted by severity desc, bulk select,
// A/D/1-3 keyboard shortcuts, row click opens the drawer.
export default function ReviewQueue({
  tickets,
  selectedIds,
  onToggleSelect,
  onSelectAll,
  onApprove,
  onDismiss,
  onSetSeverity,
  onExportSelected,
  onRowClick,
}) {
  const rows = [...tickets].sort((a, b) => (b.severity || 0) - (a.severity || 0));

  const onKey = (e) => {
    if (e.key === 'a' || e.key === 'A') onApprove();
    else if (e.key === 'd' || e.key === 'D') onDismiss();
    else if (e.key === '1') onSetSeverity('low');
    else if (e.key === '2') onSetSeverity('med');
    else if (e.key === '3') onSetSeverity('high');
  };

  return (
    <div style={{ padding: 12, overflowY: 'auto', flex: 1 }} tabIndex={0} onKeyDown={onKey}>
      <QueueActions
        count={selectedIds.size}
        total={rows.length}
        onSelectAll={onSelectAll}
        onApprove={onApprove}
        onDismiss={onDismiss}
        onExportSelected={onExportSelected}
      />
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ textAlign: 'left', borderBottom: '2px solid #e0e0e0' }}>
            <th><input type="checkbox" checked={selectedIds.size === rows.length && rows.length > 0} onChange={onSelectAll} /></th>
            <th>Severity</th>
            <th>Type</th>
            <th>Location</th>
            <th>Repeat</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((t) => (
            <tr
              key={t.ticket_id}
              onClick={() => onRowClick(t.ticket_id)}
              style={{ borderBottom: '1px solid #eee', cursor: 'pointer' }}
            >
              <td onClick={(e) => e.stopPropagation()}>
                <input
                  type="checkbox"
                  checked={selectedIds.has(t.ticket_id)}
                  onChange={() => onToggleSelect(t.ticket_id)}
                />
              </td>
              <td style={{ minWidth: 140 }}><SeverityBar severity={t.severity} compact /></td>
              <td>{t.hole_label || t.cls || 'pothole'}</td>
              <td>{t.centroid?.[0]?.toFixed(4)}, {t.centroid?.[1]?.toFixed(4)}</td>
              <td>×{t.repeat_count ?? 1}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && <p style={{ color: '#666' }}>Queue empty — nothing awaiting review.</p>}
      <small style={{ color: '#666' }}>Shortcuts: A approve · D dismiss · 1/2/3 severity</small>
    </div>
  );
}
