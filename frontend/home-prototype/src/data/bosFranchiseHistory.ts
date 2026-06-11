import type { TeamHistorySeason } from "../types"

/** Real Boston Celtics season records · stats are era-plausible mock averages */
const BOS_SEASON_WL: readonly (readonly [string, string])[] = [
  ["1946-47", "22-38"],
  ["1947-48", "20-28"],
  ["1948-49", "25-35"],
  ["1949-50", "39-31"],
  ["1950-51", "35-37"],
  ["1951-52", "34-32"],
  ["1952-53", "46-29"],
  ["1953-54", "42-26"],
  ["1954-55", "36-36"],
  ["1955-56", "33-49"],
  ["1956-57", "44-28"],
  ["1957-58", "49-23"],
  ["1958-59", "52-20"],
  ["1959-60", "59-16"],
  ["1960-61", "57-22"],
  ["1961-62", "60-20"],
  ["1962-63", "58-22"],
  ["1963-64", "59-21"],
  ["1964-65", "62-18"],
  ["1965-66", "54-26"],
  ["1966-67", "60-21"],
  ["1967-68", "54-28"],
  ["1968-69", "48-34"],
  ["1969-70", "34-48"],
  ["1970-71", "44-38"],
  ["1971-72", "56-26"],
  ["1972-73", "68-14"],
  ["1973-74", "56-26"],
  ["1974-75", "60-22"],
  ["1975-76", "54-28"],
  ["1976-77", "44-38"],
  ["1977-78", "32-50"],
  ["1978-79", "29-53"],
  ["1979-80", "61-21"],
  ["1980-81", "62-20"],
  ["1981-82", "63-19"],
  ["1982-83", "56-26"],
  ["1983-84", "62-20"],
  ["1984-85", "63-19"],
  ["1985-86", "67-15"],
  ["1986-87", "59-23"],
  ["1987-88", "57-25"],
  ["1988-89", "42-40"],
  ["1989-90", "52-30"],
  ["1990-91", "56-26"],
  ["1991-92", "51-31"],
  ["1992-93", "48-34"],
  ["1993-94", "32-50"],
  ["1994-95", "35-47"],
  ["1995-96", "33-49"],
  ["1996-97", "15-67"],
  ["1997-98", "36-46"],
  ["1998-99", "19-31"],
  ["1999-00", "35-47"],
  ["2000-01", "36-46"],
  ["2001-02", "49-33"],
  ["2002-03", "44-38"],
  ["2003-04", "45-37"],
  ["2004-05", "45-37"],
  ["2005-06", "33-49"],
  ["2006-07", "24-58"],
  ["2007-08", "66-16"],
  ["2008-09", "62-20"],
  ["2009-10", "50-32"],
  ["2010-11", "56-26"],
  ["2011-12", "39-27"],
  ["2012-13", "41-40"],
  ["2013-14", "25-57"],
  ["2014-15", "40-42"],
  ["2015-16", "48-34"],
  ["2016-17", "53-29"],
  ["2017-18", "55-27"],
  ["2018-19", "49-33"],
  ["2019-20", "48-24"],
  ["2020-21", "36-36"],
  ["2021-22", "51-31"],
  ["2022-23", "57-25"],
  ["2023-24", "64-18"],
  ["2024-25", "41-17"],
]

function winPct(wl: string): number {
  const [w, l] = wl.split("-").map(Number)
  return w / (w + l)
}

function statsForSeason(season: string, wl: string): TeamHistorySeason["values"] {
  const year = Number.parseInt(season.slice(0, 4), 10)
  const wp = winPct(wl)

  if (year < 1954) {
    return {
      pts: +(79 + wp * 8).toFixed(1),
      reb: +(44 + wp * 4).toFixed(1),
      ast: +(19 + wp * 3).toFixed(1),
      fg_pct: (0.355 + wp * 0.04).toFixed(3).replace(/^0/, "."),
      fg3_pct: "—",
    }
  }
  if (year < 1960) {
    return {
      pts: +(104 + wp * 10).toFixed(1),
      reb: +(48 + wp * 4).toFixed(1),
      ast: +(22 + wp * 4).toFixed(1),
      fg_pct: (0.395 + wp * 0.05).toFixed(3).replace(/^0/, "."),
      fg3_pct: "—",
    }
  }
  if (year < 1970) {
    return {
      pts: +(112 + wp * 8).toFixed(1),
      reb: +(49 + wp * 3).toFixed(1),
      ast: +(24 + wp * 3).toFixed(1),
      fg_pct: (0.415 + wp * 0.04).toFixed(3).replace(/^0/, "."),
      fg3_pct: "—",
    }
  }
  if (year < 1979) {
    return {
      pts: +(108 + wp * 6).toFixed(1),
      reb: +(47 + wp * 2).toFixed(1),
      ast: +(23 + wp * 2).toFixed(1),
      fg_pct: (0.445 + wp * 0.03).toFixed(3).replace(/^0/, "."),
      fg3_pct: "—",
    }
  }
  if (year < 1990) {
    return {
      pts: +(110 + wp * 4).toFixed(1),
      reb: +(44 + wp * 2).toFixed(1),
      ast: +(25 + wp * 2).toFixed(1),
      fg_pct: (0.465 + wp * 0.025).toFixed(3).replace(/^0/, "."),
      fg3_pct: (0.22 + wp * 0.08).toFixed(3).replace(/^0/, "."),
    }
  }
  if (year < 2000) {
    return {
      pts: +(98 + wp * 6).toFixed(1),
      reb: +(42 + wp * 2).toFixed(1),
      ast: +(22 + wp * 2).toFixed(1),
      fg_pct: (0.445 + wp * 0.03).toFixed(3).replace(/^0/, "."),
      fg3_pct: (0.32 + wp * 0.06).toFixed(3).replace(/^0/, "."),
    }
  }
  if (year < 2010) {
    return {
      pts: +(96 + wp * 8).toFixed(1),
      reb: +(40 + wp * 2).toFixed(1),
      ast: +(20 + wp * 2).toFixed(1),
      fg_pct: (0.44 + wp * 0.03).toFixed(3).replace(/^0/, "."),
      fg3_pct: (0.34 + wp * 0.04).toFixed(3).replace(/^0/, "."),
    }
  }
  if (year < 2020) {
    return {
      pts: +(102 + wp * 10).toFixed(1),
      reb: +(42 + wp * 2).toFixed(1),
      ast: +(22 + wp * 3).toFixed(1),
      fg_pct: (0.455 + wp * 0.025).toFixed(3).replace(/^0/, "."),
      fg3_pct: (0.355 + wp * 0.035).toFixed(3).replace(/^0/, "."),
    }
  }
  return {
    pts: +(112 + wp * 10).toFixed(1),
    reb: +(44 + wp * 2).toFixed(1),
    ast: +(25 + wp * 2).toFixed(1),
    fg_pct: (0.465 + wp * 0.025).toFixed(3).replace(/^0/, "."),
    fg3_pct: (0.365 + wp * 0.028).toFixed(3).replace(/^0/, "."),
  }
}

/** Override recent seasons with tighter mock numbers matching the game-log mock */
const RECENT_OVERRIDES: Record<string, TeamHistorySeason["values"]> = {
  "2007-08": { pts: 100.6, reb: 39.9, ast: 22.4, fg_pct: ".459", fg3_pct: ".381" },
  "2008-09": { pts: 104.5, reb: 39.6, ast: 22.7, fg_pct: ".472", fg3_pct: ".393" },
  "2009-10": { pts: 99.2, reb: 39.9, ast: 22.9, fg_pct: ".478", fg3_pct: ".382" },
  "2010-11": { pts: 96.5, reb: 39.8, ast: 20.6, fg_pct: ".459", fg3_pct: ".362" },
  "2011-12": { pts: 91.1, reb: 39.8, ast: 21.4, fg_pct: ".459", fg3_pct: ".339" },
  "2012-13": { pts: 96.2, reb: 41.8, ast: 21.5, fg_pct: ".463", fg3_pct: ".348" },
  "2013-14": { pts: 96.2, reb: 41.3, ast: 21.0, fg_pct: ".449", fg3_pct: ".349" },
  "2014-15": { pts: 101.4, reb: 43.7, ast: 21.7, fg_pct: ".448", fg3_pct: ".349" },
  "2015-16": { pts: 105.4, reb: 42.0, ast: 22.5, fg_pct: ".448", fg3_pct: ".353" },
  "2016-17": { pts: 108.0, reb: 45.3, ast: 25.2, fg_pct: ".475", fg3_pct: ".378" },
  "2017-18": { pts: 104.0, reb: 45.3, ast: 22.5, fg_pct: ".475", fg3_pct: ".378" },
  "2018-19": { pts: 112.4, reb: 44.7, ast: 24.0, fg_pct: ".464", fg3_pct: ".356" },
  "2019-20": { pts: 113.7, reb: 46.3, ast: 25.0, fg_pct: ".462", fg3_pct: ".380" },
  "2020-21": { pts: 112.6, reb: 45.3, ast: 24.0, fg_pct: ".464", fg3_pct: ".369" },
  "2021-22": { pts: 104.6, reb: 46.1, ast: 24.8, fg_pct: ".466", fg3_pct: ".353" },
  "2022-23": { pts: 117.9, reb: 44.9, ast: 26.7, fg_pct: ".485", fg3_pct: ".378" },
  "2023-24": { pts: 120.6, reb: 46.3, ast: 26.6, fg_pct: ".486", fg3_pct: ".388" },
  "2024-25": { pts: 118.6, reb: 46.0, ast: 26.4, fg_pct: ".479", fg3_pct: ".379" },
}

export const BOS_FRANCHISE_HISTORY: TeamHistorySeason[] = BOS_SEASON_WL.map(
  ([season, wl]) => ({
    season,
    wl,
    values: RECENT_OVERRIDES[season] ?? statsForSeason(season, wl),
  }),
)
