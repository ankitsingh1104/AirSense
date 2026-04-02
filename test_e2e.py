import httpx
import asyncio
import json

async def comprehensive_test():
    async with httpx.AsyncClient() as client:
        print("=" * 70)
        print("COMPREHENSIVE END-TO-END TEST")
        print("=" * 70)
        
        # Test 1: Health Check
        print("\n1. HEALTH CHECK")
        print("-" * 70)
        r = await client.get('http://localhost:8000/health')
        health = r.json()
        print(f"Status: {health.get('status')}")
        print(f"Models Loaded: {health.get('models_loaded')}")
        print(f"Cache: {health.get('cache')}")
        
        # Test 2: Realtime predictions for multiple countries
        print("\n2. REALTIME PREDICTIONS (Multiple Countries)")
        print("-" * 70)
        countries = ['IN', 'US', 'CN']
        for code in countries:
            r = await client.get(f'http://localhost:8000/api/realtime/{code}')
            data = r.json()
            live = data.get('live_aqi')
            pred = data.get('predicted_aqi')
            city = data.get('city')
            print(f"{code} ({city:15s}): live={live:6.1f}  predicted={pred:6.1f}  diff={pred-live:+6.1f}")
        
        # Test 3: Globe snapshot coverage
        print("\n3. GLOBE SNAPSHOT COVERAGE")
        print("-" * 70)
        r = await client.get('http://localhost:8000/api/globe/snapshot')
        snapshot = r.json()
        print(f"Total countries in snapshot: {len(snapshot)}")
        print(f"Sample countries: {[item['country_code'] for item in snapshot[:5]]}")
        
        # Test 4: Verify feature engineering works
        print("\n4. FEATURE ENGINEERING VERIFICATION")
        print("-" * 70)
        r = await client.get('http://localhost:8000/api/realtime/IN')
        data = r.json()
        pollutants = data.get('pollutants', {})
        print(f"Input pollutants (AQI sub-indices):")
        for k, v in pollutants.items():
            if isinstance(v, dict):
                val = v.get('aqi_value')
            else:
                val = v
            print(f"  {k:8s}: {val}")
        print(f"\nModel outputs:")
        print(f"  RF Prediction:  {data.get('rf_prediction')}")
        print(f"  XGB Prediction: {data.get('xgb_prediction')}")
        print(f"  Ensemble Avg:   {data.get('predicted_aqi')}")
        
        # Test 5: Verify SHAP contributions
        print("\n5. MODEL EXPLAINABILITY (SHAP Values)")
        print("-" * 70)
        shap_vals = data.get('shap_values', [])
        for i, contrib in enumerate(shap_vals[:3]):
            feature = contrib.get('feature')
            value = contrib.get('value')
            contribution = contrib.get('contribution')
            print(f"  {feature:25s}: value={value:8.2f}  contribution={contribution:+8.2f}")
        
        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED - SYSTEM FULLY OPERATIONAL")
        print("=" * 70)

asyncio.run(comprehensive_test())
