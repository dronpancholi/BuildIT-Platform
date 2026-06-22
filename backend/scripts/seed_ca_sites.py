#!/usr/bin/env python3
"""
Seed Canadian Citation Sites — 200 Canadian Directory Sites
==========================================================
Run: python scripts/seed_ca_sites.py
"""

from __future__ import annotations

from seed_helper import seed_sites

# ============================================================================
# CA SITES — Tier 1: High Priority (25 sites)
# ============================================================================
TIER1_CA = [
    {"name": "Yellow Pages Canada", "url": "https://www.yellowpages.ca", "submission_url": "https://www.yellowpages.ca/submit", "category": "local", "geo_target": "ca", "difficulty_score": 35, "domain_authority": 88, "monthly_visitors": 5000000, "importance_score": 85, "submission_difficulty": "medium", "estimated_field_count": 22},
    {"name": "Yelp Canada", "url": "https://www.yelp.ca", "submission_url": "https://biz.yelp.com/signup", "category": "review", "geo_target": "ca", "difficulty_score": 50, "domain_authority": 95, "monthly_visitors": 8000000, "importance_score": 90, "submission_difficulty": "medium", "estimated_field_count": 25},
    {"name": "Google Business Profile Canada", "url": "https://business.google.com", "submission_url": "https://business.google.com/create", "category": "general", "geo_target": "ca", "difficulty_score": 60, "domain_authority": 98, "monthly_visitors": 50000000, "importance_score": 98, "submission_difficulty": "hard", "estimated_field_count": 30},
    {"name": "Bing Places Canada", "url": "https://www.bingplaces.com", "submission_url": "https://www.bingplaces.com/signup", "category": "general", "geo_target": "ca", "difficulty_score": 35, "domain_authority": 90, "monthly_visitors": 10000000, "importance_score": 85, "submission_difficulty": "medium", "estimated_field_count": 20},
    {"name": "Facebook Canada", "url": "https://www.facebook.com", "submission_url": "https://www.facebook.com/pages/create", "category": "social", "geo_target": "ca", "difficulty_score": 40, "domain_authority": 99, "monthly_visitors": 200000000, "importance_score": 95, "submission_difficulty": "easy", "estimated_field_count": 20},
    {"name": "LinkedIn Canada", "url": "https://www.linkedin.com", "submission_url": "https://www.linkedin.com/company/setup/new", "category": "social", "geo_target": "ca", "difficulty_score": 35, "domain_authority": 98, "monthly_visitors": 80000000, "importance_score": 90, "submission_difficulty": "easy", "estimated_field_count": 18},
    {"name": "411.ca", "url": "https://www.411.ca", "submission_url": "https://www.411.ca/add-listing", "category": "local", "geo_target": "ca", "difficulty_score": 20, "domain_authority": 72, "monthly_visitors": 1500000, "importance_score": 75, "submission_difficulty": "easy", "estimated_field_count": 18},
    {"name": "Canada411", "url": "https://www.canada411.ca", "submission_url": "https://www.canada411.ca/add-listing", "category": "local", "geo_target": "ca", "difficulty_score": 20, "domain_authority": 70, "monthly_visitors": 1200000, "importance_score": 72, "submission_difficulty": "easy", "estimated_field_count": 18},
    {"name": "Brownbook Canada", "url": "https://www.brownbook.net", "submission_url": "https://www.brownbook.net/add-business", "category": "general", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 55, "monthly_visitors": 200000, "importance_score": 55, "submission_difficulty": "easy", "estimated_field_count": 12},
    {"name": "Hotfrog Canada", "url": "https://www.hotfrog.ca", "submission_url": "https://www.hotfrog.ca/add-your-business", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 50, "monthly_visitors": 120000, "importance_score": 50, "submission_difficulty": "easy", "estimated_field_count": 12},
    {"name": "iLocal.ca", "url": "https://www.ilocal.ca", "submission_url": "https://www.ilocal.ca/add-listing", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 42, "monthly_visitors": 60000, "importance_score": 45, "submission_difficulty": "easy", "estimated_field_count": 12},
    {"name": "WebLocal.ca", "url": "https://www.weblocal.ca", "submission_url": "https://www.weblocal.ca/add-listing", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 40, "monthly_visitors": 50000, "importance_score": 42, "submission_difficulty": "easy", "estimated_field_count": 12},
    {"name": "2findlocal.ca", "url": "https://www.2findlocal.com/ca", "submission_url": "https://www.2findlocal.com/add-business", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 42, "monthly_visitors": 60000, "importance_score": 42, "submission_difficulty": "easy", "estimated_field_count": 10},
    {"name": "Cylex.ca", "url": "https://www.cylex.ca", "submission_url": "https://www.cylex.ca/add-business", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 45, "monthly_visitors": 80000, "importance_score": 45, "submission_difficulty": "easy", "estimated_field_count": 10},
    {"name": "11880.com Canada", "url": "https://www.11880.com/ca", "submission_url": "https://www.11880.com/ca/add-business", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 48, "monthly_visitors": 90000, "importance_score": 48, "submission_difficulty": "easy", "estimated_field_count": 10},
    {"name": "TripAdvisor Canada", "url": "https://www.tripadvisor.ca", "submission_url": "https://www.tripadvisor.ca/Owners", "category": "review", "geo_target": "ca", "difficulty_score": 55, "domain_authority": 93, "monthly_visitors": 40000000, "importance_score": 90, "submission_difficulty": "hard", "estimated_field_count": 28},
    {"name": "BBB Better Business Bureau Canada", "url": "https://www.bbb.org/ca", "submission_url": "https://www.bbb.org/ca/verify-business", "category": "general", "geo_target": "ca", "difficulty_score": 70, "domain_authority": 92, "monthly_visitors": 15000000, "importance_score": 90, "is_premium": True, "submission_difficulty": "hard", "estimated_field_count": 35},
    {"name": "Industry Canada", "url": "https://ised-isde.canada.ca", "submission_url": "https://ised-isde.canada.ca/site/ffca/index-eng.html", "category": "government", "geo_target": "ca", "difficulty_score": 50, "domain_authority": 85, "monthly_visitors": 2000000, "importance_score": 80, "submission_difficulty": "hard", "estimated_field_count": 30},
    {"name": "ChamberofCommerce.ca", "url": "https://www.chamberofcommerce.ca", "submission_url": "https://www.chamberofcommerce.ca/add-listing", "category": "local", "geo_target": "ca", "difficulty_score": 25, "domain_authority": 70, "monthly_visitors": 500000, "importance_score": 70, "submission_difficulty": "medium", "estimated_field_count": 18},
    {"name": "Twitter/X Canada", "url": "https://twitter.com", "submission_url": "https://twitter.com/signup", "category": "social", "geo_target": "ca", "difficulty_score": 30, "domain_authority": 97, "monthly_visitors": 150000000, "importance_score": 85, "submission_difficulty": "easy", "estimated_field_count": 12},
    {"name": "Apple Maps Connect", "url": "https://mapsconnect.apple.com", "submission_url": "https://mapsconnect.apple.com", "category": "general", "geo_target": "ca", "difficulty_score": 30, "domain_authority": 95, "monthly_visitors": 20000000, "importance_score": 90, "submission_difficulty": "medium", "estimated_field_count": 15},
    {"name": "Foursquare Canada", "url": "https://foursquare.com", "submission_url": "https://foursquare.com/add-business", "category": "general", "geo_target": "ca", "difficulty_score": 40, "domain_authority": 85, "monthly_visitors": 3000000, "importance_score": 75, "submission_difficulty": "medium", "estimated_field_count": 18},
    {"name": "MapQuest Canada", "url": "https://www.mapquest.com", "submission_url": "https://www.mapquest.com/add-business", "category": "general", "geo_target": "ca", "difficulty_score": 25, "domain_authority": 80, "monthly_visitors": 2000000, "importance_score": 72, "submission_difficulty": "easy", "estimated_field_count": 15},
    {"name": "ShowMeLocal Canada", "url": "https://www.showmelocal.com", "submission_url": "https://www.showmelocal.com/add-business", "category": "general", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 48, "monthly_visitors": 100000, "importance_score": 48, "submission_difficulty": "easy", "estimated_field_count": 12},
    {"name": "Cybo Canada", "url": "https://www.cybo.com", "submission_url": "https://www.cybo.com/add-business", "category": "general", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 50, "monthly_visitors": 150000, "importance_score": 50, "submission_difficulty": "easy", "estimated_field_count": 12},
    {"name": "Opendi Canada", "url": "https://www.opendi.ca", "submission_url": "https://www.opendi.ca/add-business", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 48, "monthly_visitors": 80000, "importance_score": 48, "submission_difficulty": "easy", "estimated_field_count": 10},
]

# ============================================================================
# CA SITES — Tier 2: Medium Priority (75 sites) — Provincial + City + Niche
# ============================================================================
TIER2_CA = [
    # Ontario Directories
    {"name": "Ontario Business Directory", "url": "https://www.ontariobusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 38, "monthly_visitors": 50000, "importance_score": 42},
    {"name": "Toronto Business Directory", "url": "https://www.torontobusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 38, "monthly_visitors": 50000, "importance_score": 42},
    {"name": "Ottawa Business Directory", "url": "https://www.ottawabusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 35, "monthly_visitors": 30000, "importance_score": 40},
    {"name": "Mississauga Business Directory", "url": "https://www.mississaugabusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 35, "monthly_visitors": 25000, "importance_score": 38},
    {"name": "Hamilton Business Directory", "url": "https://www.hamiltonbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 35, "monthly_visitors": 25000, "importance_score": 38},
    {"name": "London Ontario Business Directory", "url": "https://www.londonontariobusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 32, "monthly_visitors": 20000, "importance_score": 35},
    {"name": "Kitchener Business Directory", "url": "https://www.kitchenerbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 32, "monthly_visitors": 20000, "importance_score": 35},
    {"name": "Windsor Ontario Business Directory", "url": "https://www.windsorontariobusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 32, "monthly_visitors": 18000, "importance_score": 35},
    {"name": "Brampton Business Directory", "url": "https://www.bramptonbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 32, "monthly_visitors": 18000, "importance_score": 35},
    {"name": "Vaughan Business Directory", "url": "https://www.vaughanbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 32, "monthly_visitors": 15000, "importance_score": 35},
    # British Columbia Directories
    {"name": "British Columbia Business Directory", "url": "https://www.bcbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 38, "monthly_visitors": 50000, "importance_score": 42},
    {"name": "Vancouver Business Directory", "url": "https://www.vancouverbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 38, "monthly_visitors": 50000, "importance_score": 42},
    {"name": "Surrey BC Business Directory", "url": "https://www.surreybcbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 35, "monthly_visitors": 25000, "importance_score": 38},
    {"name": "Burnaby Business Directory", "url": "https://www.burnabybusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 32, "monthly_visitors": 20000, "importance_score": 35},
    {"name": "Richmond BC Business Directory", "url": "https://www.richmondbcbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 32, "monthly_visitors": 18000, "importance_score": 35},
    {"name": "Victoria BC Business Directory", "url": "https://www.victoriabcbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 32, "monthly_visitors": 20000, "importance_score": 35},
    {"name": "Kelowna Business Directory", "url": "https://www.kelownabusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 30, "monthly_visitors": 15000, "importance_score": 32},
    {"name": "Abbotsford BC Business Directory", "url": "https://www.abbotsfordbcbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 30, "monthly_visitors": 12000, "importance_score": 32},
    # Alberta Directories
    {"name": "Alberta Business Directory", "url": "https://www.albertabusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 38, "monthly_visitors": 50000, "importance_score": 42},
    {"name": "Calgary Business Directory", "url": "https://www.calgarybusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 38, "monthly_visitors": 50000, "importance_score": 42},
    {"name": "Edmonton Business Directory", "url": "https://www.edmontonbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 38, "monthly_visitors": 45000, "importance_score": 42},
    {"name": "Red Deer Business Directory", "url": "https://www.reddeerbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 30, "monthly_visitors": 15000, "importance_score": 32},
    {"name": "Lethbridge Business Directory", "url": "https://www.lethbridgebusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 30, "monthly_visitors": 12000, "importance_score": 32},
    {"name": "Medicine Hat Business Directory", "url": "https://www.medicinehatbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 28, "monthly_visitors": 10000, "importance_score": 30},
    {"name": "St. Albert Business Directory", "url": "https://www.stalbertbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 28, "monthly_visitors": 10000, "importance_score": 30},
    {"name": "Fort McMurray Business Directory", "url": "https://www.fortmcmurraybusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 28, "monthly_visitors": 10000, "importance_score": 30},
    # Quebec Directories
    {"name": "Quebec Business Directory", "url": "https://www.quebecbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 38, "monthly_visitors": 50000, "importance_score": 42},
    {"name": "Montreal Business Directory", "url": "https://www.montrealbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 38, "monthly_visitors": 50000, "importance_score": 42},
    {"name": "Quebec City Business Directory", "url": "https://www.quebeccitybusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 35, "monthly_visitors": 30000, "importance_score": 38},
    {"name": "Laval Business Directory", "url": "https://www.lavalbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 32, "monthly_visitors": 20000, "importance_score": 35},
    {"name": "Gatineau Business Directory", "url": "https://www.gatineaubusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 30, "monthly_visitors": 15000, "importance_score": 32},
    {"name": "Sherbrooke Business Directory", "url": "https://www.sherbrookebusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 28, "monthly_visitors": 12000, "importance_score": 30},
    {"name": "Trois-Rivieres Business Directory", "url": "https://www.troisrivieresbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 28, "monthly_visitors": 10000, "importance_score": 30},
    {"name": "Saguenay Business Directory", "url": "https://www.saguenaybusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 28, "monthly_visitors": 10000, "importance_score": 30},
    # Manitoba & Saskatchewan
    {"name": "Winnipeg Business Directory", "url": "https://www.winnipegbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 35, "monthly_visitors": 30000, "importance_score": 38},
    {"name": "Manitoba Business Directory", "url": "https://www.manitobabusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 32, "monthly_visitors": 20000, "importance_score": 35},
    {"name": "Saskatoon Business Directory", "url": "https://www.saskatoonbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 32, "monthly_visitors": 20000, "importance_score": 35},
    {"name": "Regina Business Directory", "url": "https://www.reginabusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 32, "monthly_visitors": 18000, "importance_score": 35},
    {"name": "Saskatchewan Business Directory", "url": "https://www.saskatchewanbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 30, "monthly_visitors": 15000, "importance_score": 32},
    # Atlantic Canada
    {"name": "Halifax Business Directory", "url": "https://www.halifaxbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 32, "monthly_visitors": 20000, "importance_score": 35},
    {"name": "New Brunswick Business Directory", "url": "https://www.newbrunswickbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 30, "monthly_visitors": 15000, "importance_score": 32},
    {"name": "Nova Scotia Business Directory", "url": "https://www.novascotiabusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 30, "monthly_visitors": 15000, "importance_score": 32},
    {"name": "Prince Edward Island Business Directory", "url": "https://www.peibusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 28, "monthly_visitors": 10000, "importance_score": 30},
    {"name": "St. Johns Business Directory", "url": "https://www.stjohnsbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 30, "monthly_visitors": 12000, "importance_score": 32},
    # Industry Associations
    {"name": "Canadian Chamber of Commerce", "url": "https://chamber.ca", "category": "government", "geo_target": "ca", "difficulty_score": 40, "domain_authority": 78, "monthly_visitors": 800000, "importance_score": 78},
    {"name": "Canadian Medical Association", "url": "https://www.cma.ca", "category": "niche", "geo_target": "ca", "difficulty_score": 50, "domain_authority": 75, "monthly_visitors": 500000, "importance_score": 72},
    {"name": "Canadian Bar Association", "url": "https://www.cba.org", "category": "niche", "geo_target": "ca", "difficulty_score": 45, "domain_authority": 72, "monthly_visitors": 400000, "importance_score": 70},
    {"name": "Canadian Dental Association", "url": "https://www.cda-adc.ca", "category": "niche", "geo_target": "ca", "difficulty_score": 40, "domain_authority": 68, "monthly_visitors": 300000, "importance_score": 65},
    {"name": "Canadian Real Estate Association", "url": "https://www.crea.ca", "category": "niche", "geo_target": "ca", "difficulty_score": 50, "domain_authority": 82, "monthly_visitors": 1000000, "importance_score": 80},
    {"name": "Canadian Restaurant Association", "url": "https://www.cra-arc.ca", "category": "niche", "geo_target": "ca", "difficulty_score": 40, "domain_authority": 68, "monthly_visitors": 300000, "importance_score": 65},
    {"name": "Canadian Federation of Independent Business", "url": "https://www.cfib-fcei.ca", "category": "government", "geo_target": "ca", "difficulty_score": 45, "domain_authority": 75, "monthly_visitors": 600000, "importance_score": 72},
    {"name": "Canadian Manufacturing Association", "url": "https://www.cmf.ca", "category": "niche", "geo_target": "ca", "difficulty_score": 35, "domain_authority": 62, "monthly_visitors": 200000, "importance_score": 60},
    {"name": "Canadian Construction Association", "url": "https://www.cca-acc.com", "category": "niche", "geo_target": "ca", "difficulty_score": 35, "domain_authority": 62, "monthly_visitors": 200000, "importance_score": 60},
    {"name": "Canadian Technology Network", "url": "https://www.cantech.ca", "category": "niche", "geo_target": "ca", "difficulty_score": 30, "domain_authority": 58, "monthly_visitors": 150000, "importance_score": 55},
    # Niche: Automotive
    {"name": "AutoTrader.ca", "url": "https://www.autotrader.ca", "submission_url": "https://www.autotrader.ca/dealer/", "category": "niche", "geo_target": "ca", "difficulty_score": 45, "domain_authority": 88, "monthly_visitors": 12000000, "importance_score": 82, "submission_difficulty": "hard", "estimated_field_count": 25},
    {"name": "Kijiji Canada", "url": "https://www.kijiji.ca", "submission_url": "https://www.kijiji.ca/b-post-ad", "category": "local", "geo_target": "ca", "difficulty_score": 40, "domain_authority": 92, "monthly_visitors": 20000000, "importance_score": 85, "submission_difficulty": "easy", "estimated_field_count": 15},
    {"name": "Canadian Car Dealer", "url": "https://www.canadiancardealer.ca", "category": "niche", "geo_target": "ca", "difficulty_score": 25, "domain_authority": 55, "monthly_visitors": 100000, "importance_score": 52},
    {"name": "Automotive Association Canada", "url": "https://www.caa.ca", "category": "niche", "geo_target": "ca", "difficulty_score": 35, "domain_authority": 68, "monthly_visitors": 300000, "importance_score": 65},
    # Niche: Restaurant
    {"name": "SkipTheDishes", "url": "https://www.skipthedishes.com", "submission_url": "https://www.skipthedishes.com/partner", "category": "niche", "geo_target": "ca", "difficulty_score": 40, "domain_authority": 75, "monthly_visitors": 3000000, "importance_score": 72, "submission_difficulty": "medium", "estimated_field_count": 20},
    {"name": "Uber Eats Canada", "url": "https://www.ubereats.com", "submission_url": "https://www.ubereats.com/ca/restaurant/signup", "category": "niche", "geo_target": "ca", "difficulty_score": 45, "domain_authority": 88, "monthly_visitors": 10000000, "importance_score": 82, "submission_difficulty": "medium", "estimated_field_count": 22},
    {"name": "DoorDash Canada", "url": "https://www.doordash.com", "submission_url": "https://www.doordash.com/merchant/signup", "category": "niche", "geo_target": "ca", "difficulty_score": 45, "domain_authority": 85, "monthly_visitors": 8000000, "importance_score": 80, "submission_difficulty": "medium", "estimated_field_count": 22},
    {"name": "OpenTable Canada", "url": "https://www.opentable.ca", "submission_url": "https://www.opentable.ca/partner", "category": "niche", "geo_target": "ca", "difficulty_score": 50, "domain_authority": 88, "monthly_visitors": 10000000, "importance_score": 82, "submission_difficulty": "hard", "estimated_field_count": 25},
    # Niche: Real Estate
    {"name": "Realtor.ca", "url": "https://www.realtor.ca", "submission_url": "https://www.realtor.ca/realestateagents/", "category": "niche", "geo_target": "ca", "difficulty_score": 50, "domain_authority": 90, "monthly_visitors": 15000000, "importance_score": 88, "is_premium": True, "submission_difficulty": "hard", "estimated_field_count": 25},
    {"name": "Zolo.ca", "url": "https://www.zolo.ca", "category": "niche", "geo_target": "ca", "difficulty_score": 40, "domain_authority": 65, "monthly_visitors": 500000, "importance_score": 62},
    {"name": "HouseSigma", "url": "https://housesigma.com", "category": "niche", "geo_target": "ca", "difficulty_score": 35, "domain_authority": 60, "monthly_visitors": 400000, "importance_score": 58},
    {"name": "Point2Homes Canada", "url": "https://www.point2homes.com/ca/", "category": "niche", "geo_target": "ca", "difficulty_score": 30, "domain_authority": 55, "monthly_visitors": 300000, "importance_score": 52},
    # Niche: Medical
    {"name": "RateMDs Canada", "url": "https://www.ratemds.com", "category": "niche", "geo_target": "ca", "difficulty_score": 30, "domain_authority": 65, "monthly_visitors": 1500000, "importance_score": 65},
    {"name": "HealthGrades Canada", "url": "https://www.healthgrades.com", "category": "niche", "geo_target": "ca", "difficulty_score": 40, "domain_authority": 80, "monthly_visitors": 5000000, "importance_score": 78},
    {"name": "Canadian Medical Directory", "url": "https://www.cmd-lcc.ca", "category": "niche", "geo_target": "ca", "difficulty_score": 35, "domain_authority": 55, "monthly_visitors": 100000, "importance_score": 52},
    {"name": "Maple Health", "url": "https://www.getmaple.ca", "category": "niche", "geo_target": "ca", "difficulty_score": 30, "domain_authority": 50, "monthly_visitors": 80000, "importance_score": 48},
    # Niche: Legal
    {"name": "CanLII", "url": "https://www.canlii.org", "category": "niche", "geo_target": "ca", "difficulty_score": 45, "domain_authority": 72, "monthly_visitors": 400000, "importance_score": 70},
    {"name": "FindLaw Canada", "url": "https://www.findlaw.ca", "category": "niche", "geo_target": "ca", "difficulty_score": 40, "domain_authority": 68, "monthly_visitors": 300000, "importance_score": 65},
    {"name": "Canadian Lawyer Magazine", "url": "https://www.canadianlawyermag.com", "category": "niche", "geo_target": "ca", "difficulty_score": 35, "domain_authority": 62, "monthly_visitors": 200000, "importance_score": 58},
    {"name": "Lawyer Daily Canada", "url": "https://www.lawyered.ca", "category": "niche", "geo_target": "ca", "difficulty_score": 30, "domain_authority": 55, "monthly_visitors": 120000, "importance_score": 52},
    # Niche: Technology
    {"name": "BlogTO", "url": "https://blogto.com", "category": "social", "geo_target": "ca", "difficulty_score": 25, "domain_authority": 78, "monthly_visitors": 2000000, "importance_score": 72},
    {"name": "TechVibes", "url": "https://techvibes.com", "category": "social", "geo_target": "ca", "difficulty_score": 20, "domain_authority": 62, "monthly_visitors": 200000, "importance_score": 55},
    {"name": "Canadian Startup News", "url": "https://canadianstartupnews.com", "category": "social", "geo_target": "ca", "difficulty_score": 15, "domain_authority": 48, "monthly_visitors": 50000, "importance_score": 42},
    {"name": "Betakit", "url": "https://betakit.com", "category": "social", "geo_target": "ca", "difficulty_score": 15, "domain_authority": 52, "monthly_visitors": 80000, "importance_score": 45},
]

# ============================================================================
# CA SITES — Tier 3: Lower Priority (100 sites)
# ============================================================================
TIER3_CA = [
    # Canadian Article Directories
    {"name": "Canadian Content", "url": "https://canadiancontent.net", "category": "social", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 45, "monthly_visitors": 50000, "importance_score": 40, "submission_difficulty": "easy", "estimated_field_count": 8},
    {"name": "Canoe.com", "url": "https://www.canoe.com", "category": "social", "geo_target": "ca", "difficulty_score": 15, "domain_authority": 72, "monthly_visitors": 500000, "importance_score": 55, "submission_difficulty": "easy", "estimated_field_count": 8},
    {"name": "HuffPost Canada", "url": "https://www.huffpost.com/canada", "category": "social", "geo_target": "ca", "difficulty_score": 25, "domain_authority": 92, "monthly_visitors": 5000000, "importance_score": 75, "submission_difficulty": "medium", "estimated_field_count": 10},
    {"name": "Daily Hive", "url": "https://dailyhive.com", "category": "social", "geo_target": "ca", "difficulty_score": 20, "domain_authority": 72, "monthly_visitors": 1000000, "importance_score": 65, "submission_difficulty": "easy", "estimated_field_count": 8},
    {"name": "Narcity", "url": "https://www.narcity.com", "category": "social", "geo_target": "ca", "difficulty_score": 15, "domain_authority": 65, "monthly_visitors": 800000, "importance_score": 58, "submission_difficulty": "easy", "estimated_field_count": 8},
    {"name": "MobileSyrup", "url": "https://mobilesyrup.com", "category": "social", "geo_target": "ca", "difficulty_score": 15, "domain_authority": 68, "monthly_visitors": 600000, "importance_score": 55, "submission_difficulty": "easy", "estimated_field_count": 8},
    # Social Bookmarking
    {"name": "Reddit Canada", "url": "https://www.reddit.com/r/canada", "category": "social", "geo_target": "ca", "difficulty_score": 20, "domain_authority": 99, "monthly_visitors": 200000000, "importance_score": 70, "submission_difficulty": "easy", "estimated_field_count": 5},
    {"name": "Digg Canada", "url": "https://digg.com", "category": "social", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 80, "monthly_visitors": 5000000, "importance_score": 55, "submission_difficulty": "easy", "estimated_field_count": 5},
    {"name": "Scoop.it Canada", "url": "https://www.scoop.it", "category": "social", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 72, "monthly_visitors": 2000000, "importance_score": 50, "submission_difficulty": "easy", "estimated_field_count": 5},
    # Canadian Profile Links
    {"name": "About.me Canada", "url": "https://about.me", "category": "social", "geo_target": "ca", "difficulty_score": 5, "domain_authority": 75, "monthly_visitors": 3000000, "importance_score": 52, "submission_difficulty": "easy", "estimated_field_count": 8},
    {"name": "Gravatar Canada", "url": "https://gravatar.com", "category": "social", "geo_target": "ca", "difficulty_score": 5, "domain_authority": 80, "monthly_visitors": 5000000, "importance_score": 55, "submission_difficulty": "easy", "estimated_field_count": 5},
    {"name": "Medium Canada", "url": "https://medium.com", "category": "social", "geo_target": "ca", "difficulty_score": 15, "domain_authority": 95, "monthly_visitors": 50000000, "importance_score": 75, "submission_difficulty": "easy", "estimated_field_count": 8},
    {"name": "WordPress.com", "url": "https://wordpress.com", "category": "social", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 92, "monthly_visitors": 30000000, "importance_score": 72, "submission_difficulty": "easy", "estimated_field_count": 8},
    {"name": "Blogger Canada", "url": "https://www.blogger.com", "category": "social", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 92, "monthly_visitors": 20000000, "importance_score": 70, "submission_difficulty": "easy", "estimated_field_count": 6},
    {"name": "Tumblr Canada", "url": "https://www.tumblr.com", "category": "social", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 90, "monthly_visitors": 15000000, "importance_score": 68, "submission_difficulty": "easy", "estimated_field_count": 6},
    {"name": "Weebly Canada", "url": "https://www.weebly.com", "category": "social", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 85, "monthly_visitors": 10000000, "importance_score": 65, "submission_difficulty": "easy", "estimated_field_count": 8},
    {"name": "Substack Canada", "url": "https://substack.com", "category": "social", "geo_target": "ca", "difficulty_score": 15, "domain_authority": 82, "monthly_visitors": 5000000, "importance_score": 65, "submission_difficulty": "easy", "estimated_field_count": 6},
    {"name": "DEV Community Canada", "url": "https://dev.to", "category": "social", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 75, "monthly_visitors": 2000000, "importance_score": 60, "submission_difficulty": "easy", "estimated_field_count": 6},
    {"name": "Hashnode Canada", "url": "https://hashnode.com", "category": "social", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 72, "monthly_visitors": 1500000, "importance_score": 58, "submission_difficulty": "easy", "estimated_field_count": 6},
    # Canadian Directories - Smaller
    {"name": "Canpages", "url": "https://www.canpages.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 48, "monthly_visitors": 80000, "importance_score": 45},
    {"name": "YellowPagesGroup.ca", "url": "https://www.yellowpagesgroup.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 45, "monthly_visitors": 60000, "importance_score": 42},
    {"name": "LocalSearch.ca", "url": "https://www.localsearch.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 42, "monthly_visitors": 50000, "importance_score": 40},
    {"name": "BusinessDirectory.ca", "url": "https://www.businessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 40, "monthly_visitors": 40000, "importance_score": 38},
    {"name": "CanadaDirectory.ca", "url": "https://www.canadadirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 38, "monthly_visitors": 35000, "importance_score": 35},
    {"name": "CanadianBusinessDirectory.ca", "url": "https://www.canadianbusinessdirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 38, "monthly_visitors": 35000, "importance_score": 35},
    {"name": "MyBusiness.ca", "url": "https://www.mybusiness.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 35, "monthly_visitors": 25000, "importance_score": 32},
    {"name": "Fyple Canada", "url": "https://www.fyple.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 35, "monthly_visitors": 25000, "importance_score": 32},
    {"name": "iGlobal Canada", "url": "https://iglobal.co/ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 35, "monthly_visitors": 20000, "importance_score": 32},
    {"name": "Yalwa Canada", "url": "https://www.yalwa.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 32, "monthly_visitors": 18000, "importance_score": 30},
    {"name": "Tupalo Canada", "url": "https://www.tupalo.com/ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 32, "monthly_visitors": 15000, "importance_score": 30},
    {"name": "nGraph Canada", "url": "https://www.ngraph.com", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 32, "monthly_visitors": 15000, "importance_score": 30},
    # Press Release Sites
    {"name": "CNW Group", "url": "https://www.newswire.ca", "category": "social", "geo_target": "ca", "difficulty_score": 25, "domain_authority": 72, "monthly_visitors": 500000, "importance_score": 62, "submission_difficulty": "medium", "estimated_field_count": 15},
    {"name": "Marketwired", "url": "https://www.marketwired.com", "category": "social", "geo_target": "ca", "difficulty_score": 20, "domain_authority": 68, "monthly_visitors": 400000, "importance_score": 58, "submission_difficulty": "easy", "estimated_field_count": 12},
    {"name": "PRLog Canada", "url": "https://www.prlog.org", "category": "social", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 65, "monthly_visitors": 500000, "importance_score": 45, "submission_difficulty": "easy", "estimated_field_count": 10},
    {"name": "OpenPR Canada", "url": "https://www.openpr.com", "category": "social", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 62, "monthly_visitors": 400000, "importance_score": 42, "submission_difficulty": "easy", "estimated_field_count": 10},
    # Canadian Social Platforms
    {"name": "LinkedIn Canada", "url": "https://www.linkedin.com", "category": "social", "geo_target": "ca", "difficulty_score": 35, "domain_authority": 98, "monthly_visitors": 80000000, "importance_score": 90, "submission_difficulty": "easy", "estimated_field_count": 18},
    {"name": "Instagram Canada", "url": "https://www.instagram.com", "category": "social", "geo_target": "ca", "difficulty_score": 30, "domain_authority": 96, "monthly_visitors": 100000000, "importance_score": 85, "submission_difficulty": "easy", "estimated_field_count": 10},
    {"name": "YouTube Canada", "url": "https://www.youtube.com", "category": "social", "geo_target": "ca", "difficulty_score": 25, "domain_authority": 99, "monthly_visitors": 200000000, "importance_score": 80, "submission_difficulty": "easy", "estimated_field_count": 8},
    {"name": "Pinterest Canada", "url": "https://business.pinterest.com", "category": "social", "geo_target": "ca", "difficulty_score": 25, "domain_authority": 94, "monthly_visitors": 50000000, "importance_score": 75, "submission_difficulty": "easy", "estimated_field_count": 12},
    # Canadian Article Sites
    {"name": "Canadian Living", "url": "https://www.canadianliving.com", "category": "social", "geo_target": "ca", "difficulty_score": 20, "domain_authority": 72, "monthly_visitors": 1000000, "importance_score": 62, "submission_difficulty": "easy", "estimated_field_count": 8},
    {"name": "Today's Parent", "url": "https://www.todayisparent.com", "category": "social", "geo_target": "ca", "difficulty_score": 15, "domain_authority": 62, "monthly_visitors": 500000, "importance_score": 52, "submission_difficulty": "easy", "estimated_field_count": 8},
    {"name": "MoneySense", "url": "https://www.moneysense.ca", "category": "social", "geo_target": "ca", "difficulty_score": 20, "domain_authority": 68, "monthly_visitors": 800000, "importance_score": 58, "submission_difficulty": "easy", "estimated_field_count": 8},
    {"name": "Canadian Business", "url": "https://www.canadianbusiness.com", "category": "social", "geo_target": "ca", "difficulty_score": 20, "domain_authority": 70, "monthly_visitors": 600000, "importance_score": 58, "submission_difficulty": "easy", "estimated_field_count": 8},
    # Web 2.0 Platforms
    {"name": "Wix Canada", "url": "https://www.wix.com", "category": "social", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 92, "monthly_visitors": 30000000, "importance_score": 70, "submission_difficulty": "easy", "estimated_field_count": 8},
    {"name": "Squarespace Canada", "url": "https://www.squarespace.com", "category": "social", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 90, "monthly_visitors": 20000000, "importance_score": 68, "submission_difficulty": "easy", "estimated_field_count": 8},
    {"name": "Jimdo Canada", "url": "https://www.jimdo.com", "category": "social", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 82, "monthly_visitors": 10000000, "importance_score": 62, "submission_difficulty": "easy", "estimated_field_count": 8},
    {"name": "Site123", "url": "https://www.site123.com", "category": "social", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 75, "monthly_visitors": 5000000, "importance_score": 55, "submission_difficulty": "easy", "estimated_field_count": 8},
    # Canadian Niche Directories
    {"name": "Canada Business Network", "url": "https://www.canada.ca/en/business-network.html", "category": "government", "geo_target": "ca", "difficulty_score": 35, "domain_authority": 82, "monthly_visitors": 500000, "importance_score": 72},
    {"name": "CanadaVisa Business Directory", "url": "https://www.canadavisa.com", "category": "local", "geo_target": "ca", "difficulty_score": 30, "domain_authority": 72, "monthly_visitors": 400000, "importance_score": 62},
    {"name": "Canadian Small Business Directory", "url": "https://www.canadiansmallbusiness.com", "category": "local", "geo_target": "ca", "difficulty_score": 15, "domain_authority": 48, "monthly_visitors": 80000, "importance_score": 42},
    {"name": "Startup Canada", "url": "https://startupcanada.ca", "category": "social", "geo_target": "ca", "difficulty_score": 20, "domain_authority": 58, "monthly_visitors": 150000, "importance_score": 52},
    {"name": "Canada Trade Directory", "url": "https://www.canadatradedirectory.com", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 42, "monthly_visitors": 50000, "importance_score": 40},
    # Profile and Listing Sites
    {"name": "Crunchbase Canada", "url": "https://www.crunchbase.com", "category": "social", "geo_target": "ca", "difficulty_score": 20, "domain_authority": 82, "monthly_visitors": 2000000, "importance_score": 65, "submission_difficulty": "easy", "estimated_field_count": 10},
    {"name": "AngelList Canada", "url": "https://angel.co", "category": "social", "geo_target": "ca", "difficulty_score": 15, "domain_authority": 85, "monthly_visitors": 3000000, "importance_score": 68, "submission_difficulty": "easy", "estimated_field_count": 10},
    {"name": "Clutch.co Canada", "url": "https://clutch.co", "category": "local", "geo_target": "ca", "difficulty_score": 20, "domain_authority": 72, "monthly_visitors": 800000, "importance_score": 60, "submission_difficulty": "easy", "estimated_field_count": 12},
    {"name": "UpCity Canada", "url": "https://www.upcity.com", "category": "local", "geo_target": "ca", "difficulty_score": 15, "domain_authority": 65, "monthly_visitors": 400000, "importance_score": 55, "submission_difficulty": "easy", "estimated_field_count": 12},
    {"name": "G2 Canada", "url": "https://www.g2.com", "category": "local", "geo_target": "ca", "difficulty_score": 20, "domain_authority": 82, "monthly_visitors": 2000000, "importance_score": 68, "submission_difficulty": "easy", "estimated_field_count": 12},
    # More Local Directories
    {"name": "LocalPages Canada", "url": "https://www.localpages.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 38, "monthly_visitors": 30000, "importance_score": 35},
    {"name": "CityDirectory.ca", "url": "https://www.citydirectory.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 35, "monthly_visitors": 25000, "importance_score": 32},
    {"name": "CanadaOnlineDirectory", "url": "https://www.canadaonlinedirectory.com", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 35, "monthly_visitors": 20000, "importance_score": 32},
    {"name": "SmartFind Canada", "url": "https://www.smartfind.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 32, "monthly_visitors": 15000, "importance_score": 30},
    {"name": "LocalBusiness.ca", "url": "https://www.localbusiness.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 32, "monthly_visitors": 15000, "importance_score": 30},
    {"name": "CanadaSearch", "url": "https://www.canadasearch.com", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 30, "monthly_visitors": 12000, "importance_score": 28},
    {"name": "FindLocal.ca", "url": "https://www.findlocal.ca", "category": "local", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 30, "monthly_visitors": 12000, "importance_score": 28},
    {"name": "CanadaWebDirectory", "url": "https://www.canadawebdirectory.com", "category": "general", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 28, "monthly_visitors": 10000, "importance_score": 25},
    {"name": "CaDir.com", "url": "https://www.cadir.com", "category": "general", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 28, "monthly_visitors": 10000, "importance_score": 25},
    {"name": "Canada Directory Listing", "url": "https://www.canadadirectorylisting.com", "category": "general", "geo_target": "ca", "difficulty_score": 10, "domain_authority": 25, "monthly_visitors": 8000, "importance_score": 22},
    {"name": "Free Canada Directory", "url": "https://www.freecanadadirectory.com", "category": "general", "geo_target": "ca", "difficulty_score": 5, "domain_authority": 25, "monthly_visitors": 8000, "importance_score": 22},
    {"name": "CA Directory", "url": "https://www.cadirectory.ca", "category": "general", "geo_target": "ca", "difficulty_score": 5, "domain_authority": 22, "monthly_visitors": 5000, "importance_score": 20},
    {"name": "Canada Business Links", "url": "https://www.canadabusinesslinks.com", "category": "general", "geo_target": "ca", "difficulty_score": 5, "domain_authority": 22, "monthly_visitors": 5000, "importance_score": 20},
]


def main():
    """Seed all Canadian sites."""
    all_sites = TIER1_CA + TIER2_CA + TIER3_CA
    print(f"Total CA sites to seed: {len(all_sites)}")
    inserted = seed_sites(all_sites, region="ca")
    print(f"Done. Inserted {inserted} CA sites.")


if __name__ == "__main__":
    main()
