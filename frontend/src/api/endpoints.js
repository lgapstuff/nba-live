import { http } from "./http";

export const fetchHealth = async () => {
  const { data } = await http.get("/health");
  return data;
};

export const fetchSchedule = async (date) => {
  const { data } = await http.get("/nba/games", { params: { date } });
  return data;
};

export const fetchLatestOdds = async () => {
  const { data } = await http.get("/nba/odds/latest");
  return data;
};

export const fetchCdnScoreboard = async () => {
  const { data } = await http.get("/nba/cdn/scoreboard/today");
  return data;
};

export const fetchLineupByGameId = async (gameId) => {
  const { data } = await http.get(`/nba/games/${gameId}/lineups`);
  return data;
};

export const fetchLineupByTeams = async (homeTeam, awayTeam, date) => {
  const params = { home_team: homeTeam, away_team: awayTeam };
  if (date) {
    params.date = date;
  }
  const { data } = await http.get("/nba/lineups/resolve", { params });
  return data;
};

export const fetchLineupsByDate = async (date) => {
  const { data } = await http.get("/nba/lineups", { params: { date } });
  return data;
};

export const fetchGameOdds = async (gameId) => {
  const { data } = await http.get(`/nba/games/${gameId}/odds`);
  return data;
};

export const fetchCdnBoxscore = async (gameId) => {
  const { data } = await http.get(`/nba/cdn/boxscore/${gameId}`);
  return data;
};

export const fetchCdnPlayByPlay = async (gameId) => {
  const { data } = await http.get(`/nba/cdn/playbyplay/${gameId}`);
  return data;
};

export const loadGameLogsForEvent = async (gameId) => {
  const { data } = await http.post(`/nba/games/${gameId}/game-logs`);
  return data;
};

export const fetchPlayerGameLogs = async (playerId) => {
  const { data } = await http.get(`/nba/players/${playerId}/game-logs`);
  return data;
};

export const loadPlayerGameLogs = async (playerId, playerName) => {
  const params = {};
  if (playerName) {
    params.player_name = playerName;
  }
  const { data } = await http.post(`/nba/players/${playerId}/game-logs/load`, null, { params });
  return data;
};
