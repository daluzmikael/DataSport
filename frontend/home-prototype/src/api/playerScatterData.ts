export const DEFAULT_SCATTER_SEASON = "2023-24"

export interface ScatterPointRow {
  player_name: string
  x_value: number
  y_value: number
}

function parseNum(raw: unknown): number {
  const n = typeof raw === "number" ? raw : parseFloat(String(raw ?? ""))
  return Number.isNaN(n) ? 0 : n
}

export function scatterRowsFromApi(
  rows: Record<string, unknown>[] | null | undefined,
): ScatterPointRow[] {
  if (!rows?.length) return []
  return rows
    .map((row) => ({
      player_name: String(row.player_name ?? row.PLAYER_NAME ?? row.full_name ?? ""),
      x_value: parseNum(row.x_value),
      y_value: parseNum(row.y_value),
    }))
    .filter((row) => row.player_name && Number.isFinite(row.x_value) && Number.isFinite(row.y_value))
}

const MOCK_PTS_MIN: ScatterPointRow[] = [
  { player_name: "Joel Embiid", x_value: 34.2, y_value: 33.1 },
  { player_name: "Luka Dončić", x_value: 37.5, y_value: 32.4 },
  { player_name: "Giannis Antetokounmpo", x_value: 35.2, y_value: 31.1 },
  { player_name: "Jayson Tatum", x_value: 36.8, y_value: 26.9 },
  { player_name: "Kevin Durant", x_value: 37.1, y_value: 29.1 },
  { player_name: "Stephen Curry", x_value: 32.7, y_value: 29.4 },
  { player_name: "Nikola Jokić", x_value: 34.6, y_value: 29.3 },
  { player_name: "Devin Booker", x_value: 35.9, y_value: 27.1 },
  { player_name: "LeBron James", x_value: 35.3, y_value: 28.9 },
  { player_name: "Jaylen Brown", x_value: 33.4, y_value: 26.6 },
  { player_name: "Anthony Edwards", x_value: 35.1, y_value: 27.2 },
  { player_name: "Shai Gilgeous-Alexander", x_value: 34.4, y_value: 30.1 },
]

const MOCK_AST_TOV: ScatterPointRow[] = [
  { player_name: "Tyrese Haliburton", x_value: 2.3, y_value: 10.9 },
  { player_name: "Trae Young", x_value: 4.1, y_value: 10.8 },
  { player_name: "Luka Dončić", x_value: 3.9, y_value: 9.8 },
  { player_name: "Nikola Jokić", x_value: 3.2, y_value: 9.0 },
  { player_name: "James Harden", x_value: 3.5, y_value: 8.5 },
  { player_name: "Jayson Tatum", x_value: 2.5, y_value: 4.9 },
  { player_name: "LeBron James", x_value: 3.4, y_value: 8.3 },
  { player_name: "Stephen Curry", x_value: 2.8, y_value: 5.0 },
  { player_name: "Jaylen Brown", x_value: 2.2, y_value: 3.9 },
  { player_name: "Devin Booker", x_value: 2.9, y_value: 6.9 },
  { player_name: "Anthony Edwards", x_value: 2.6, y_value: 5.1 },
  { player_name: "Shai Gilgeous-Alexander", x_value: 2.4, y_value: 6.4 },
]

export function mockScatterPtsMin(): ScatterPointRow[] {
  return MOCK_PTS_MIN
}

export function mockScatterAstTov(): ScatterPointRow[] {
  return MOCK_AST_TOV
}
