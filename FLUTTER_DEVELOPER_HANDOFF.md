# ScoreLivePRO - Backend Migration & Flutter Integration Guide

> **Target Audience:** Flutter Mobile Engineering Team (`v2scorelivepro`)  
> **Date:** September 9, 2026  
> **Backend Release:** v2.4 (Server-side Data Normalization & Confederation Engine)  
> **Status:** Live in Production / Ready for Client Integration  

---

## 1. Executive Summary

All client-side compensations, defensive parsing rules, and data normalizations from the *Flutter Frontend Validation & Data Normalization* specification have been natively implemented in the Django backend.

This document outlines the **exact changes required in the Flutter codebase** to:
1. **Fix the Champions League 9-match collision bug** (Foresters vs Wiliete appearing under UEFA Champions League).
2. **Eliminate hardcoded continental/confederation maps** in Dart.
3. **Consume the new Pre-Grouped Fixtures API** (`/sports/fixtures/grouped/`).
4. **Use server-side `coverage` metadata** to avoid blank screens and redundant API requests.
5. **Simplify diacritic/accent search** using PostgreSQL `unaccent`.

---

## 2. Issue Resolution: Champions League 9 Matches Collision

### The Root Cause
On September 10, 2026, 9 matches occur across distinct competitions containing the words *"Champions League"*:
* **UEFA Champions League (`league.id = 2`)**: 6 matches (PSV vs Shakhtar, Bayern vs Bodo/Glimt, etc.)
* **CAF Champions League (`league.id = 12`)**: 1 match (*Foresters vs Wiliete*)
* **Nasjonal U19 Champions League (`league.id = 823`)**: 2 matches (Norway Youth)

Because the Flutter app grouped matches by `league.name` or checked `.contains("Champions League")`, all 3 separate competitions collapsed into a single accordion section of 9 matches.

### How to Fix in Flutter

You have **two options**:

#### Option A (Recommended): Consume the New Pre-Grouped Endpoint
Instead of grouping matches manually on device, consume the new backend endpoint:
```http
GET /sports/fixtures/grouped/?date=YYYY-MM-DD
```

**Response Format:**
```json
{
  "success": true,
  "count": 73,
  "total_fixtures": 168,
  "results": [
    {
      "league": {
        "id": 2,
        "name": "UEFA Champions League",
        "region": "Europe",
        "localized_region": {
          "it": "Europa",
          "en": "Europe",
          "es": "Europa",
          "fr": "Europe",
          "de": "Europa",
          "pt": "Europa",
          "tr": "Avrupa"
        },
        "country": { "name": "World", "code": null, "flag": null },
        "logo": "https://media.api-sports.io/football/leagues/2.png",
        "season_year": 2026
      },
      "count": 6,
      "fixtures": [ /* 6 UEFA Champions League matches */ ]
    },
    {
      "league": {
        "id": 12,
        "name": "CAF Champions League",
        "region": "Africa",
        "localized_region": {
          "it": "Africa",
          "en": "Africa",
          "es": "África",
          ...
        },
        "country": { "name": "World", "code": null, "flag": null },
        "logo": "https://media.api-sports.io/football/leagues/12.png",
        "season_year": 2026
      },
      "count": 1,
      "fixtures": [ /* Foresters vs Wiliete */ ]
    }
  ]
}
```

#### Option B: If Keeping Local Grouping in Dart
If you continue using the flat list (`GET /sports/fixtures/?date=...`), change the grouping key from `league.name` to `league.id`:

```dart
// ❌ INCORRECT (Causes the 9-match collision):
final groupKey = match.league?.name; 
// or
if (match.league?.name?.contains("Champions League") ?? false) ...

// ✅ CORRECT (Strictly isolated by tournament ID):
final int leagueId = match.league?.id ?? 0;
final groupKey = "${leagueId}_${match.league?.name ?? ''}";
```

---

## 3. Continental & Confederation Localizations

### What Changed in Backend
Every `league` object in all sports endpoints now includes:
1. `"region"`: Canonical English continent (`Europe`, `Africa`, `Asia`, `South America`, `North & Central America`, `Oceania`, `World`).
2. `"localized_region"`: 7-language localized dictionary (`en`, `it`, `es`, `fr`, `de`, `pt`, `tr`).

### What to Change in Flutter
* In `lib/core/utils/country_flag_helper.dart` and `lib/shared/widgets/league_header_card.dart`:
* Remove the hardcoded map of league IDs.
* Use the backend localization directly:

```dart
// Dart Model update
class LeagueModel {
  final int id;
  final String name;
  final String? region;
  final Map<String, String>? localizedRegion;
  final CountryModel? country;

  LeagueModel({
    required this.id,
    required this.name,
    this.region,
    this.localizedRegion,
    this.country,
  });

  factory LeagueModel.fromJson(Map<String, dynamic> json) {
    return LeagueModel(
      id: json['id'] ?? 0,
      name: json['name'] ?? '',
      region: json['region'],
      localizedRegion: json['localized_region'] != null
          ? Map<String, String>.from(json['localized_region'])
          : null,
      country: json['country'] != null ? CountryModel.fromJson(json['country']) : null,
    );
  }

  /// Resolves the header country/continent label for the current device language
  String getDisplayRegion(String languageCode) {
    if (country?.name == "World" || country?.name == "International") {
      return localizedRegion?[languageCode] ?? region ?? "World";
    }
    return country?.name ?? "";
  }
}
```

---

## 4. Upcoming Matches & Strict Date Filtering

### What Changed in Backend
* **Strict Date Bounding:** `GET /sports/fixtures/?status=upcoming&date=YYYY-MM-DD` now strictly returns matches scheduled on that day.
* **Leakage Elimination:** Calling `GET /sports/fixtures/?status=upcoming` without a date now defaults to the **next 24 hours** (`now + 24h`) instead of returning 15 days of future fixtures.
* **Multi-day Schedule:** To request multiple days, pass `&days=N` (e.g. `?status=upcoming&days=7`).

### What to Change in Flutter
* You can now safely pass `&date=${selectedDate.toIso8601String().split('T')[0]}` when fetching upcoming matches:
  ```http
  GET /sports/fixtures/?status=upcoming&date=2026-09-10
  ```
* You can remove the complex client-side post-filter `_isMatchOnDate` because the server now guarantees that no multi-week fixtures leak into today's view.

---

## 5. Fixture Coverage Metadata

### What Changed in Backend
Every fixture object in detail and list responses now includes a `coverage` object:
```json
"coverage": {
  "lineups": false,
  "statistics": false,
  "events": true
}
```

### What to Change in Flutter
In `lib/features/home/ui/match_details/widgets/lineups_tab_view.dart` and `statistics_tab_view.dart`:
* Check `fixture.coverage.lineups` and `fixture.coverage.statistics`.
* If `false`, immediately display the empty state:
  * *"Lineups not available for this tournament"*
  * *"Statistics not available for this tournament"*
* **Do not fire redundant HTTP requests** to `/fixtures/{id}/lineups/` or `/fixtures/{id}/statistics/` when `coverage` is `false`.

---

## 6. Real-Time Status & Clock Stoppage Time

### What Changed in Backend
1. **Clock Normalization:** Fixture object now returns a normalized `status` object alongside legacy fields:
   ```json
   "status": {
     "short": "2H",
     "long": "Second Half",
     "elapsed": 90,
     "extra": 4
   }
   ```
2. **Kickoff Invalidation:** When a match status transitions from `NS` to `1H` / `LIVE`, the backend immediately clears stale cache hashes. Background HTTP requests will no longer overwrite active WebSocket live matches with stale `"NS"` statuses.
3. **Suspended Matches (`SUSP` / `INT`):** Reconciled automatically by a Celery background worker every 10 minutes. If officially abandoned or postponed, the status updates to `ABD` or `PST` automatically.

---

## 7. Accent & Diacritic Search Normalization

### What Changed in Backend
`GET /sports/teams/?search=...` and `GET /sports/leagues/?search=...` now use PostgreSQL `unaccent`.

### What to Change in Flutter
* You no longer need to strip diacritics or accents on device before making search queries.
* Raw user input can be sent directly:
  * `"atletico"` $\rightarrow$ Matches `"Atlético Madrid"`, `"Alianza Atletico"`, etc.
  * `"sao paulo"` $\rightarrow$ Matches `"São Paulo"`, `"Sao Paulo"`.

---

## 8. Summary Checklist for Flutter Developers

| Module | Action Required | Status |
| :--- | :--- | :---: |
| **Home Screen** | Switch to `GET /sports/fixtures/grouped/?date=YYYY-MM-DD` OR group by `league.id`. | 🔴 Critical |
| **League Header** | Read `league.localized_region[langCode]` instead of hardcoded ID map. | 🟡 Recommended |
| **Upcoming Feed** | Pass `&date=YYYY-MM-DD` on `status=upcoming`. Remove client multi-day prune. | 🟢 Ready |
| **Match Details** | Inspect `fixture.coverage.lineups` / `statistics` before rendering tabs. | 🟢 Ready |
| **Search Screen** | Pass raw search text to `?search=...` without client normalization. | 🟢 Ready |

---

*For any questions or endpoint verifications, contact the backend team.*
