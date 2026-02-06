from playwright.sync_api import sync_playwright
import time
import json
from datetime import datetime
import os
import sys


# Importera Firebase notifier om vi är i GitHub Actions
try:
    from firebase_notifier import notify_ramelia_change
    FIREBASE_ENABLED = True
    print("✅ Firebase notifier importerad!")
except ImportError as e:
    FIREBASE_ENABLED = False
    print(f"ℹ️  Firebase notifier inte tillgänglig: {e}")
except Exception as e:
    FIREBASE_ENABLED = False
    print(f"❌ Fel vid import av firebase_notifier: {e}")

# URL för webbplatsen
url = 'https://shiprep.no/shiprepwebui/CurrentPilotages.aspx'

def search_ramelia_in_area(page, dispatch_area, station_name):
    """
    Sök efter ALLA förekomster av Ramelia i ett specifikt losområde och station
    
    Args:
        page: Playwright page object
        dispatch_area: T.ex. "Kvitsøy losformidling"
        station_name: T.ex. "-- All --"
    
    Returns:
        list: Lista med alla Ramelia-förekomster (kan vara tom)
    """
    try:
        print(f"\n--- Söker i {dispatch_area} / {station_name} ---")
        
        # Gå till sidan med kortare timeout
        try:
            page.goto(url, wait_until='networkidle', timeout=20000)
            print("✓ Sida laddad")
        except Exception as e:
            print(f"⚠️  Timeout vid laddning av sida, försöker igen...")
            page.goto(url, wait_until='load', timeout=15000)
            print("✓ Sida laddad (med load istället för networkidle)")
        
        # Välj Pilot Dispatch dropdown
        dispatch_dropdown = page.locator('#ctl00_MainContent_PilotageDispatchDepartmentDropDown')
        print(f"📍 Väljer område: {dispatch_area}")
        dispatch_dropdown.select_option(label=dispatch_area)
        
        # Vänta lite för att nästa dropdown ska uppdateras
        time.sleep(2)
        
        # Välj Pilot Station dropdown
        station_dropdown = page.locator('#ctl00_MainContent_PilotageDipatchLocationDropDown')
        print(f"🏢 Väljer station: {station_name}")
        station_dropdown.select_option(label=station_name)
        
        # Vänta lite innan vi klickar på knappen
        time.sleep(1)
        
        # VIKTIGT: Tryck på "Show Pilotages" knappen för att ladda tabellen
        try:
            show_button = page.locator('input[type="submit"][value="Show Pilotages"]')
            if show_button.is_visible():
                print("✅ Klickar på 'Show Pilotages' knappen")
                show_button.click()
                # Vänta på att tabellen laddas efter knapptryck
                time.sleep(3)
            else:
                print("⚠️  'Show Pilotages' knappen inte synlig")
        except Exception as e:
            print(f"⚠️  Kunde inte klicka på 'Show Pilotages': {e}")
        
        # Hitta alla tabeller på sidan
        tables = page.locator('table').all()
        print(f"📋 Hittade {len(tables)} tabell(er)")
        
        ramelia_findings = []  # Lista för att samla ALLA träffar
        
        # Max antal Ramelia-förekomster att leta efter
        MAX_RAMELIA_FINDINGS = 8
        
        # Gå igenom varje tabell
        for table_index, table in enumerate(tables):
            try:
                # Använd en smart selector för att hitta ENDAST rader som innehåller "RAMELIA"
                # Detta är mycket snabbare än att iterera genom alla 2619 rader
                print(f"🔍 Söker efter Ramelia i tabell {table_index + 1}...")
                
                # Hitta alla rader i tabellen som innehåller text "RAMELIA" eller "Ramelia"
                # Vi använder :has-text() selector för att filtrera direkt
                ramelia_rows = table.locator('tr:has-text("RAMELIA"), tr:has-text("Ramelia")').all()
                
                print(f"✨ Hittade {len(ramelia_rows)} rad(er) med Ramelia")
                
                # Om inga rader hittades, fortsätt till nästa tabell
                if not ramelia_rows:
                    continue
                
                # Gå igenom endast de rader som innehåller Ramelia
                for row_index, row in enumerate(ramelia_rows):
                    # Kolla om vi redan hittat max antal
                    if len(ramelia_findings) >= MAX_RAMELIA_FINDINGS:
                        print(f"\n⏹️  Max antal ({MAX_RAMELIA_FINDINGS}) Ramelia-förekomster hittade - stoppar sökning")
                        return ramelia_findings
                    
                    try:
                        # Lägg till timeout för att undvika hängande operationer
                        cells = row.locator('td, th').all()
                        
                        # Använd timeout för inner_text() operationer
                        cell_texts = []
                        for cell in cells:
                            try:
                                text = cell.inner_text(timeout=2000).strip()
                                if text:
                                    cell_texts.append(text)
                            except Exception:
                                # Skippa celler som tar för lång tid
                                continue
                        
                        row_text = ' | '.join(cell_texts)
                        
                        print(f"\n⭐ RAMELIA HITTAD I TABELL {table_index + 1}! (Träff #{len(ramelia_findings) + 1})")
                        print(f"📋 Rad: {row_text}")
                        
                        ramelia_data = {
                            'dispatch_area': dispatch_area,
                            'station': station_name,
                            'row_data': row_text,
                            'timestamp': datetime.now().isoformat(),
                            'cells': cell_texts,
                            'table_index': table_index + 1,
                            'row_index': row_index
                        }
                        
                        # Skriv ut varje cell för bättre läsbarhet
                        print("\n📊 Detaljerad information:")
                        for i, cell_text in enumerate(cell_texts):
                            print(f"   Kolumn {i+1}: {cell_text}")
                        
                        ramelia_findings.append(ramelia_data)
                    
                    except Exception as row_error:
                        # Om vi får fel på en rad, fortsätt till nästa
                        print(f"⚠️  Fel vid läsning av rad: {row_error}")
                        continue
                
                # Om vi hittat Ramelia i denna tabell, rapportera
                if ramelia_findings:
                    print(f"\n✅ Totalt {len(ramelia_findings)} Ramelia-förekomst(er) funna hittills")
            
            except Exception as table_error:
                print(f"⚠️  Fel vid läsning av tabell {table_index + 1}: {table_error}")
                continue
        
        # När vi gått igenom alla tabeller
        if ramelia_findings:
            print(f"\n✅ Sökning slutförd - totalt {len(ramelia_findings)} Ramelia-förekomst(er) funna i {dispatch_area}/{station_name}")
            return ramelia_findings
        
        print("❌ Ramelia inte funnen")
        return []
        
    except Exception as e:
        print(f"❌ Fel vid sökning: {e}")
        import traceback
        traceback.print_exc()
        return []

def check_all_areas():
    """Sök igenom alla losområden och stationer"""
    
    # Konfiguration: vilka områden och stationer ska vi söka i

    search_config = [
        {
            'area': 'Kvitsøy losformidling',
            'stations': ['-- All --']
        },
        
        {
            'area': 'Horten losformidling',
            'stations': ['-- All --']
         },
         {
           'area': 'Lødingen losformidling',
        'stations': ['-- All --']
        }
    ]
    
    all_results = []
    
    with sync_playwright() as p:
        print("🔧 Startar webbläsare...")
        
        # Starta Chromium i headless mode (osynligt)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        # Sätt default timeout för sidan
        page.set_default_timeout(30000)  # 30 sekunder
        
        print("✓ Webbläsare startad")
        
        try:
            # Gå igenom varje område och station
            for config in search_config:
                for station in config['stations']:
                    results = search_ramelia_in_area(page, config['area'], station)
                    # results är nu en lista - lägg till alla träffar
                    if results:
                        all_results.extend(results)
                        # Om vi hittat Ramelia, behöver vi inte söka mer
                        print("✅ Ramelia funnen - avslutar sökning")
                        break
                if all_results:
                    break
            
        finally:
            print("\n🔒 Stänger webbläsare...")
            browser.close()
            print("✓ Webbläsare stängd")
    
    return all_results

def save_state(data):
    """Spara tillstånd till JSON-fil"""
    state = {
        'last_data': data,
        'last_check': datetime.now().isoformat()
    }
    
    with open('ramelia_state.json', 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    
    print("✓ Tillstånd sparat till ramelia_state.json")

def load_state():
    """Ladda tidigare tillstånd"""
    try:
        with open('ramelia_state.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("ℹ️  Ingen tidigare data (första körningen)")
        return None

def format_ramelia_info(data):
    """Formatera Ramelia-information för läsbar output"""
    if not data:
        return "Ingen data"
    
    result = []
    result.append(f"🌍 Område: {data.get('dispatch_area', 'N/A')}")
    result.append(f"🏢 Station: {data.get('station', 'N/A')}")
    result.append(f"🕐 Tidpunkt: {data.get('timestamp', 'N/A')}")
    result.append(f"📋 Data: {data.get('row_data', 'N/A')}")
    
    return '\n'.join(result)
    
def check_for_changes():
    """Huvudfunktion - kolla efter ändringar"""
    print(f"\n{'='*70}")
    print(f"🔍 KONTROLL STARTAD: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    
    # Sök efter Ramelia
    current_results = check_all_areas()
    
    if current_results:
        print(f"\n✅ Hittade {len(current_results)} träff(ar) för Ramelia!")
        
        # Ladda tidigare tillstånd
        previous_state = load_state()
        
        # Jämför med tidigare
        if previous_state and previous_state.get('last_data'):
            prev_data = previous_state['last_data']
            
            # Jämför row_data för att se om något ändrats
            prev_rows = [item['row_data'] for item in prev_data] if isinstance(prev_data, list) else []
            curr_rows = [item['row_data'] for item in current_results]
            
            if prev_rows != curr_rows:
                print("\n🚨 FÖRÄNDRING UPPTÄCKT! 🚨")
                print("\n📜 TIDIGARE DATA:")
                for item in prev_data:
                    print(format_ramelia_info(item))
                print("\n📜 NY DATA:")
                for item in current_results:
                    print(format_ramelia_info(item))
                
                # Skicka Firebase-notifikation
                if FIREBASE_ENABLED and os.environ.get('FIREBASE_SERVICE_ACCOUNT'):
                    print("\n📲 Skickar push-notifikation...")
                    notify_ramelia_change(prev_data, current_results)
                else:
                    print("\nℹ️  Firebase inte konfigurerad - ingen notifikation skickad")
            else:
                print("\n✓ Ingen förändring sedan senaste kontrollen")
        else:
            print("\nℹ️  Första körningen - sparar initialt tillstånd")
        
        # Spara nuvarande tillstånd
        save_state(current_results)
        
        # Skriv ut detaljer
        print("\n" + "="*70)
        print("📊 AKTUELL INFORMATION:")
        print("="*70)
        for result in current_results:
            print("\n" + format_ramelia_info(result))
            
    else:
        print("\n❌ Ramelia inte funnen i något område")
        save_state(None)


# Huvudprogram
if __name__ == '__main__':
    print("🚢" + "="*68 + "🚢")
    print("   RAMELIA LOTSTID-ÖVERVAKNING MED PLAYWRIGHT")
    print("🚢" + "="*68 + "🚢")
       
    # Kör EN GÅNG (perfekt för GitHub Actions)
    check_for_changes()
    
    print("\n✅ Kontroll slutförd!")
    print("Nästa kontroll sker automatiskt om 30 minuter (via GitHub Actions)\n")
