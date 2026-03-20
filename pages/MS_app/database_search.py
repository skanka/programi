import requests
import pandas as pd

def calculate_mass_range(target_mass, ppm_tolerance=5):
    """
    Изчислява минималната и максималната маса въз основа на 
    допустимата грешка в ppm (parts per million).
    """
    delta = (target_mass * ppm_tolerance) / 1e6
    min_mass = target_mass - delta
    max_mass = target_mass + delta
    return min_mass, max_mass

def search_pubchem_by_mass(target_mass, ppm_tolerance=5):
    """
    Търси съединения в PubChem по точна маса с даден ppm толеранс.
    """
    min_m, max_m = calculate_mass_range(target_mass, ppm_tolerance)
    
    # PubChem API URL за търсене по масов диапазон
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/mass/{min_m}:{max_m}/property/IsomericSMILES,MolecularFormula,ExactMass/JSON"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if 'PropertyTable' in data:
            return data['PropertyTable']['Properties']
    return []

def search_massbank_by_mass(target_mass, ppm_tolerance=5):
    """
    Търси спектри в MassBank Europe API по маса на прекурсора.
    Забележка: API структурата на MassBank изисква специфични параметри,
    тук правим базова заявка към REST API-то им.
    """
    # MassBank обикновено приема толеранс в Da (Далтони), така че преобразуваме ppm в Da
    delta_da = (target_mass * ppm_tolerance) / 1e6
    
    # Примерен Endpoint за MassBank (може да изисква допълнителна настройка според документацията им)
    url = f"https://massbank.eu/MassBank/api/spectra?mz={target_mass}&tol={delta_da}"
    
    # Тъй като MassBank API понякога изисква хедъри за заявката:
    headers = {'Accept': 'application/json'}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Грешка при свързване с MassBank: {e}")
        
    return []

# --- Пример за тестване на кода изолирано ---
if __name__ == "__main__":
    # Нека тестваме с примерна маса на прекурсорен йон (напр. Кофеин с протон)
    test_mass = 195.0882 
    
    print(f"Търсене за маса {test_mass} с точност 5 ppm...")
    
    pubchem_results = search_pubchem_by_mass(test_mass, 5)
    print(f"Намерени кандидати в PubChem: {len(pubchem_results)}")
    if pubchem_results:
        print(f"Първи резултат: {pubchem_results[0]}")
        
    # Забележка: Реалното MassBank API може да изисква специфичен формат на търсене
    # massbank_results = search_massbank_by_mass(test_mass, 5)
    # print(f"Намерени кандидати в MassBank: {len(massbank_results)}")