# Ramelia Lotstid Monitor - Uppdateringar

## 📋 Sammanfattning av ändringar

Tre huvudsakliga förbättringar har gjorts i systemet:

### 1. ✅ Fånga ALLA Ramelia-förekomster
**Problem:** Scriptet stannade efter första träffen av Ramelia  
**Lösning:** 
- `search_ramelia_in_area()` returnerar nu en **lista** med alla träffar
- Fortsätter söka genom alla tabeller och rader
- Lägger till `table_index` och `row_index` för bättre spårning

### 2. ⏱️ Var 30:e minut istället för varje timme
**Problem:** Kontrollen kördes endast en gång per timme  
**Lösning:**
- GitHub Actions cron-schema ändrat från `0 * * * *` till `*/30 * * * *`
- Meddelanden i koden uppdaterade

### 3. 📱 Visa senaste info vid app-start
**Problem:** Appen visade inte någon data vid uppstart  
**Lösning:**
- Appen hämtar `ramelia_state.json` från GitHub vid start
- Visar alla träffar sorterade med senaste först
- Speciell markering för den senaste posten
- Pull-to-refresh för manuell uppdatering

---

## 🚀 Installation och implementation

### Steg 1: Uppdatera Python-scriptet

Ersätt din `web_scraper.py` med den nya versionen från detta repo.

**Viktiga ändringar:**
```python
# search_ramelia_in_area returnerar nu en LISTA
ramelia_findings = []  # Samlar alla träffar
# ... fortsätter leta istället för return vid första träffen
return ramelia_findings

# check_all_areas använder extend istället för append
results = search_ramelia_in_area(page, config['area'], station)
if results:
    all_results.extend(results)  # Lägger till alla träffar
```

### Steg 2: Uppdatera GitHub Actions

1. Gå till ditt GitHub-repo
2. Navigera till `.github/workflows/ramelia-monitor.yml` (eller vad din workflow heter)
3. Uppdatera cron-schemat:

```yaml
on:
  schedule:
    - cron: '*/30 * * * *'  # Var 30:e minut
```

**OBS:** GitHub Actions kan ha en fördröjning på upp till 15 minuter för schemalagda jobb.

### Steg 3: Uppdatera React Native-appen

Ersätt din `App.js` med den nya versionen.

**VIKTIGT:** Uppdatera GitHub-URL:en i `fetchRameliaData()`:

```javascript
const response = await fetch(
  'https://raw.githubusercontent.com/DITT_GITHUB_USERNAME/DITT_REPO/main/ramelia_state.json'
);
```

Ersätt:
- `DITT_GITHUB_USERNAME` - ditt GitHub-användarnamn
- `DITT_REPO` - namnet på ditt repo

**Exempel:**
```javascript
const response = await fetch(
  'https://raw.githubusercontent.com/johndoe/ramelia-monitor/main/ramelia_state.json'
);
```

### Steg 4: Testa ändringarna

#### Testa Python-scriptet lokalt:
```bash
python web_scraper.py
```

Förväntad output:
```
✅ Totalt X Ramelia-förekomst(er) funna i Kvitsøy losformidling/-- All --
Nästa kontroll sker automatiskt om 30 minuter (via GitHub Actions)
```

#### Testa GitHub Actions:
1. Gå till "Actions" i ditt GitHub-repo
2. Välj "Ramelia Lotstid Monitor"
3. Klicka på "Run workflow" för manuell körning
4. Kontrollera att `ramelia_state.json` uppdateras

#### Testa appen:
1. Starta appen på din enhet/emulator
2. Kontrollera att data visas direkt
3. Senaste posten ska vara markerad med "⭐ SENASTE"
4. Dra ner för att uppdatera (pull-to-refresh)

---

## 📊 Ny datastruktur

### ramelia_state.json format:

```json
{
  "last_data": [
    {
      "dispatch_area": "Kvitsøy losformidling",
      "station": "-- All --",
      "row_data": "RAMELIA | 2024-01-15 14:30 | ...",
      "timestamp": "2024-01-15T14:25:10.123456",
      "cells": ["RAMELIA", "2024-01-15 14:30", "..."],
      "table_index": 1,
      "row_index": 5
    },
    {
      "dispatch_area": "Horten losformidling",
      "station": "-- All --",
      "row_data": "RAMELIA | 2024-01-15 18:00 | ...",
      "timestamp": "2024-01-15T14:25:15.789012",
      "cells": ["RAMELIA", "2024-01-15 18:00", "..."],
      "table_index": 2,
      "row_index": 3
    }
  ],
  "last_check": "2024-01-15T14:25:20.123456"
}
```

---

## 🎨 Nya UI-funktioner i appen

### Visuella förbättringar:
- **Senaste-märkning:** Den senaste posten är markerad med grön kant och "⭐ SENASTE"
- **Antal träffar:** Visar hur många Ramelia-poster som hittades
- **Pull-to-refresh:** Dra ner för att manuellt uppdatera
- **Senaste kontroll:** Visar när den senaste automatiska kontrollen gjordes
- **Sorterad lista:** Alla poster sorterade med senaste först

---

## 🔧 Felsökning

### Scriptet hittar inte flera träffar:
- Kontrollera att du använder den nya `web_scraper.py`
- Kör scriptet manuellt och kolla output
- Se till att det står "FORTSÄTT LETA" i kommentaren

### Appen visar ingen data:
- Kontrollera GitHub-URL:en i `fetchRameliaData()`
- Se till att `ramelia_state.json` finns i ditt repo
- Öppna URL:en i webbläsaren för att testa

### GitHub Actions körs inte var 30:e minut:
- Cron-schemat måste vara `*/30 * * * *`
- Kom ihåg: GitHub Actions kan ha upp till 15 min fördröjning
- Använd "workflow_dispatch" för manuell testning

---

## 📝 Sammanfattning av filer som ska uppdateras:

1. ✅ `web_scraper.py` - Ny version med multi-träff-support
2. ✅ `.github/workflows/ramelia-monitor.yml` - Uppdaterat schema (*/30)
3. ✅ `App.js` - Hämtar och visar data vid start
4. ⚙️ Glöm inte byta GitHub-URL i App.js!

---

## 🎉 Resultat

Efter implementering kommer systemet att:
- ✅ Hitta och spara ALLA Ramelia-poster
- ✅ Kontrollera var 30:e minut (istället för varje timme)
- ✅ Visa senaste info direkt när du öppnar appen
- ✅ Sortera och markera den senaste posten tydligt
- ✅ Möjliggöra manuell uppdatering med pull-to-refresh

---

**Lycka till med implementeringen! 🚢**
