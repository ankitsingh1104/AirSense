import httpx
import asyncio

async def test():
    async with httpx.AsyncClient() as client:
        url = 'https://api.waqi.info/feed/New%20Delhi/?token=d0e77067652248388ea1ca6d5b116133dbbf00ac'
        r = await client.get(url, timeout=10)
        data = r.json()
        if data.get('status') == 'ok':
            d = data['data']
            print('Raw WAQI Response for Delhi:')
            print('  aqi:', d.get('aqi'))
            iaqi = d.get('iaqi', {})
            print('  iaqi (raw concentrations):')
            for k in ['co', 'o3', 'no2', 'pm25']:
                v = iaqi.get(k, {}).get('v', 'N/A')
                print('    ' + k + ':', v)

asyncio.run(test())
