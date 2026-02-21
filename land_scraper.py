#!/usr/bin/env python3
"""
Land Search Scraper
Scrapes landsearch.com, landwatch.com, and land.com for land listings
matching specific criteria across multiple regions.
"""

import json
import re
import time
from html.parser import HTMLParser
from urllib.parse import urlencode, urljoin

# Search criteria
PRICE_MIN = 200000
PRICE_MAX = 500000
ACRES_MIN = 3
ACRES_MAX = 5

# Search regions - organized by airport/region
REGIONS = {
    "Portland OR Metro (PDX)": {
        "state": "OR",
        "counties": ["Washington", "Clackamas", "Yamhill", "Columbia"],
        "airport": "PDX"
    },
    "WA Columbia Gorge (PDX)": {
        "state": "WA",
        "counties": ["Skamania"],
        "airport": "PDX",
        "notes": "Up to Stevenson"
    },
    "Tacoma WA Area (SEA-TAC)": {
        "state": "WA",
        "counties": ["Pierce", "King South"],
        "airport": "SEA-TAC"
    },
    "Santa Fe NM Area (ABQ)": {
        "state": "NM",
        "counties": ["Santa Fe", "Bernalillo", "Sandoval"],
        "airport": "ABQ"
    },
    "Southern California Border (SAN)": {
        "state": "CA",
        "counties": ["San Diego"],
        "airport": "SAN"
    },
    "Colorado Front Range (DEN/COS)": {
        "state": "CO",
        "counties": ["El Paso", "Douglas", "Jefferson", "Boulder", "Larimer"],
        "airport": "DEN/COS"
    }
}

class SimpleHTMLExtractor(HTMLParser):
    """Simple HTML parser to extract text and links"""
    def __init__(self):
        super().__init__()
        self.links = []
        self.current_text = []
        
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = dict(attrs).get('href', '')
            if href:
                self.links.append(href)
    
    def handle_data(self, data):
        self.current_text.append(data.strip())
    
    def get_text(self):
        return ' '.join(filter(None, self.current_text))


def build_landsearch_url(state, county=None):
    """Build URL for landsearch.com with filters"""
    state_abbr = state.lower()
    base_url = f"https://www.landsearch.com/properties/{state_abbr}"
    
    params = {
        'minPrice': PRICE_MIN,
        'maxPrice': PRICE_MAX,
        'minAcres': ACRES_MIN,
        'maxAcres': ACRES_MAX
    }
    
    if county:
        county_slug = county.lower().replace(' ', '-')
        base_url = f"https://www.landsearch.com/properties/{county_slug}-county-{state_abbr}"
    
    url = f"{base_url}?{urlencode(params)}"
    return url


def build_landwatch_url(state, county=None):
    """Build URL for landwatch.com with filters"""
    state_abbr = state.upper()
    base_url = f"https://www.landwatch.com/{state}/land-for-sale"
    
    params = {
        'MinPrice': PRICE_MIN,
        'MaxPrice': PRICE_MAX,
        'MinAcres': ACRES_MIN,
        'MaxAcres': ACRES_MAX
    }
    
    if county:
        params['County'] = county
    
    url = f"{base_url}?{urlencode(params)}"
    return url


def build_land_com_url(state, county=None):
    """Build URL for land.com with filters"""
    state_name = {
        'OR': 'oregon', 'WA': 'washington', 'NM': 'new-mexico',
        'CA': 'california', 'CO': 'colorado'
    }.get(state, state.lower())
    
    base_url = f"https://www.land.com/{state_name}"
    
    params = {
        'minPrice': PRICE_MIN,
        'maxPrice': PRICE_MAX,
        'minAcres': ACRES_MIN,
        'maxAcres': ACRES_MAX
    }
    
    url = f"{base_url}?{urlencode(params)}"
    return url


def generate_search_urls():
    """Generate all search URLs for all regions and sites"""
    urls = {}
    
    for region_name, region_data in REGIONS.items():
        urls[region_name] = {
            'region_data': region_data,
            'searches': []
        }
        
        state = region_data['state']
        
        # Add state-wide searches
        urls[region_name]['searches'].append({
            'site': 'landsearch.com',
            'url': build_landsearch_url(state),
            'scope': 'state-wide'
        })
        urls[region_name]['searches'].append({
            'site': 'landwatch.com',
            'url': build_landwatch_url(state),
            'scope': 'state-wide'
        })
        urls[region_name]['searches'].append({
            'site': 'land.com',
            'url': build_land_com_url(state),
            'scope': 'state-wide'
        })
        
        # Add county-specific searches
        for county in region_data.get('counties', []):
            urls[region_name]['searches'].append({
                'site': 'landsearch.com',
                'url': build_landsearch_url(state, county),
                'scope': f'{county} County'
            })
            urls[region_name]['searches'].append({
                'site': 'landwatch.com',
                'url': build_landwatch_url(state, county),
                'scope': f'{county} County'
            })
    
    return urls


def main():
    """Generate search URLs and save to file"""
    print("Land Search Scraper")
    print("=" * 80)
    print(f"Search Criteria:")
    print(f"  Price: ${PRICE_MIN:,} - ${PRICE_MAX:,}")
    print(f"  Acreage: {ACRES_MIN} - {ACRES_MAX} acres")
    print(f"  Road access: Noted if mentioned")
    print(f"  Zoning: Flagging ag-only/recreational/conservation")
    print("=" * 80)
    print()
    
    urls = generate_search_urls()
    
    # Save URLs to file for reference
    with open('/data/.openclaw/workspace/search-urls.json', 'w') as f:
        json.dump(urls, f, indent=2)
    
    print(f"Generated {sum(len(r['searches']) for r in urls.values())} search URLs")
    print("URLs saved to: search-urls.json")
    print()
    print("Next step: Use browser automation to visit each URL and extract listings")
    
    # Print sample URLs for each region
    for region_name, region_info in urls.items():
        print(f"\n{region_name}:")
        for search in region_info['searches'][:2]:  # Show first 2 per region
            print(f"  {search['site']} ({search['scope']}): {search['url'][:80]}...")


if __name__ == '__main__':
    main()
