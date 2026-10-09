// Severity color mapping + formatting (mirrors API thresholds: 70 file, 40 review).
export const FILED_COLOR = '#E53935'; // red
export const REVIEW_COLOR = '#FF8F00'; // amber
export const DISMISSED_COLOR = '#9E9E9E'; // grey

export function statusOf(ticket) {
  return ticket.status;
}

export function colorFor(ticket) {
  if (ticket.status === 'filed') return FILED_COLOR;
  if (ticket.status === 'pending') return REVIEW_COLOR;
  return DISMISSED_COLOR;
}

export function labelFor(severity) {
  if (severity >= 70) return 'Critical';
  if (severity >= 40) return 'Review';
  return 'Low';
}
