"""
NBA CDN client for live scoreboard and boxscore data.
"""
import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple, List


class NBACdnClient:
    """Client for NBA CDN live data endpoints."""

    def __init__(self, timeout_seconds: int = 10) -> None:
        self.timeout_seconds = timeout_seconds
        self.scoreboard_url = os.getenv(
            "NBA_CDN_SCOREBOARD_URL",
            "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
        )
        self.boxscore_url_template = os.getenv(
            "NBA_CDN_BOXSCORE_URL_TEMPLATE",
            "https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json",
        )
        self.playbyplay_url_template = os.getenv(
            "NBA_CDN_PLAYBYPLAY_URL_TEMPLATE",
            "https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game_id}.json",
        )
        self.s3_boxscore_url_template = os.getenv(
            "NBA_S3_BOXSCORE_URL_TEMPLATE",
            "https://nba-prod-us-east-1-mediaops-stats.s3.amazonaws.com/NBA/liveData/boxscore/boxscore_{game_id}.json",
        )
        self.s3_playbyplay_url_template = os.getenv(
            "NBA_S3_PLAYBYPLAY_URL_TEMPLATE",
            "https://nba-prod-us-east-1-mediaops-stats.s3.amazonaws.com/NBA/liveData/playbyplay/playbyplay_{game_id}.json",
        )

    def get_todays_scoreboard(self) -> Dict[str, Any]:
        """Return today's live scoreboard JSON."""
        return self._fetch_json(self.scoreboard_url)

    def get_boxscore(self, game_id: str, cache_bust: str | None = None) -> Dict[str, Any]:
        """Return boxscore JSON for a specific NBA GameID."""
        scoreboard_game = self._get_scoreboard_game(game_id)
        if scoreboard_game and self._is_game_not_started(scoreboard_game):
            return self._build_pregame_boxscore(scoreboard_game)

        url = self.boxscore_url_template.format(game_id=game_id)
        if cache_bust:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}t={cache_bust}"
        urls = [url, self.s3_boxscore_url_template.format(game_id=game_id)]
        last_error: Optional[Exception] = None
        for candidate in urls:
            try:
                return self._fetch_json(candidate)
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code in {403, 404, 410}:
                    continue
                raise
            except urllib.error.URLError as exc:
                last_error = exc
                continue
        if last_error:
            raise last_error
        raise urllib.error.URLError("Unable to fetch boxscore.")

    def get_playbyplay(self, game_id: str, cache_bust: str | None = None) -> Dict[str, Any]:
        """Return play-by-play JSON for a specific NBA GameID."""
        url = self.playbyplay_url_template.format(game_id=game_id)
        if cache_bust:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}t={cache_bust}"
        urls = [url, self.s3_playbyplay_url_template.format(game_id=game_id)]
        last_error: Optional[Exception] = None
        for candidate in urls:
            try:
                return self._fetch_json(candidate)
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code in {403, 404, 410}:
                    continue
                raise
            except urllib.error.URLError as exc:
                last_error = exc
                continue
        if last_error:
            raise last_error
        raise urllib.error.URLError("Unable to fetch play-by-play.")

    def _get_scoreboard_game(self, game_id: str) -> Optional[Dict[str, Any]]:
        try:
            data = self.get_todays_scoreboard()
            scoreboard = data.get("scoreboard", {})
            games = scoreboard.get("games", [])
            for game in games:
                if str(game.get("gameId")) == str(game_id):
                    return game
        except Exception:
            return None
        return None

    def _is_game_not_started(self, game: Dict[str, Any]) -> bool:
        status = game.get("gameStatus")
        period = game.get("period")
        return status in {0, 1} or (period == 0)

    def _build_pregame_boxscore(self, game: Dict[str, Any]) -> Dict[str, Any]:
        home = game.get("homeTeam", {}) or {}
        away = game.get("awayTeam", {}) or {}
        return {
            "game": {
                "gameId": game.get("gameId"),
                "gameStatus": game.get("gameStatus"),
                "gameStatusText": game.get("gameStatusText"),
                "period": game.get("period"),
                "gameClock": game.get("gameClock"),
                "homeTeam": {
                    "teamId": home.get("teamId"),
                    "teamTricode": home.get("teamTricode"),
                    "players": [],
                },
                "awayTeam": {
                    "teamId": away.get("teamId"),
                    "teamTricode": away.get("teamTricode"),
                    "players": [],
                },
            }
        }

    def _fetch_json(self, url: str) -> Dict[str, Any]:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Origin": "https://www.nba.com",
                "Referer": "https://www.nba.com/",
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            payload = response.read().decode("utf-8")
        return json.loads(payload)
