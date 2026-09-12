import type { FieldSpec } from "../../api/chartSpec"
import { formatValue } from "../../api/chartSpec"

/* The fallback. A chart that cannot be chosen confidently should not be invented —
 * rendering the rows is always honest, and it means no answer ever shows a blank frame. */
interface AnalystTableProps {
  rows: Array<Record<string, unknown>>
  columns: FieldSpec[]
}

export function AnalystTable({ rows, columns }: AnalystTableProps) {
  if (!rows.length || !columns.length) {
    return <p className="py-8 text-center text-sm text-ds-muted">No rows to show.</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-xs">
        <thead>
          <tr className="border-b border-ds-border">
            {columns.map((col) => (
              <th
                key={col.column}
                className="whitespace-nowrap px-2 py-1.5 font-semibold text-ds-muted"
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-ds-border/40 last:border-0">
              {columns.map((col) => {
                const value = row[col.column]
                return (
                  <td
                    key={col.column}
                    className="whitespace-nowrap px-2 py-1.5 text-ds-text/90"
                  >
                    {typeof value === "number"
                      ? formatValue(value, col)
                      : value == null
                        ? "—"
                        : String(value)}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
