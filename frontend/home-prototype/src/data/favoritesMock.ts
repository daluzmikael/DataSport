import type { FavoritePlayer, FavoriteTeam } from "../types"

export const INITIAL_FOLLOWED_TEAMS: FavoriteTeam[] = [
  { id: "team-bos", abbr: "BOS", name: "Celtics", city: "Boston", isLive: true },
  { id: "team-lal", abbr: "LAL", name: "Lakers", city: "Los Angeles", isLive: true },
  { id: "team-gsw", abbr: "GSW", name: "Warriors", city: "Golden State" },
]

export const INITIAL_FOLLOWED_PLAYERS: FavoritePlayer[] = [
  {
    id: "player-tatum",
    name: "Jayson Tatum",
    teamAbbr: "BOS",
    position: "F",
    isLive: true,
    seasonAvgGameScore: 7.1,
  },
  {
    id: "player-durant",
    name: "Kevin Durant",
    teamAbbr: "PHX",
    position: "F",
    isLive: true,
    seasonAvgGameScore: 7.6,
  },
  {
    id: "player-jokic",
    name: "Nikola Jokic",
    teamAbbr: "DEN",
    position: "C",
    seasonAvgGameScore: 8.2,
  },
  {
    id: "player-embiid",
    name: "Joel Embiid",
    teamAbbr: "PHI",
    position: "C",
    seasonAvgGameScore: 7.4,
  },
]

export const SEARCHABLE_TEAMS: FavoriteTeam[] = [
  { id: "team-atl", abbr: "ATL", name: "Hawks", city: "Atlanta" },
  { id: "team-bkn", abbr: "BKN", name: "Nets", city: "Brooklyn" },
  { id: "team-bos", abbr: "BOS", name: "Celtics", city: "Boston" },
  { id: "team-cha", abbr: "CHA", name: "Hornets", city: "Charlotte" },
  { id: "team-chi", abbr: "CHI", name: "Bulls", city: "Chicago" },
  { id: "team-cle", abbr: "CLE", name: "Cavaliers", city: "Cleveland" },
  { id: "team-dal", abbr: "DAL", name: "Mavericks", city: "Dallas" },
  { id: "team-den", abbr: "DEN", name: "Nuggets", city: "Denver" },
  { id: "team-det", abbr: "DET", name: "Pistons", city: "Detroit" },
  { id: "team-gsw", abbr: "GSW", name: "Warriors", city: "Golden State" },
  { id: "team-hou", abbr: "HOU", name: "Rockets", city: "Houston" },
  { id: "team-ind", abbr: "IND", name: "Pacers", city: "Indiana" },
  { id: "team-lac", abbr: "LAC", name: "Clippers", city: "LA Clippers" },
  { id: "team-lal", abbr: "LAL", name: "Lakers", city: "Los Angeles" },
  { id: "team-mem", abbr: "MEM", name: "Grizzlies", city: "Memphis" },
  { id: "team-mia", abbr: "MIA", name: "Heat", city: "Miami" },
  { id: "team-mil", abbr: "MIL", name: "Bucks", city: "Milwaukee" },
  { id: "team-nyk", abbr: "NYK", name: "Knicks", city: "New York" },
  { id: "team-okc", abbr: "OKC", name: "Thunder", city: "Oklahoma City" },
  { id: "team-orl", abbr: "ORL", name: "Magic", city: "Orlando" },
  { id: "team-phi", abbr: "PHI", name: "76ers", city: "Philadelphia" },
  { id: "team-phx", abbr: "PHX", name: "Suns", city: "Phoenix" },
  { id: "team-por", abbr: "POR", name: "Trail Blazers", city: "Portland" },
  { id: "team-sac", abbr: "SAC", name: "Kings", city: "Sacramento" },
  { id: "team-sas", abbr: "SAS", name: "Spurs", city: "San Antonio" },
  { id: "team-tor", abbr: "TOR", name: "Raptors", city: "Toronto" },
  { id: "team-uta", abbr: "UTA", name: "Jazz", city: "Utah" },
  { id: "team-was", abbr: "WAS", name: "Wizards", city: "Washington" },
]

export const SEARCHABLE_PLAYERS: FavoritePlayer[] = [
  { id: "player-tatum", name: "Jayson Tatum", teamAbbr: "BOS", position: "F" },
  { id: "player-brown", name: "Jaylen Brown", teamAbbr: "BOS", position: "G" },
  { id: "player-durant", name: "Kevin Durant", teamAbbr: "PHX", position: "F" },
  { id: "player-curry", name: "Stephen Curry", teamAbbr: "GSW", position: "G" },
  { id: "player-jokic", name: "Nikola Jokic", teamAbbr: "DEN", position: "C" },
  { id: "player-embiid", name: "Joel Embiid", teamAbbr: "PHI", position: "C" },
  { id: "player-giannis", name: "Giannis Antetokounmpo", teamAbbr: "MIL", position: "F" },
  { id: "player-luka", name: "Luka Doncic", teamAbbr: "DAL", position: "G" },
  { id: "player-lebron", name: "LeBron James", teamAbbr: "LAL", position: "F" },
  { id: "player-edwards", name: "Anthony Edwards", teamAbbr: "MIN", position: "G" },
  { id: "player-brunson", name: "Jalen Brunson", teamAbbr: "NYK", position: "G" },
  { id: "player-booker", name: "Devin Booker", teamAbbr: "PHX", position: "G" },
]
