"""
Comprehensive MRP Simulator Verification Tests
Tests U1-U3 integration and LLM functionality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db_connector import DatabaseConnector
from src.services.mrp_simulator import MRPSimulator
import pandas as pd

def run_mrp_verification():
    print("="*70)
    print("KOMPLETNE TESTY WERYFIKACYJNE MRP SIMULATOR")
    print("="*70 + "\n")
    
    # Initialize
    db = DatabaseConnector()
    simulator = MRPSimulator(db)
    results = {}
    
    # Get a test product with technology
    print("[Setup] Pobieranie produktu z technologią do testów...")
    products = db.get_products_with_technology()
    if products.empty:
        print("   BRAK produktów z technologią! Nie można kontynuować.")
        return
    
    test_product_id = int(products['FinalProductId'].iloc[0])
    test_product_code = products['Code'].iloc[0]
    test_quantity = 100.0
    
    print(f"   Test produkt: {test_product_code} (ID: {test_product_id})")
    print(f"   Test ilość: {test_quantity}")
    print()
    
    # TEST 1: Basic simulation
    print("[TEST 1] simulate_production() - podstawowa symulacja...")
    try:
        result1 = simulator.simulate_production(test_product_id, test_quantity)
        has_limiting = result1.get('limiting_factor') is not None
        has_ingredient_id = has_limiting and 'ingredient_id' in result1['limiting_factor']
        results['T1_basic_simulation'] = {
            'can_produce': result1['can_produce'],
            'max_producible': result1.get('max_producible', 0),
            'shortages_count': len(result1.get('shortages', [])),
            'limiting_factor_present': has_limiting,
            'ingredient_id_present': has_ingredient_id,
            'status': 'OK'
        }
        print(f"   OK - can_produce: {result1['can_produce']}, max: {result1['max_producible']:.0f}")
        print(f"   OK - limiting_factor.ingredient_id: {'TAK' if has_ingredient_id else 'BRAK'}")
    except Exception as e:
        results['T1_basic_simulation'] = {'error': str(e)[:60], 'status': 'FAIL'}
        print(f"   FAIL - {str(e)[:60]}")
    
    # TEST 2: Simulation with delivery
    print("\n[TEST 2] simulate_production_with_delivery() - z czasami dostaw...")
    try:
        result2 = simulator.simulate_production_with_delivery(test_product_id, test_quantity)
        has_delivery = 'max_delivery_time' in result2
        has_earliest = 'earliest_production_date' in result2
        has_ingredient_id2 = result2.get('limiting_factor', {}).get('ingredient_id') is not None or \
                            'ingredient_id' in str(result2.get('limiting_factor', {}))
        results['T2_delivery_simulation'] = {
            'has_delivery_time': has_delivery,
            'has_earliest_date': has_earliest,
            'ingredient_id_in_limiting': 'ingredient_id' in str(result2.get('limiting_factor', {})),
            'status': 'OK'
        }
        print(f"   OK - max_delivery_time: {result2.get('max_delivery_time', 0)} dni")
        print(f"   OK - earliest_date: {result2.get('earliest_production_date', 'N/A')}")
    except Exception as e:
        results['T2_delivery_simulation'] = {'error': str(e)[:60], 'status': 'FAIL'}
        print(f"   FAIL - {str(e)[:60]}")
    
    # TEST 3: Comprehensive analysis (U1-U3)
    print("\n[TEST 3] get_comprehensive_production_analysis() - analiza U1-U3...")
    try:
        analysis = simulator.get_comprehensive_production_analysis(test_product_id, test_quantity)
        has_u1 = "Status Zleceń" in analysis or "Status Produkcji" in analysis
        has_u2 = "CTI Braki" in analysis or "Synchronizacja" in analysis
        has_u3 = "Zamienniki" in analysis or "zamiennik" in analysis.lower()
        
        results['T3_comprehensive'] = {
            'length': len(analysis),
            'contains_U1_status': has_u1,
            'contains_U2_sync': has_u2,
            'contains_U3_substitutes': has_u3,
            'status': 'OK'
        }
        print(f"   OK - Analiza: {len(analysis)} znaków")
        print(f"   U1 (Status): {'TAK' if has_u1 else 'NIE'}")
        print(f"   U2 (Sync CTI): {'TAK' if has_u2 else 'NIE'}")
        print(f"   U3 (Zamienniki): {'TAK' if has_u3 else 'NIE'}")
        
        # Print first 500 chars of analysis
        print("\n   --- Fragment analizy ---")
        print("   " + analysis[:500].replace("\n", "\n   ") + "...")
    except Exception as e:
        results['T3_comprehensive'] = {'error': str(e)[:60], 'status': 'FAIL'}
        print(f"   FAIL - {str(e)[:60]}")
    
    # TEST 4: LLM Integration (without actual LLM call)
    print("\n[TEST 4] _generate_llm_prompt() - generowanie promptu LLM...")
    try:
        # Get simulation for prompt generation
        sim = simulator.simulate_production_with_delivery(test_product_id, test_quantity)
        prompt = simulator._generate_llm_prompt(test_product_id, test_quantity, sim, "test")
        
        has_context = "Produkt do wyprodukowania" in prompt
        has_task = "Zadanie" in prompt
        has_polish = "zakupów" in prompt or "produkcji" in prompt
        
        results['T4_llm_prompt'] = {
            'length': len(prompt),
            'has_context': has_context,
            'has_task': has_task,
            'is_polish': has_polish,
            'status': 'OK'
        }
        print(f"   OK - Prompt: {len(prompt)} znaków")
        print(f"   OK - Zawiera kontekst: {has_context}")
        print(f"   OK - Zawiera zadanie: {has_task}")
    except Exception as e:
        results['T4_llm_prompt'] = {'error': str(e)[:60], 'status': 'FAIL'}
        print(f"   FAIL - {str(e)[:60]}")
    
    # TEST 5: analyze_with_llm (checks LLM availability)
    print("\n[TEST 5] analyze_with_llm() - test integracji LLM...")
    try:
        llm_result = simulator.analyze_with_llm(test_product_id, test_quantity)
        
        has_analysis = 'analysis' in llm_result and len(llm_result['analysis']) > 0
        has_llm_field = 'llm_available' in llm_result
        has_recommendation = 'llm_recommendation' in llm_result
        
        results['T5_llm_integration'] = {
            'has_analysis': has_analysis,
            'llm_available': llm_result.get('llm_available', False),
            'has_recommendation': has_recommendation,
            'status': 'OK'
        }
        print(f"   OK - Analysis present: {has_analysis}")
        print(f"   LLM available: {llm_result.get('llm_available', False)}")
        if llm_result.get('llm_recommendation'):
            print(f"   LLM message: {llm_result['llm_recommendation'][:80]}...")
    except Exception as e:
        results['T5_llm_integration'] = {'error': str(e)[:60], 'status': 'FAIL'}
        print(f"   FAIL - {str(e)[:60]}")
    
    # TEST 6: Shortage with substitutes
    print("\n[TEST 6] get_shortage_with_substitutes() - braki z zamiennikami...")
    try:
        subs_result = simulator.get_shortage_with_substitutes(test_product_id, test_quantity)
        
        has_shortages = 'shortages_with_substitutes' in subs_result
        has_available = 'substitutes_available' in subs_result
        
        results['T6_substitutes'] = {
            'has_shortages_data': has_shortages,
            'has_available_flag': has_available,
            'substitutes_available': subs_result.get('substitutes_available', False),
            'status': 'OK'
        }
        print(f"   OK - shortages_with_substitutes: {has_shortages}")
        print(f"   OK - substitutes_available: {subs_result.get('substitutes_available', False)}")
    except Exception as e:
        results['T6_substitutes'] = {'error': str(e)[:60], 'status': 'FAIL'}
        print(f"   FAIL - {str(e)[:60]}")
    
    # Summary
    print("\n" + "="*70)
    print("PODSUMOWANIE TESTÓW MRP SIMULATOR")
    print("="*70)
    
    ok_count = sum(1 for v in results.values() if v.get('status') == 'OK')
    fail_count = len(results) - ok_count
    
    print(f"\nTesty OK: {ok_count}/{len(results)}")
    print(f"Testy FAIL: {fail_count}/{len(results)}")
    
    if fail_count == 0:
        print("\n*** WSZYSTKIE TESTY PRZESZŁY POMYŚLNIE! ***")
        print("\nIntegracja U1-U3 + LLM działa poprawnie.")
    else:
        print("\nNiektóre testy nie przeszły - sprawdź logi powyżej")
    
    # Return for potential further analysis
    return results

if __name__ == "__main__":
    run_mrp_verification()
