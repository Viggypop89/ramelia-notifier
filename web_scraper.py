from playwright.sync_api import sync_playwright
import time
import json
import os
import requests
from pathlib import Path
from datetime import datetime

# Konfiguration
DATA_FILE = Path('ramelia_data.json')
FIREBASE_URL = "din_firebase_url_kommer_här"  # Vi sätter detta senare

# URL för webbplatsen
url = 'https://shiprep.no/shiprepwebui/CurrentPilotages.aspx'

def click_show_pilotages(page):
    """Försök hitta och klicka på Show Pilotages-knappen"""
    try:
        # Försök hitta knappen med olika sökvägar
        selectors = [
            'input[type="submit"][value="Show Pilotages"]',
            'button:has-text("Show Pilotages")',
            'input[value="Show Pilotages"]',
            '//input[@type="submit"][contains(@value, "Show")]',
            '#btnShowPilotages'  # Lägg till fler selectors om behövs
        ]
        
        for selector in selectors:
            try:
                button = page.locator(selector).first
                if button.is_visible():
                    print(f"✅ Hittade knappen med selector: {selector}")
                    button.click()
                    print("✅ Klickade på 'Show Pilotages'")
                    # Vänta lite extra efter klicket
                    page.wait_for_load_state('networkidle')
                    time.sleep(3)
                    return True
            except Exception as e:
                print(f"❌ Kunde inte klicka med {selector}: {str(e)}")
                continue
        
        print("❌ Kunde inte hitta 'Show Pilotages'-knappen")
        # Ta en skärmdump för felsökning
        page.screenshot(path='error_show_button.png')
        print("📸 Sparade skärmdump som 'error_show_button.png'")
        return False
        
    except Exception as e:
        print(f"❌ Fel vid sökning efter knapp: {str(e)}")
        return False

def search_ramelia_in_area(page, dispatch_area, station_name):
    """
    Sök efter Ramelia i ett specifikt losområde och station
    
    Args:
        page: Playwright page object
        dispatch_area: T.ex. "Kvitsøy losformidling"
        station_name: T.ex. "Fedje" eller "-- All --"
    """
    try:
        print(f"\n--- Söker i {dispatch_area} / {station_name} ---")
        
        # Gå till sidan
        page.goto(url, wait_until='networkidle', timeout=30000)
        print("✓ Sida laddad")
        
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
        
        # Vänta på att tabellen laddas
        time.sleep(3)
                # Klicka på Show Pilotages
        if not click_show_pilotages(page):
            print("❌ Kunde inte klicka på Show Pilotages, försöker fortsätta ändå...")
        
        # Ta en skärmdump för felsökning
        page.screenshot(path=f'screenshot_{dispatch_area}_{station_name}.png'.replace(' ', '_'))
        print(f"📸 Sparade skärmdump som 'screenshot_{dispatch_area}_{station_name}.png'")
        
        # Spara sidans källa för felsökning
        with open('page_source.html', 'w', encoding='utf-8') as f:
            f.write(page.content())
        print("💾 Sparade sidans källa till 'page_source.html'")
        # Hitta alla tabeller på sidan
        tables = page.locator('table').all()
        print(f"📋 Hittade {len(tables)} tabell(er)")
        
        ramelia_data = None
        
        # Gå igenom varje tabell
        for table_index, table in enumerate(tables):
            # Hitta alla rader i tabellen
            rows = table.locator('tr').all()
            
            for row_index, row in enumerate(rows):
                # Hämta text från alla celler i raden
                cells = row.locator('td, th').all()
                cell_texts = [cell.inner_text().strip() for cell in cells if cell.inner_text().strip()]
                row_text = ' | '.join(cell_texts)
                
                # Kolla om raden innehåller "Ramelia"
                if 'RAMELIA' in row_text.upper() or 'Ramelia' in row_text:
                    print(f"\n⭐ RAMELIA HITTAD I TABELL {table_index + 1}!")
                    print(f"📋 Rad {row_index}: {row_text}")
                    
                    ramelia_data = {
                        'dispatch_area': dispatch_area,
                        'station': station_name,
                        'row_data': row_text,
                        'timestamp': datetime.now().isoformat(),
                        'cells': cell_texts
                    }
                    
                    # Skriv ut varje cell för bättre läsbarhet
                    print("\n📊 Detaljerad information:")
                    for i, cell_text in enumerate(cell_texts):
                        print(f"   Kolumn {i+1}: {cell_text}")
                    
                    return ramelia_data
        
        print("❌ Ramelia inte funnen i denna tabell")
        return None
        
    except Exception as e:
        print(f"❌ Fel vid sökning: {e}")
        import traceback
        traceback.print_exc()
        return None

def check_all_areas():
    """Sök igenom alla losområden och stationer"""
    
    # Konfiguration: vilka områden och stationer ska vi söka i
    search_config = [
        {
            'area': 'Kvitsøy losformidling',
            'stations': ['-- All --']  # Endast sök i "-- All --" för att undvika dubbletter
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
        
        print("✓ Webbläsare startad")
        
        try:
            # Gå igenom varje område och station
            for config in search_config:
                for station in config['stations']:
                    result = search_ramelia_in_area(page, config['area'], station)
                    if result:
                        all_results.append(result)
                        # Om vi hittat Ramelia, kanske vi inte behöver söka vidare?
                        # Ta bort break nedan om du vill söka i alla områden ändå
                        # break
            
        finally:
            browser.close()
            print("\n🔒 Webbläsare stängd")
    
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
    result.append(f"🌍 Område: {data['dispatch_area']}")
    result.append(f"🏢 Station: {data['station']}")
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
                # TODO: Skicka Android-notifikation här
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
    print("\nTryck Ctrl+C för att avsluta\n")
    
    try:
        # Första kontrollen
        check_for_changes()
        
        print(f"\n⏰ Nästa kontroll om 30 minuter...")
        print("(Programmet körs i bakgrunden)\n")
        
        # Upprepa var 30:e minut
        while True:
            time.sleep(1800)  # 30 minuter = 1800 sekunder
            check_for_changes()
            print(f"\n⏰ Nästa kontroll om 30 minuter...")
            
    except KeyboardInterrupt:
        print("\n\n👋 Övervakning avslutad av användare")
        print("Hej då! 🚢")
