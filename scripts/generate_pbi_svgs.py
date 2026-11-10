#!/usr/bin/env python3
"""
Generates 3 institutional-grade 16:9 vector SVG dashboard pages for Power BI:
  1. 01_executive_portfolio_risk.svg
  2. 02_vintage_delinquency_chargeoff.svg
  3. 03_dq_governance_vendor_sla.svg
"""

import re
from pathlib import Path

OUT_DIR = Path("reports/powerbi")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def xml_escape(text: str) -> str:
    return re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;)', '&amp;', text)

COMMON_DEFS = """
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0B132B"/>
      <stop offset="100%" stop-color="#1C2541"/>
    </linearGradient>
    <linearGradient id="cardGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1E293B"/>
      <stop offset="100%" stop-color="#182234"/>
    </linearGradient>
    <linearGradient id="blueBarGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#38BDF8"/>
      <stop offset="100%" stop-color="#0284C7"/>
    </linearGradient>
    <linearGradient id="navyBarGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#60A5FA"/>
      <stop offset="100%" stop-color="#2563EB"/>
    </linearGradient>
    <linearGradient id="amberGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#FBBF24"/>
      <stop offset="100%" stop-color="#D97706"/>
    </linearGradient>
    <linearGradient id="redGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#F87171"/>
      <stop offset="100%" stop-color="#DC2626"/>
    </linearGradient>
    <linearGradient id="greenGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#34D399"/>
      <stop offset="100%" stop-color="#059669"/>
    </linearGradient>
    <filter id="cardShadow" x="-5%" y="-5%" width="110%" height="115%" filterUnits="userSpaceOnUse">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000000" flood-opacity="0.35"/>
    </filter>
  </defs>
"""

def generate_header(active_tab: int, title: str, subtitle: str) -> str:
    tabs = [
        ("1. Executive Risk & Exposure", 0),
        ("2. Vintage Delinquency & Loss", 1),
        ("3. DQ & Vendor SLA Governance", 2)
    ]
    tab_elements = []
    x_offset = 32
    for label, idx in tabs:
        is_active = (idx == active_tab)
        bg = "#2563EB" if is_active else "#1E293B"
        border = "#60A5FA" if is_active else "#334155"
        txt_col = "#FFFFFF" if is_active else "#94A3B8"
        font_wt = "bold" if is_active else "normal"
        width = 220
        tab_elements.append(f"""
          <g transform="translate({x_offset}, 58)">
            <rect width="{width}" height="32" rx="6" fill="{bg}" stroke="{border}" stroke-width="1"/>
            <text x="{width//2}" y="21" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif" font-size="12" font-weight="{font_wt}" fill="{txt_col}" text-anchor="middle">{label}</text>
          </g>
        """)
        x_offset += width + 12

    return f"""
    <!-- Power BI App Header -->
    <rect x="0" y="0" width="1600" height="98" fill="#0F172A" stroke="#1E293B" stroke-width="1"/>
    
    <!-- Power BI Brand & Title -->
    <g transform="translate(32, 18)">
      <!-- Power BI Icon glyph -->
      <rect x="0" y="2" width="22" height="26" rx="3" fill="#F2C811"/>
      <rect x="5" y="14" width="3" height="11" fill="#1E293B"/>
      <rect x="10" y="9" width="3" height="16" fill="#1E293B"/>
      <rect x="15" y="5" width="3" height="20" fill="#1E293B"/>
      
      <text x="32" y="18" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif" font-size="18" font-weight="700" fill="#F8FAFC">LoanWatch BI <tspan font-weight="400" fill="#94A3B8">| {title.replace('&amp;', '&amp;amp;').replace('&', '&amp;')}</tspan></text>
      <text x="32" y="32" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif" font-size="11" fill="#64748B">{subtitle.replace('&amp;', '&amp;amp;').replace('&', '&amp;')}</text>
    </g>
    
    <!-- Page Navigation Tabs -->
    {''.join(tab_elements)}
    
    <!-- Slicers / Context Pills -->
    <g transform="translate(1120, 58)">
      <rect x="0" y="0" width="130" height="32" rx="6" fill="#1E293B" stroke="#334155" stroke-width="1"/>
      <text x="14" y="20" font-family="sans-serif" font-size="11" fill="#94A3B8">As of:</text>
      <text x="56" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#38BDF8">2026-10-09</text>
      
      <rect x="140" y="0" width="150" height="32" rx="6" fill="#1E293B" stroke="#334155" stroke-width="1"/>
      <text x="154" y="20" font-family="sans-serif" font-size="11" fill="#94A3B8">Servicer:</text>
      <text x="210" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">FirstMark</text>
      
      <rect x="300" y="0" width="148" height="32" rx="6" fill="#1E293B" stroke="#059669" stroke-width="1"/>
      <circle cx="314" cy="16" r="4" fill="#10B981"/>
      <text x="326" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#34D399">DirectQuery Live</text>
    </g>
    """


# ==============================================================================
# PAGE 1: Executive Portfolio Risk & Exposure
# ==============================================================================
def create_page_1() -> str:
    header = generate_header(0, "Executive Credit Risk & Portfolio Exposure", "Citi Retail Lending MIS • 2,256,390 Clean Loans • PostgreSQL 16 DirectQuery")
    
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" width="1600" height="900">
  {COMMON_DEFS}
  <!-- Main Canvas Background -->
  <rect width="1600" height="900" fill="url(#bgGrad)"/>
  
  {header}
  
  <!-- ROW 1: 4 KPI CARDS -->
  <!-- Card 1: Total Funded Principal -->
  <g transform="translate(32, 110)" filter="url(#cardShadow)">
    <rect width="365" height="110" rx="10" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="24" y="32" font-family="sans-serif" font-size="12" font-weight="600" fill="#94A3B8" letter-spacing="0.5">TOTAL FUNDED EXPOSURE</text>
    <text x="24" y="74" font-family="sans-serif" font-size="34" font-weight="800" fill="#F8FAFC">$33.92B</text>
    <rect x="230" y="52" width="110" height="24" rx="12" fill="#1E3A8A"/>
    <text x="285" y="68" font-family="sans-serif" font-size="11" font-weight="700" fill="#60A5FA" text-anchor="middle">2,256,390 Loans</text>
    <text x="24" y="96" font-family="sans-serif" font-size="11" fill="#64748B">Avg Loan Size: $15,032 • 36/60M Tenor</text>
  </g>

  <!-- Card 2: Current Active UPB -->
  <g transform="translate(422, 110)" filter="url(#cardShadow)">
    <rect width="365" height="110" rx="10" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="24" y="32" font-family="sans-serif" font-size="12" font-weight="600" fill="#94A3B8" letter-spacing="0.5">CURRENT ACTIVE UPB</text>
    <text x="24" y="74" font-family="sans-serif" font-size="34" font-weight="800" fill="#38BDF8">$9.46B</text>
    <rect x="235" y="52" width="105" height="24" rx="12" fill="#0C4A6E"/>
    <text x="287" y="68" font-family="sans-serif" font-size="11" font-weight="700" fill="#38BDF8" text-anchor="middle">27.9% of Funded</text>
    <text x="24" y="96" font-family="sans-serif" font-size="11" fill="#64748B">Amortized: $24.46B received principal</text>
  </g>

  <!-- Card 3: Weighted Average Coupon (WAC) -->
  <g transform="translate(812, 110)" filter="url(#cardShadow)">
    <rect width="365" height="110" rx="10" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="24" y="32" font-family="sans-serif" font-size="12" font-weight="600" fill="#94A3B8" letter-spacing="0.5">WEIGHTED AVERAGE COUPON (WAC)</text>
    <text x="24" y="74" font-family="sans-serif" font-size="34" font-weight="800" fill="#FBBF24">13.38%</text>
    <rect x="235" y="52" width="105" height="24" rx="12" fill="#451A03"/>
    <text x="287" y="68" font-family="sans-serif" font-size="11" font-weight="700" fill="#F59E0B" text-anchor="middle">Avg FICO: 696</text>
    <text x="24" y="96" font-family="sans-serif" font-size="11" fill="#64748B">Range: 7.07% (Grade A) to 28.11% (Grade G)</text>
  </g>

  <!-- Card 4: 30+ DPD & Severe Delinquency -->
  <g transform="translate(1202, 110)" filter="url(#cardShadow)">
    <rect width="365" height="110" rx="10" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="24" y="32" font-family="sans-serif" font-size="12" font-weight="600" fill="#94A3B8" letter-spacing="0.5">30+ DPD / SEVERE PROXY RATE</text>
    <text x="24" y="74" font-family="sans-serif" font-size="34" font-weight="800" fill="#F87171">0.95% <tspan font-size="18" font-weight="600" fill="#94A3B8">/ 11.93%</tspan></text>
    <rect x="250" y="52" width="90" height="24" rx="12" fill="#450A0A"/>
    <text x="295" y="68" font-family="sans-serif" font-size="11" font-weight="700" fill="#EF4444" text-anchor="middle">MoM -1.8 bps</text>
    <text x="24" y="96" font-family="sans-serif" font-size="11" fill="#64748B">Severe Proxy: Default (0.1%) + Charged Off (11.8%)</text>
  </g>

  <!-- ROW 2: VISUAL 1 & VISUAL 2 -->
  <!-- Visual 1: Funded Exposure & Delinquency by Grade (Combo Chart) -->
  <g transform="translate(32, 235)" filter="url(#cardShadow)">
    <rect width="940" height="340" rx="10" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="24" y="28" font-family="sans-serif" font-size="14" font-weight="700" fill="#F8FAFC">Funded Principal ($B) and Delinquency / Default Rates (%) by Credit Grade</text>
    <text x="24" y="44" font-family="sans-serif" font-size="11" fill="#64748B">Columns: Funded Exposure ($B) • Red Line: Severe Delinquency Proxy (%) • Amber Dashed: 30+ DPD Rate (%)</text>
    
    <!-- Legend -->
    <g transform="translate(580, 20)">
      <rect x="0" y="4" width="12" height="12" fill="#2563EB" rx="2"/>
      <text x="18" y="14" font-family="sans-serif" font-size="10" fill="#94A3B8">Funded ($B)</text>
      <line x1="90" y1="10" x2="110" y2="10" stroke="#EF4444" stroke-width="2.5"/>
      <circle cx="100" cy="10" r="3.5" fill="#EF4444"/>
      <text x="116" y="14" font-family="sans-serif" font-size="10" fill="#94A3B8">Severe Delinq (%)</text>
      <line x1="220" y1="10" x2="240" y2="10" stroke="#F59E0B" stroke-width="2" stroke-dasharray="3,3"/>
      <text x="246" y="14" font-family="sans-serif" font-size="10" fill="#94A3B8">30+ DPD (%)</text>
    </g>

    <!-- Gridlines & Y-Axis Left ($B) -->
    <line x1="60" y1="70" x2="880" y2="70" stroke="#334155" stroke-dasharray="2,2"/>
    <text x="50" y="74" font-family="sans-serif" font-size="10" fill="#64748B" text-anchor="end">$10B</text>
    <line x1="60" y1="130" x2="880" y2="130" stroke="#334155" stroke-dasharray="2,2"/>
    <text x="50" y="134" font-family="sans-serif" font-size="10" fill="#64748B" text-anchor="end">$7.5B</text>
    <line x1="60" y1="190" x2="880" y2="190" stroke="#334155" stroke-dasharray="2,2"/>
    <text x="50" y="194" font-family="sans-serif" font-size="10" fill="#64748B" text-anchor="end">$5.0B</text>
    <line x1="60" y1="250" x2="880" y2="250" stroke="#334155" stroke-dasharray="2,2"/>
    <text x="50" y="254" font-family="sans-serif" font-size="10" fill="#64748B" text-anchor="end">$2.5B</text>
    <line x1="60" y1="300" x2="880" y2="300" stroke="#475569" stroke-width="1.5"/>
    <text x="50" y="304" font-family="sans-serif" font-size="10" fill="#64748B" text-anchor="end">$0</text>

    <!-- Right Axis (Delinquency %) -->
    <text x="890" y="74" font-family="sans-serif" font-size="10" fill="#EF4444">40%</text>
    <text x="890" y="130" font-family="sans-serif" font-size="10" fill="#EF4444">30%</text>
    <text x="890" y="190" font-family="sans-serif" font-size="10" fill="#EF4444">20%</text>
    <text x="890" y="250" font-family="sans-serif" font-size="10" fill="#EF4444">10%</text>
    <text x="890" y="304" font-family="sans-serif" font-size="10" fill="#EF4444">0%</text>

    <!-- Bars for Grades A through G -->
    <!-- Max height: 230px = $10B (23px per $1B). Grades: A($6.31B)=145px, B($9.38B)=215px, C($9.75B)=224px, D($5.08B)=117px, E($2.36B)=54px, F($0.80B)=18px, G($0.25B)=6px -->
    <!-- X Centers: A=120, B=240, C=360, D=480, E=600, F=720, G=840 -->
    <g>
      <!-- Grade A -->
      <rect x="95" y="155" width="50" height="145" fill="url(#navyBarGrad)" rx="3"/>
      <text x="120" y="145" font-family="sans-serif" font-size="10" font-weight="bold" fill="#93C5FD" text-anchor="middle">$6.31B</text>
      <text x="120" y="318" font-family="sans-serif" font-size="12" font-weight="bold" fill="#F8FAFC" text-anchor="middle">Grade A</text>
      
      <!-- Grade B -->
      <rect x="215" y="85" width="50" height="215" fill="url(#navyBarGrad)" rx="3"/>
      <text x="240" y="75" font-family="sans-serif" font-size="10" font-weight="bold" fill="#93C5FD" text-anchor="middle">$9.38B</text>
      <text x="240" y="318" font-family="sans-serif" font-size="12" font-weight="bold" fill="#F8FAFC" text-anchor="middle">Grade B</text>

      <!-- Grade C -->
      <rect x="335" y="76" width="50" height="224" fill="url(#navyBarGrad)" rx="3"/>
      <text x="360" y="66" font-family="sans-serif" font-size="10" font-weight="bold" fill="#93C5FD" text-anchor="middle">$9.75B</text>
      <text x="360" y="318" font-family="sans-serif" font-size="12" font-weight="bold" fill="#F8FAFC" text-anchor="middle">Grade C</text>

      <!-- Grade D -->
      <rect x="455" y="183" width="50" height="117" fill="url(#navyBarGrad)" rx="3"/>
      <text x="480" y="173" font-family="sans-serif" font-size="10" font-weight="bold" fill="#93C5FD" text-anchor="middle">$5.08B</text>
      <text x="480" y="318" font-family="sans-serif" font-size="12" font-weight="bold" fill="#F8FAFC" text-anchor="middle">Grade D</text>

      <!-- Grade E -->
      <rect x="575" y="246" width="50" height="54" fill="url(#navyBarGrad)" rx="3"/>
      <text x="600" y="238" font-family="sans-serif" font-size="10" font-weight="bold" fill="#93C5FD" text-anchor="middle">$2.36B</text>
      <text x="600" y="318" font-family="sans-serif" font-size="12" font-weight="bold" fill="#F8FAFC" text-anchor="middle">Grade E</text>

      <!-- Grade F -->
      <rect x="695" y="282" width="50" height="18" fill="url(#navyBarGrad)" rx="3"/>
      <text x="720" y="274" font-family="sans-serif" font-size="10" font-weight="bold" fill="#93C5FD" text-anchor="middle">$0.80B</text>
      <text x="720" y="318" font-family="sans-serif" font-size="12" font-weight="bold" fill="#F8FAFC" text-anchor="middle">Grade F</text>

      <!-- Grade G -->
      <rect x="815" y="294" width="50" height="6" fill="url(#navyBarGrad)" rx="3"/>
      <text x="840" y="286" font-family="sans-serif" font-size="10" font-weight="bold" fill="#93C5FD" text-anchor="middle">$0.25B</text>
      <text x="840" y="318" font-family="sans-serif" font-size="12" font-weight="bold" fill="#F8FAFC" text-anchor="middle">Grade G</text>
    </g>

    <!-- Severe Delinquency Line (Red): A=3.29%(y=281), B=7.95%(y=254), C=13.21%(y=224), D=18.91%(y=191), E=26.73%(y=146), F=34.92%(y=99), G=38.14%(y=81) -->
    <polyline points="120,281 240,254 360,224 480,191 600,146 720,99 840,81" fill="none" stroke="#EF4444" stroke-width="3"/>
    <g fill="#EF4444" stroke="#0F172A" stroke-width="2">
      <circle cx="120" cy="281" r="5"/>
      <circle cx="240" cy="254" r="5"/>
      <circle cx="360" cy="224" r="5"/>
      <circle cx="480" cy="191" r="5"/>
      <circle cx="600" cy="146" r="5"/>
      <circle cx="720" cy="99" r="5"/>
      <circle cx="840" cy="81" r="5"/>
    </g>
    <text x="120" y="271" font-family="sans-serif" font-size="10" font-weight="bold" fill="#FCA5A5" text-anchor="middle">3.3%</text>
    <text x="240" y="244" font-family="sans-serif" font-size="10" font-weight="bold" fill="#FCA5A5" text-anchor="middle">7.9%</text>
    <text x="360" y="214" font-family="sans-serif" font-size="10" font-weight="bold" fill="#FCA5A5" text-anchor="middle">13.2%</text>
    <text x="480" y="181" font-family="sans-serif" font-size="10" font-weight="bold" fill="#FCA5A5" text-anchor="middle">18.9%</text>
    <text x="600" y="136" font-family="sans-serif" font-size="10" font-weight="bold" fill="#FCA5A5" text-anchor="middle">26.7%</text>
    <text x="720" y="89" font-family="sans-serif" font-size="10" font-weight="bold" fill="#FCA5A5" text-anchor="middle">34.9%</text>
    <text x="840" y="71" font-family="sans-serif" font-size="10" font-weight="bold" fill="#FCA5A5" text-anchor="middle">38.1%</text>

    <!-- 30+ DPD Dashed Line (Amber): A=0.31%, B=0.72%, C=1.16%, D=1.47%, E=1.59%, F=1.53%, G=1.94% -->
    <polyline points="120,298 240,296 360,293 480,291 600,290 720,291 840,288" fill="none" stroke="#F59E0B" stroke-width="2.5" stroke-dasharray="4,3"/>
  </g>

  <!-- Visual 2: Top 10 State Concentrations (Horizontal Bar Chart) -->
  <g transform="translate(990, 235)" filter="url(#cardShadow)">
    <rect width="578" height="340" rx="10" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="24" y="28" font-family="sans-serif" font-size="14" font-weight="700" fill="#F8FAFC">Top 10 State Concentrations by Funded Principal</text>
    <text x="24" y="44" font-family="sans-serif" font-size="11" fill="#64748B">CA, TX, and NY represent 31.0% of total national credit commitment</text>

    <!-- State Bars -->
    <!-- Max bar width = 340px for CA ($4.80B). Scale = 70.8 px per $1B -->
    <!-- States: CA $4.80B, TX $2.92B, NY $2.76B, FL $2.33B, IL $1.40B, NJ $1.31B, GA $1.14B, PA $1.13B, OH $1.08B, NC $0.93B -->
    <g transform="translate(30, 60)">
      <!-- CA -->
      <text x="0" y="16" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">CA</text>
      <rect x="35" y="4" width="340" height="15" fill="url(#blueBarGrad)" rx="2"/>
      <text x="385" y="16" font-family="sans-serif" font-size="11" font-weight="bold" fill="#38BDF8">$4.80B (14.2%)</text>
      
      <!-- TX -->
      <text x="0" y="42" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">TX</text>
      <rect x="35" y="30" width="207" height="15" fill="url(#blueBarGrad)" rx="2"/>
      <text x="252" y="42" font-family="sans-serif" font-size="11" font-weight="bold" fill="#38BDF8">$2.92B (8.6%)</text>

      <!-- NY -->
      <text x="0" y="68" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">NY</text>
      <rect x="35" y="56" width="195" height="15" fill="url(#blueBarGrad)" rx="2"/>
      <text x="240" y="68" font-family="sans-serif" font-size="11" font-weight="bold" fill="#38BDF8">$2.76B (8.1%)</text>

      <!-- FL -->
      <text x="0" y="94" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">FL</text>
      <rect x="35" y="82" width="165" height="15" fill="url(#blueBarGrad)" rx="2"/>
      <text x="210" y="94" font-family="sans-serif" font-size="11" font-weight="bold" fill="#38BDF8">$2.33B (6.9%)</text>

      <!-- IL -->
      <text x="0" y="120" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">IL</text>
      <rect x="35" y="108" width="99" height="15" fill="url(#blueBarGrad)" rx="2"/>
      <text x="144" y="120" font-family="sans-serif" font-size="11" font-weight="bold" fill="#38BDF8">$1.40B (4.1%)</text>

      <!-- NJ -->
      <text x="0" y="146" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">NJ</text>
      <rect x="35" y="134" width="93" height="15" fill="url(#blueBarGrad)" rx="2"/>
      <text x="138" y="146" font-family="sans-serif" font-size="11" font-weight="bold" fill="#38BDF8">$1.31B (3.9%)</text>

      <!-- GA -->
      <text x="0" y="172" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">GA</text>
      <rect x="35" y="160" width="81" height="15" fill="url(#blueBarGrad)" rx="2"/>
      <text x="126" y="172" font-family="sans-serif" font-size="11" font-weight="bold" fill="#38BDF8">$1.14B (3.4%)</text>

      <!-- PA -->
      <text x="0" y="198" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">PA</text>
      <rect x="35" y="186" width="80" height="15" fill="url(#blueBarGrad)" rx="2"/>
      <text x="125" y="198" font-family="sans-serif" font-size="11" font-weight="bold" fill="#38BDF8">$1.13B (3.3%)</text>

      <!-- OH -->
      <text x="0" y="224" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">OH</text>
      <rect x="35" y="212" width="76" height="15" fill="url(#blueBarGrad)" rx="2"/>
      <text x="121" y="224" font-family="sans-serif" font-size="11" font-weight="bold" fill="#38BDF8">$1.08B (3.2%)</text>

      <!-- NC -->
      <text x="0" y="250" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">NC</text>
      <rect x="35" y="238" width="66" height="15" fill="url(#blueBarGrad)" rx="2"/>
      <text x="111" y="250" font-family="sans-serif" font-size="11" font-weight="bold" fill="#38BDF8">$0.93B (2.7%)</text>
    </g>
  </g>

  <!-- ROW 3: VISUAL 3 & VISUAL 4 -->
  <!-- Visual 3: Credit Grade Summary Matrix / Table -->
  <g transform="translate(32, 595)" filter="url(#cardShadow)">
    <rect width="940" height="275" rx="10" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="24" y="26" font-family="sans-serif" font-size="14" font-weight="700" fill="#F8FAFC">Grade-Level Portfolio Credit Risk Matrix</text>
    
    <!-- Table Header -->
    <rect x="20" y="40" width="900" height="28" fill="#0F172A" rx="4"/>
    <text x="40" y="58" font-family="sans-serif" font-size="11" font-weight="700" fill="#94A3B8">GRADE</text>
    <text x="130" y="58" font-family="sans-serif" font-size="11" font-weight="700" fill="#94A3B8" text-anchor="end">LOAN COUNT</text>
    <text x="260" y="58" font-family="sans-serif" font-size="11" font-weight="700" fill="#94A3B8" text-anchor="end">FUNDED ($B)</text>
    <text x="390" y="58" font-family="sans-serif" font-size="11" font-weight="700" fill="#94A3B8" text-anchor="end">ACTIVE UPB ($B)</text>
    <text x="490" y="58" font-family="sans-serif" font-size="11" font-weight="700" fill="#94A3B8" text-anchor="end">WAC %</text>
    <text x="590" y="58" font-family="sans-serif" font-size="11" font-weight="700" fill="#94A3B8" text-anchor="end">AVG FICO</text>
    <text x="690" y="58" font-family="sans-serif" font-size="11" font-weight="700" fill="#94A3B8" text-anchor="end">AVG DTI</text>
    <text x="790" y="58" font-family="sans-serif" font-size="11" font-weight="700" fill="#94A3B8" text-anchor="end">30+ DPD %</text>
    <text x="900" y="58" font-family="sans-serif" font-size="11" font-weight="700" fill="#94A3B8" text-anchor="end">SEVERE PROXY %</text>

    <!-- Table Rows -->
    <!-- Row A -->
    <g transform="translate(20, 72)">
      <circle cx="20" cy="14" r="5" fill="#10B981"/>
      <text x="35" y="18" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">A</text>
      <text x="110" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">432,363</text>
      <text x="240" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">$6.31B</text>
      <text x="370" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">$1.99B</text>
      <text x="470" y="18" font-family="sans-serif" font-size="11" font-weight="bold" fill="#34D399" text-anchor="end">7.07%</text>
      <text x="570" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">731.0</text>
      <text x="670" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">16.06</text>
      <text x="770" y="18" font-family="sans-serif" font-size="11" fill="#34D399" text-anchor="end">0.31%</text>
      <text x="880" y="18" font-family="sans-serif" font-size="11" fill="#34D399" text-anchor="end">3.29%</text>
      <line x1="0" y1="26" x2="900" y2="26" stroke="#1E293B"/>
    </g>

    <!-- Row B -->
    <g transform="translate(20, 100)">
      <circle cx="20" cy="14" r="5" fill="#34D399"/>
      <text x="35" y="18" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">B</text>
      <text x="110" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">662,453</text>
      <text x="240" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">$9.38B</text>
      <text x="370" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">$2.66B</text>
      <text x="470" y="18" font-family="sans-serif" font-size="11" fill="#60A5FA" text-anchor="end">10.67%</text>
      <text x="570" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">701.8</text>
      <text x="670" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">17.74</text>
      <text x="770" y="18" font-family="sans-serif" font-size="11" fill="#60A5FA" text-anchor="end">0.72%</text>
      <text x="880" y="18" font-family="sans-serif" font-size="11" fill="#60A5FA" text-anchor="end">7.95%</text>
      <line x1="0" y1="26" x2="900" y2="26" stroke="#1E293B"/>
    </g>

    <!-- Row C -->
    <g transform="translate(20, 128)">
      <circle cx="20" cy="14" r="5" fill="#60A5FA"/>
      <text x="35" y="18" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">C</text>
      <text x="110" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">648,749</text>
      <text x="240" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">$9.75B</text>
      <text x="370" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">$2.83B</text>
      <text x="470" y="18" font-family="sans-serif" font-size="11" fill="#93C5FD" text-anchor="end">14.18%</text>
      <text x="570" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">691.3</text>
      <text x="670" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">19.28</text>
      <text x="770" y="18" font-family="sans-serif" font-size="11" fill="#93C5FD" text-anchor="end">1.16%</text>
      <text x="880" y="18" font-family="sans-serif" font-size="11" fill="#FBBF24" text-anchor="end">13.21%</text>
      <line x1="0" y1="26" x2="900" y2="26" stroke="#1E293B"/>
    </g>

    <!-- Row D -->
    <g transform="translate(20, 156)">
      <circle cx="20" cy="14" r="5" fill="#FBBF24"/>
      <text x="35" y="18" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">D</text>
      <text x="110" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">323,630</text>
      <text x="240" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">$5.08B</text>
      <text x="370" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">$1.36B</text>
      <text x="470" y="18" font-family="sans-serif" font-size="11" fill="#FBBF24" text-anchor="end">18.17%</text>
      <text x="570" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">685.9</text>
      <text x="670" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">20.61</text>
      <text x="770" y="18" font-family="sans-serif" font-size="11" fill="#FBBF24" text-anchor="end">1.47%</text>
      <text x="880" y="18" font-family="sans-serif" font-size="11" fill="#F87171" text-anchor="end">18.91%</text>
      <line x1="0" y1="26" x2="900" y2="26" stroke="#1E293B"/>
    </g>

    <!-- Row E -->
    <g transform="translate(20, 184)">
      <circle cx="20" cy="14" r="5" fill="#F97316"/>
      <text x="35" y="18" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">E</text>
      <text x="110" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">135,345</text>
      <text x="240" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">$2.36B</text>
      <text x="370" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">$0.45B</text>
      <text x="470" y="18" font-family="sans-serif" font-size="11" fill="#F97316" text-anchor="end">21.78%</text>
      <text x="570" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">684.4</text>
      <text x="670" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">21.23</text>
      <text x="770" y="18" font-family="sans-serif" font-size="11" fill="#F97316" text-anchor="end">1.59%</text>
      <text x="880" y="18" font-family="sans-serif" font-size="11" font-weight="bold" fill="#EF4444" text-anchor="end">26.73%</text>
      <line x1="0" y1="26" x2="900" y2="26" stroke="#1E293B"/>
    </g>

    <!-- Row F/G summary -->
    <g transform="translate(20, 212)">
      <circle cx="20" cy="14" r="5" fill="#EF4444"/>
      <text x="35" y="18" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">F &amp; G</text>
      <text x="110" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">53,850</text>
      <text x="240" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">$1.04B</text>
      <text x="370" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">$0.16B</text>
      <text x="470" y="18" font-family="sans-serif" font-size="11" font-weight="bold" fill="#EF4444" text-anchor="end">26.09%</text>
      <text x="570" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">682.1</text>
      <text x="670" y="18" font-family="sans-serif" font-size="11" fill="#E2E8F0" text-anchor="end">21.54</text>
      <text x="770" y="18" font-family="sans-serif" font-size="11" font-weight="bold" fill="#EF4444" text-anchor="end">1.62%</text>
      <text x="880" y="18" font-family="sans-serif" font-size="11" font-weight="bold" fill="#DC2626" text-anchor="end">35.64%</text>
    </g>
  </g>

  <!-- Visual 4: Loan Purpose Distribution (Donut Chart) -->
  <g transform="translate(990, 595)" filter="url(#cardShadow)">
    <rect width="578" height="275" rx="10" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="24" y="26" font-family="sans-serif" font-size="14" font-weight="700" fill="#F8FAFC">Portfolio Exposure by Stated Purpose</text>
    
    <!-- SVG Donut Chart -->
    <g transform="translate(130, 145)">
      <!-- Debt Consolidation (58.4%) -->
      <circle cx="0" cy="0" r="70" fill="transparent" stroke="#2563EB" stroke-width="38" stroke-dasharray="257 440" stroke-dashoffset="0"/>
      <!-- Credit Card (22.8%) -->
      <circle cx="0" cy="0" r="70" fill="transparent" stroke="#38BDF8" stroke-width="38" stroke-dasharray="100 440" stroke-dashoffset="-257"/>
      <!-- Home Improvement (6.6%) -->
      <circle cx="0" cy="0" r="70" fill="transparent" stroke="#F59E0B" stroke-width="38" stroke-dasharray="29 440" stroke-dashoffset="-357"/>
      <!-- Major Purchase / Other (12.2%) -->
      <circle cx="0" cy="0" r="70" fill="transparent" stroke="#64748B" stroke-width="38" stroke-dasharray="54 440" stroke-dashoffset="-386"/>
      <!-- Donut Center Callout -->
      <text x="0" y="-4" font-family="sans-serif" font-size="18" font-weight="800" fill="#F8FAFC" text-anchor="middle">$33.92B</text>
      <text x="0" y="14" font-family="sans-serif" font-size="10" fill="#94A3B8" text-anchor="middle">100% FUNDED</text>
    </g>

    <!-- Donut Legend & Stats -->
    <g transform="translate(280, 75)">
      <rect x="0" y="4" width="14" height="14" fill="#2563EB" rx="3"/>
      <text x="24" y="16" font-family="sans-serif" font-size="12" font-weight="bold" fill="#F8FAFC">Debt Consolidation</text>
      <text x="24" y="32" font-family="sans-serif" font-size="11" fill="#94A3B8">$19.82B (58.4%) • 1,277,877 Loans</text>

      <rect x="0" y="52" width="14" height="14" fill="#38BDF8" rx="3"/>
      <text x="24" y="64" font-family="sans-serif" font-size="12" font-weight="bold" fill="#F8FAFC">Credit Card Payoff</text>
      <text x="24" y="80" font-family="sans-serif" font-size="11" fill="#94A3B8">$7.74B (22.8%) • 516,971 Loans</text>

      <rect x="0" y="100" width="14" height="14" fill="#F59E0B" rx="3"/>
      <text x="24" y="112" font-family="sans-serif" font-size="12" font-weight="bold" fill="#F8FAFC">Home Improvement</text>
      <text x="24" y="128" font-family="sans-serif" font-size="11" fill="#94A3B8">$2.24B (6.6%) • 150,457 Loans</text>

      <rect x="0" y="148" width="14" height="14" fill="#64748B" rx="3"/>
      <text x="24" y="160" font-family="sans-serif" font-size="12" font-weight="bold" fill="#F8FAFC">Other / Major Purchase</text>
      <text x="24" y="176" font-family="sans-serif" font-size="11" fill="#94A3B8">$4.12B (12.2%) • 311,085 Loans</text>
    </g>
  </g>
</svg>"""


# ==============================================================================
# PAGE 2: Vintage Delinquency & Loss Migration
# ==============================================================================
def create_page_2() -> str:
    header = generate_header(1, "Vintage Delinquency & Net Credit Loss Curves", "Origination Cohorts 2014–2018 • Rolling 3M Net Credit Loss Rate • Amortization Tenure")
    
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" width="1600" height="900">
  {COMMON_DEFS}
  <!-- Main Canvas Background -->
  <rect width="1600" height="900" fill="url(#bgGrad)"/>
  
  {header}
  
  <!-- ROW 1: 4 KPI CARDS -->
  <!-- Card 1: Gross Charge-Off Principal -->
  <g transform="translate(32, 110)" filter="url(#cardShadow)">
    <rect width="365" height="110" rx="10" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="24" y="32" font-family="sans-serif" font-size="12" font-weight="600" fill="#94A3B8" letter-spacing="0.5">GROSS CHARGE-OFF PRINCIPAL</text>
    <text x="24" y="74" font-family="sans-serif" font-size="34" font-weight="800" fill="#EF4444">$4.42B</text>
    <rect x="235" y="52" width="105" height="24" rx="12" fill="#450A0A"/>
    <text x="287" y="68" font-family="sans-serif" font-size="11" font-weight="700" fill="#F87171" text-anchor="middle">268,559 Units</text>
    <text x="24" y="96" font-family="sans-serif" font-size="11" fill="#64748B">Lifetime Gross Default Rate: 13.04%</text>
  </g>

  <!-- Card 2: Cumulative Recoveries -->
  <g transform="translate(422, 110)" filter="url(#cardShadow)">
    <rect width="365" height="110" rx="10" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="24" y="32" font-family="sans-serif" font-size="12" font-weight="600" fill="#94A3B8" letter-spacing="0.5">POST-CHARGE-OFF RECOVERIES</text>
    <text x="24" y="74" font-family="sans-serif" font-size="34" font-weight="800" fill="#34D399">$371.4M</text>
    <rect x="235" y="52" width="105" height="24" rx="12" fill="#064E3B"/>
    <text x="287" y="68" font-family="sans-serif" font-size="11" font-weight="700" fill="#34D399" text-anchor="middle">8.4% Recovery</text>
    <text x="24" y="96" font-family="sans-serif" font-size="11" fill="#64748B">Legal collections &amp; secondary debt sales</text>
  </g>

  <!-- Card 3: Net Credit Loss (NCL) -->
  <g transform="translate(812, 110)" filter="url(#cardShadow)">
    <rect width="365" height="110" rx="10" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="24" y="32" font-family="sans-serif" font-size="12" font-weight="600" fill="#94A3B8" letter-spacing="0.5">NET CREDIT LOSS (NCL)</text>
    <text x="24" y="74" font-family="sans-serif" font-size="34" font-weight="800" fill="#F97316">$4.05B</text>
    <rect x="235" y="52" width="105" height="24" rx="12" fill="#431407"/>
    <text x="287" y="68" font-family="sans-serif" font-size="11" font-weight="700" fill="#FB923C" text-anchor="middle">Net Loss: 11.9%</text>
    <text x="24" y="96" font-family="sans-serif" font-size="11" fill="#64748B">Gross Charge-Offs minus Recoveries</text>
  </g>

  <!-- Card 4: 3-Month Rolling Net Loss Rate -->
  <g transform="translate(1202, 110)" filter="url(#cardShadow)">
    <rect width="365" height="110" rx="10" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="24" y="32" font-family="sans-serif" font-size="12" font-weight="600" fill="#94A3B8" letter-spacing="0.5">3M ROLLING NET LOSS RATE</text>
    <text x="24" y="74" font-family="sans-serif" font-size="34" font-weight="800" fill="#38BDF8">7.82%</text>
    <rect x="240" y="52" width="100" height="24" rx="12" fill="#0C4A6E"/>
    <text x="290" y="68" font-family="sans-serif" font-size="11" font-weight="700" fill="#38BDF8" text-anchor="middle">Peak: 11.4%</text>
    <text x="24" y="96" font-family="sans-serif" font-size="11" fill="#64748B">Recent 2018 vintages seasoning favorably</text>
  </g>

  <!-- ROW 2: VINTAGE LOSS CURVES & VOLUME COMBO CHART (Full Width) -->
  <g transform="translate(32, 235)" filter="url(#cardShadow)">
    <rect width="1535" height="345" rx="10" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="24" y="28" font-family="sans-serif" font-size="15" font-weight="700" fill="#F8FAFC">Vintage Origination Volume ($M) &amp; 3-Month Rolling Net Credit Loss Trend (2014–2018)</text>
    <text x="24" y="46" font-family="sans-serif" font-size="11" fill="#64748B">PostgreSQL view: vw_chargeoff_loss_trend • Derived via AVG(net_loss_rate_pct) OVER (ORDER BY issue_ym ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)</text>
    
    <!-- Legend -->
    <g transform="translate(1080, 20)">
      <rect x="0" y="4" width="14" height="14" fill="#334155" rx="2"/>
      <text x="20" y="16" font-family="sans-serif" font-size="11" fill="#94A3B8">Origination Vol ($M)</text>
      <line x1="160" y1="11" x2="190" y2="11" stroke="#94A3B8" stroke-width="1.5" stroke-dasharray="3,3"/>
      <text x="198" y="16" font-family="sans-serif" font-size="11" fill="#94A3B8">Monthly NCL %</text>
      <line x1="300" y1="11" x2="330" y2="11" stroke="#EF4444" stroke-width="3"/>
      <text x="338" y="16" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F87171">3M Rolling NCL %</text>
    </g>

    <!-- Gridlines & Y-Axis Left ($M Volume) -->
    <line x1="60" y1="75" x2="1470" y2="75" stroke="#334155" stroke-dasharray="2,2"/>
    <text x="50" y="79" font-family="sans-serif" font-size="10" fill="#64748B" text-anchor="end">$1,000M</text>
    <line x1="60" y1="135" x2="1470" y2="135" stroke="#334155" stroke-dasharray="2,2"/>
    <text x="50" y="139" font-family="sans-serif" font-size="10" fill="#64748B" text-anchor="end">$750M</text>
    <line x1="60" y1="195" x2="1470" y2="195" stroke="#334155" stroke-dasharray="2,2"/>
    <text x="50" y="199" font-family="sans-serif" font-size="10" fill="#64748B" text-anchor="end">$500M</text>
    <line x1="60" y1="255" x2="1470" y2="255" stroke="#334155" stroke-dasharray="2,2"/>
    <text x="50" y="259" font-family="sans-serif" font-size="10" fill="#64748B" text-anchor="end">$250M</text>
    <line x1="60" y1="305" x2="1470" y2="305" stroke="#475569" stroke-width="1.5"/>
    <text x="50" y="309" font-family="sans-serif" font-size="10" fill="#64748B" text-anchor="end">$0</text>

    <!-- Right Axis (NCL Rate %) -->
    <text x="1480" y="79" font-family="sans-serif" font-size="10" fill="#EF4444">14.0%</text>
    <text x="1480" y="139" font-family="sans-serif" font-size="10" fill="#EF4444">10.5%</text>
    <text x="1480" y="199" font-family="sans-serif" font-size="10" fill="#EF4444">7.0%</text>
    <text x="1480" y="259" font-family="sans-serif" font-size="10" fill="#EF4444">3.5%</text>
    <text x="1480" y="309" font-family="sans-serif" font-size="10" fill="#EF4444">0.0%</text>

    <!-- Volume Bars (Sample of 30 monthly cohorts across 2014-2018) -->
    <!-- X ranges from 75 to 1450 -->
    <g fill="#1E3A8A" opacity="0.65">
      <rect x="75" y="240" width="28" height="65" rx="2"/>
      <rect x="120" y="235" width="28" height="70" rx="2"/>
      <rect x="165" y="225" width="28" height="80" rx="2"/>
      <rect x="210" y="220" width="28" height="85" rx="2"/>
      <rect x="255" y="210" width="28" height="95" rx="2"/>
      <rect x="300" y="170" width="28" height="135" rx="2"/>
      <rect x="345" y="160" width="28" height="145" rx="2"/>
      <rect x="390" y="150" width="28" height="155" rx="2"/>
      <rect x="435" y="145" width="28" height="160" rx="2"/>
      <rect x="480" y="125" width="28" height="180" rx="2"/>
      <rect x="525" y="130" width="28" height="175" rx="2"/>
      <rect x="570" y="115" width="28" height="190" rx="2"/>
      <rect x="615" y="100" width="28" height="205" rx="2"/>
      <rect x="660" y="90" width="28" height="215" rx="2"/>
      <rect x="705" y="85" width="28" height="220" rx="2"/>
      <rect x="750" y="110" width="28" height="195" rx="2"/>
      <rect x="795" y="130" width="28" height="175" rx="2"/>
      <rect x="840" y="140" width="28" height="165" rx="2"/>
      <rect x="885" y="150" width="28" height="155" rx="2"/>
      <rect x="930" y="135" width="28" height="170" rx="2"/>
      <rect x="975" y="145" width="28" height="160" rx="2"/>
      <rect x="1020" y="130" width="28" height="175" rx="2"/>
      <rect x="1065" y="120" width="28" height="185" rx="2"/>
      <rect x="1110" y="110" width="28" height="195" rx="2"/>
      <rect x="1155" y="105" width="28" height="200" rx="2"/>
      <rect x="1200" y="95" width="28" height="210" rx="2"/>
      <rect x="1245" y="90" width="28" height="215" rx="2"/>
      <rect x="1290" y="85" width="28" height="220" rx="2"/>
      <rect x="1335" y="100" width="28" height="205" rx="2"/>
      <rect x="1380" y="120" width="28" height="185" rx="2"/>
      <rect x="1425" y="135" width="28" height="170" rx="2"/>
    </g>

    <!-- Monthly Net Loss Line (Light Slate Dotted) -->
    <polyline points="89,145 134,140 179,132 224,124 269,122 314,118 359,126 404,115 449,112 494,110 539,120 584,114 629,105 674,108 719,102 764,112 809,118 854,116 899,102 944,115 989,140 1034,148 1079,165 1124,180 1169,210 1214,235 1259,255 1304,275 1349,288 1394,296 1439,301" fill="none" stroke="#94A3B8" stroke-width="1.5" stroke-dasharray="3,3"/>

    <!-- 3M Rolling Net Loss Curve (Crimson Solid with Gradient Glow) -->
    <polyline points="89,145 134,142 179,136 224,128 269,123 314,120 359,121 404,120 449,116 494,112 539,114 584,113 629,110 674,107 719,105 764,109 809,113 854,115 899,112 944,110 989,122 1034,138 1079,151 1124,168 1169,195 1214,225 1259,250 1304,272 1349,285 1394,295 1439,300" fill="none" stroke="#EF4444" stroke-width="3.5"/>

    <!-- Data Callout Markers -->
    <g transform="translate(674, 107)">
      <circle cx="0" cy="0" r="5" fill="#EF4444" stroke="#FFFFFF" stroke-width="2"/>
      <rect x="-40" y="-30" width="80" height="22" rx="4" fill="#1E293B" stroke="#EF4444" stroke-width="1"/>
      <text x="0" y="-15" font-family="sans-serif" font-size="10" font-weight="bold" fill="#FCA5A5" text-anchor="middle">Peak 11.4%</text>
    </g>
    <g transform="translate(1439, 300)">
      <circle cx="0" cy="0" r="5" fill="#10B981" stroke="#FFFFFF" stroke-width="2"/>
      <rect x="-45" y="-30" width="90" height="22" rx="4" fill="#1E293B" stroke="#10B981" stroke-width="1"/>
      <text x="0" y="-15" font-family="sans-serif" font-size="10" font-weight="bold" fill="#34D399" text-anchor="middle">Current 0.4%</text>
    </g>

    <!-- X-Axis Labels (Timeline 2014 to 2018) -->
    <text x="140" y="325" font-family="sans-serif" font-size="11" fill="#94A3B8" text-anchor="middle">2014-Q1</text>
    <text x="400" y="325" font-family="sans-serif" font-size="11" fill="#94A3B8" text-anchor="middle">2015-Q1</text>
    <text x="680" y="325" font-family="sans-serif" font-size="11" fill="#94A3B8" text-anchor="middle">2016-Q1</text>
    <text x="960" y="325" font-family="sans-serif" font-size="11" fill="#94A3B8" text-anchor="middle">2017-Q1</text>
    <text x="1240" y="325" font-family="sans-serif" font-size="11" fill="#94A3B8" text-anchor="middle">2018-Q1</text>
  </g>

  <!-- ROW 3: VINTAGE DELINQUENCY HEATMAP & TENOR COMPARISON -->
  <!-- Visual 3: Delinquency Migration Matrix (Heatmap) -->
  <g transform="translate(32, 600)" filter="url(#cardShadow)">
    <rect width="980" height="270" rx="10" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="24" y="26" font-family="sans-serif" font-size="14" font-weight="700" fill="#F8FAFC">Vintage Delinquency Heatmap (30+ DPD % by Origination Year &amp; Grade)</text>
    
    <!-- Heatmap Table -->
    <rect x="24" y="42" width="932" height="26" fill="#0F172A" rx="4"/>
    <text x="40" y="59" font-family="sans-serif" font-size="11" font-weight="700" fill="#94A3B8">VINTAGE</text>
    <text x="170" y="59" font-family="sans-serif" font-size="11" font-weight="700" fill="#94A3B8">GRADE A</text>
    <text x="300" y="59" font-family="sans-serif" font-size="11" font-weight="700" fill="#94A3B8">GRADE B</text>
    <text x="430" y="59" font-family="sans-serif" font-size="11" font-weight="700" fill="#94A3B8">GRADE C</text>
    <text x="560" y="59" font-family="sans-serif" font-size="11" font-weight="700" fill="#94A3B8">GRADE D</text>
    <text x="690" y="59" font-family="sans-serif" font-size="11" font-weight="700" fill="#94A3B8">GRADE E</text>
    <text x="820" y="59" font-family="sans-serif" font-size="11" font-weight="700" fill="#94A3B8">GRADE F/G</text>

    <!-- 2014 -->
    <g transform="translate(24, 76)">
      <text x="16" y="22" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">2014 Cohort</text>
      <rect x="130" y="4" width="100" height="24" rx="4" fill="#064E3B"/><text x="180" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#34D399" text-anchor="middle">0.12%</text>
      <rect x="260" y="4" width="100" height="24" rx="4" fill="#064E3B"/><text x="310" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#34D399" text-anchor="middle">0.28%</text>
      <rect x="390" y="4" width="100" height="24" rx="4" fill="#065F46"/><text x="440" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#34D399" text-anchor="middle">0.45%</text>
      <rect x="520" y="4" width="100" height="24" rx="4" fill="#78350F"/><text x="570" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#FBBF24" text-anchor="middle">0.82%</text>
      <rect x="650" y="4" width="100" height="24" rx="4" fill="#9A3412"/><text x="700" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#FB923C" text-anchor="middle">1.15%</text>
      <rect x="780" y="4" width="100" height="24" rx="4" fill="#7F1D1D"/><text x="830" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F87171" text-anchor="middle">1.48%</text>
    </g>

    <!-- 2015 -->
    <g transform="translate(24, 110)">
      <text x="16" y="22" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">2015 Cohort</text>
      <rect x="130" y="4" width="100" height="24" rx="4" fill="#064E3B"/><text x="180" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#34D399" text-anchor="middle">0.18%</text>
      <rect x="260" y="4" width="100" height="24" rx="4" fill="#065F46"/><text x="310" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#34D399" text-anchor="middle">0.42%</text>
      <rect x="390" y="4" width="100" height="24" rx="4" fill="#78350F"/><text x="440" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#FBBF24" text-anchor="middle">0.78%</text>
      <rect x="520" y="4" width="100" height="24" rx="4" fill="#9A3412"/><text x="570" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#FB923C" text-anchor="middle">1.22%</text>
      <rect x="650" y="4" width="100" height="24" rx="4" fill="#7F1D1D"/><text x="700" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F87171" text-anchor="middle">1.64%</text>
      <rect x="780" y="4" width="100" height="24" rx="4" fill="#991B1B"/><text x="830" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#FCA5A5" text-anchor="middle">2.10%</text>
    </g>

    <!-- 2016 -->
    <g transform="translate(24, 144)">
      <text x="16" y="22" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">2016 Cohort</text>
      <rect x="130" y="4" width="100" height="24" rx="4" fill="#064E3B"/><text x="180" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#34D399" text-anchor="middle">0.24%</text>
      <rect x="260" y="4" width="100" height="24" rx="4" fill="#065F46"/><text x="310" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#34D399" text-anchor="middle">0.55%</text>
      <rect x="390" y="4" width="100" height="24" rx="4" fill="#78350F"/><text x="440" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#FBBF24" text-anchor="middle">0.96%</text>
      <rect x="520" y="4" width="100" height="24" rx="4" fill="#7F1D1D"/><text x="570" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F87171" text-anchor="middle">1.54%</text>
      <rect x="650" y="4" width="100" height="24" rx="4" fill="#991B1B"/><text x="700" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#FCA5A5" text-anchor="middle">2.05%</text>
      <rect x="780" y="4" width="100" height="24" rx="4" fill="#7F1D1D"/><text x="830" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F87171" text-anchor="middle">2.44%</text>
    </g>

    <!-- 2017 -->
    <g transform="translate(24, 178)">
      <text x="16" y="22" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">2017 Cohort</text>
      <rect x="130" y="4" width="100" height="24" rx="4" fill="#065F46"/><text x="180" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#34D399" text-anchor="middle">0.63%</text>
      <rect x="260" y="4" width="100" height="24" rx="4" fill="#78350F"/><text x="310" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#FBBF24" text-anchor="middle">1.39%</text>
      <rect x="390" y="4" width="100" height="24" rx="4" fill="#991B1B"/><text x="440" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#FCA5A5" text-anchor="middle">2.13%</text>
      <rect x="520" y="4" width="100" height="24" rx="4" fill="#7F1D1D"/><text x="570" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F87171" text-anchor="middle">2.78%</text>
      <rect x="650" y="4" width="100" height="24" rx="4" fill="#991B1B"/><text x="700" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#FCA5A5" text-anchor="middle">3.21%</text>
      <rect x="780" y="4" width="100" height="24" rx="4" fill="#7F1D1D"/><text x="830" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F87171" text-anchor="middle">3.74%</text>
    </g>

    <!-- 2018 -->
    <g transform="translate(24, 212)">
      <text x="16" y="22" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">2018 Cohort</text>
      <rect x="130" y="4" width="100" height="24" rx="4" fill="#065F46"/><text x="180" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#34D399" text-anchor="middle">0.45%</text>
      <rect x="260" y="4" width="100" height="24" rx="4" fill="#78350F"/><text x="310" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#FBBF24" text-anchor="middle">1.12%</text>
      <rect x="390" y="4" width="100" height="24" rx="4" fill="#78350F"/><text x="440" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#FBBF24" text-anchor="middle">1.75%</text>
      <rect x="520" y="4" width="100" height="24" rx="4" fill="#991B1B"/><text x="570" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#FCA5A5" text-anchor="middle">2.35%</text>
      <rect x="650" y="4" width="100" height="24" rx="4" fill="#7F1D1D"/><text x="700" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F87171" text-anchor="middle">2.82%</text>
      <rect x="780" y="4" width="100" height="24" rx="4" fill="#7F1D1D"/><text x="830" y="20" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F87171" text-anchor="middle">3.40%</text>
    </g>
  </g>

  <!-- Visual 4: 36M vs 60M Term Performance Comparison -->
  <g transform="translate(1030, 600)" filter="url(#cardShadow)">
    <rect width="537" height="270" rx="10" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="24" y="26" font-family="sans-serif" font-size="14" font-weight="700" fill="#F8FAFC">Tenor Comparison: 36M vs 60M Term</text>
    <text x="24" y="42" font-family="sans-serif" font-size="11" fill="#64748B">60-month loans exhibit 2.3x higher default and credit loss propensity</text>

    <!-- 36 Months Group -->
    <g transform="translate(40, 75)">
      <rect x="0" y="0" width="200" height="165" rx="8" fill="#1E293B" stroke="#2563EB" stroke-width="1.5"/>
      <text x="100" y="28" font-family="sans-serif" font-size="16" font-weight="800" fill="#60A5FA" text-anchor="middle">36 MONTHS</text>
      <text x="100" y="46" font-family="sans-serif" font-size="11" fill="#94A3B8" text-anchor="middle">1,611,801 Loans (71.4%)</text>
      
      <line x1="20" y1="58" x2="180" y2="58" stroke="#334155"/>
      <text x="24" y="80" font-family="sans-serif" font-size="11" fill="#94A3B8">Funded Principal:</text>
      <text x="176" y="80" font-family="sans-serif" font-size="12" font-weight="bold" fill="#F8FAFC" text-anchor="end">$20.24B</text>

      <text x="24" y="105" font-family="sans-serif" font-size="11" fill="#94A3B8">Avg Coupon (WAC):</text>
      <text x="176" y="105" font-family="sans-serif" font-size="12" font-weight="bold" fill="#38BDF8" text-anchor="end">12.15%</text>

      <text x="24" y="130" font-family="sans-serif" font-size="11" fill="#94A3B8">30+ DPD Rate:</text>
      <text x="176" y="130" font-family="sans-serif" font-size="12" font-weight="bold" fill="#34D399" text-anchor="end">0.78%</text>

      <text x="24" y="152" font-family="sans-serif" font-size="11" fill="#94A3B8">Default Proxy Rate:</text>
      <text x="176" y="152" font-family="sans-serif" font-size="12" font-weight="bold" fill="#34D399" text-anchor="end">8.92%</text>
    </g>

    <!-- 60 Months Group -->
    <g transform="translate(280, 75)">
      <rect x="0" y="0" width="200" height="165" rx="8" fill="#1E293B" stroke="#F59E0B" stroke-width="1.5"/>
      <text x="100" y="28" font-family="sans-serif" font-size="16" font-weight="800" fill="#FBBF24" text-anchor="middle">60 MONTHS</text>
      <text x="100" y="46" font-family="sans-serif" font-size="11" fill="#94A3B8" text-anchor="middle">644,589 Loans (28.6%)</text>
      
      <line x1="20" y1="58" x2="180" y2="58" stroke="#334155"/>
      <text x="24" y="80" font-family="sans-serif" font-size="11" fill="#94A3B8">Funded Principal:</text>
      <text x="176" y="80" font-family="sans-serif" font-size="12" font-weight="bold" fill="#F8FAFC" text-anchor="end">$13.68B</text>

      <text x="24" y="105" font-family="sans-serif" font-size="11" fill="#94A3B8">Avg Coupon (WAC):</text>
      <text x="176" y="105" font-family="sans-serif" font-size="12" font-weight="bold" fill="#FBBF24" text-anchor="end">15.20%</text>

      <text x="24" y="130" font-family="sans-serif" font-size="11" fill="#94A3B8">30+ DPD Rate:</text>
      <text x="176" y="130" font-family="sans-serif" font-size="12" font-weight="bold" fill="#F87171" text-anchor="end">1.37%</text>

      <text x="24" y="152" font-family="sans-serif" font-size="11" fill="#94A3B8">Default Proxy Rate:</text>
      <text x="176" y="152" font-family="sans-serif" font-size="12" font-weight="bold" fill="#EF4444" text-anchor="end">19.46%</text>
    </g>
  </g>
</svg>"""


# ==============================================================================
# PAGE 3: Vendor Feed SLA & Data Quality Governance
# ==============================================================================
def create_page_3() -> str:
    header = generate_header(2, "Vendor Feed Delivery SLA & Data Quality Governance", "FirstMark Servicing Feed Audits • 12 Rule Pass % • Negative Testing Quarantine Breakdown")
    
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" width="1600" height="900">
  {COMMON_DEFS}
  <!-- Main Canvas Background -->
  <rect width="1600" height="900" fill="url(#bgGrad)"/>
  
  {header}
  
  <!-- ROW 1: 4 KPI CARDS -->
  <!-- Card 1: Total Processed Records -->
  <g transform="translate(32, 110)" filter="url(#cardShadow)">
    <rect width="365" height="110" rx="10" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="24" y="32" font-family="sans-serif" font-size="12" font-weight="600" fill="#94A3B8" letter-spacing="0.5">INGESTED FEED VOLUME</text>
    <text x="24" y="74" font-family="sans-serif" font-size="34" font-weight="800" fill="#F8FAFC">2,260,701</text>
    <rect x="235" y="52" width="105" height="24" rx="12" fill="#1E3A8A"/>
    <text x="287" y="68" font-family="sans-serif" font-size="11" font-weight="700" fill="#60A5FA" text-anchor="middle">5 Prod Feeds</text>
    <text x="24" y="96" font-family="sans-serif" font-size="11" fill="#64748B">1.68 GB Raw Source Ingested (30 Canonical Cols)</text>
  </g>

  <!-- Card 2: Overall DQ Pass Rate -->
  <g transform="translate(422, 110)" filter="url(#cardShadow)">
    <rect width="365" height="110" rx="10" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="24" y="32" font-family="sans-serif" font-size="12" font-weight="600" fill="#94A3B8" letter-spacing="0.5">OVERALL DQ PASS RATE</text>
    <text x="24" y="74" font-family="sans-serif" font-size="34" font-weight="800" fill="#34D399">99.81%</text>
    <rect x="235" y="52" width="105" height="24" rx="12" fill="#064E3B"/>
    <text x="287" y="68" font-family="sans-serif" font-size="11" font-weight="700" fill="#34D399" text-anchor="middle">SLA: 95.00%</text>
    <text x="24" y="96" font-family="sans-serif" font-size="11" fill="#64748B">2,256,390 Clean Rows loaded to PostgreSQL</text>
  </g>

  <!-- Card 3: Vendor Feed SLA Timeliness -->
  <g transform="translate(812, 110)" filter="url(#cardShadow)">
    <rect width="365" height="110" rx="10" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="24" y="32" font-family="sans-serif" font-size="12" font-weight="600" fill="#94A3B8" letter-spacing="0.5">FEED DELIVERY SLA STATUS</text>
    <text x="24" y="74" font-family="sans-serif" font-size="34" font-weight="800" fill="#FBBF24">80.0% <tspan font-size="18" fill="#94A3B8">ON-TIME</tspan></text>
    <rect x="235" y="52" width="105" height="24" rx="12" fill="#451A03"/>
    <text x="287" y="68" font-family="sans-serif" font-size="11" font-weight="700" fill="#F59E0B" text-anchor="middle">Cutoff: 06:30 IST</text>
    <text x="24" y="96" font-family="sans-serif" font-size="11" fill="#64748B">1 Late Feed (20261008: 07:18 IST, 48m delay)</text>
  </g>

  <!-- Card 4: Quarantined & Rejection Summary -->
  <g transform="translate(1202, 110)" filter="url(#cardShadow)">
    <rect width="365" height="110" rx="10" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="24" y="32" font-family="sans-serif" font-size="12" font-weight="600" fill="#94A3B8" letter-spacing="0.5">ISOLATED REJECTS</text>
    <text x="24" y="74" font-family="sans-serif" font-size="34" font-weight="800" fill="#38BDF8">4,311 <tspan font-size="18" fill="#94A3B8">Rows</tspan></text>
    <rect x="240" y="52" width="100" height="24" rx="12" fill="#0C4A6E"/>
    <text x="290" y="68" font-family="sans-serif" font-size="11" font-weight="700" fill="#38BDF8" text-anchor="middle">0.19% Fail Rate</text>
    <text x="24" y="96" font-family="sans-serif" font-size="11" fill="#64748B">Tagged with pipe-delimited rule reason codes</text>
  </g>

  <!-- ROW 2: VISUAL 1 & VISUAL 2 -->
  <!-- Visual 1: Vendor Feed Delivery & Gatekeeper Waterfall / Column Chart -->
  <g transform="translate(32, 235)" filter="url(#cardShadow)">
    <rect width="940" height="345" rx="10" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="24" y="28" font-family="sans-serif" font-size="14" font-weight="700" fill="#F8FAFC">Vendor Feed Gatekeeper &amp; Negative-Testing Audit Log (11 Batch Runs)</text>
    <text x="24" y="44" font-family="sans-serif" font-size="11" fill="#64748B">Green: On-Time Pass • Orange: Late Pass • Red: Quarantined (Exit Codes 10, 11, 12, 13, 20)</text>

    <!-- Legend -->
    <g transform="translate(630, 20)">
      <circle cx="6" cy="10" r="5" fill="#10B981"/>
      <text x="16" y="14" font-family="sans-serif" font-size="10" fill="#94A3B8">On-Time Pass (0)</text>
      <circle cx="120" cy="10" r="5" fill="#F59E0B"/>
      <text x="130" y="14" font-family="sans-serif" font-size="10" fill="#94A3B8">Late Pass (0)</text>
      <circle cx="215" cy="10" r="5" fill="#EF4444"/>
      <text x="225" y="14" font-family="sans-serif" font-size="10" fill="#94A3B8">Rejected (Non-Zero)</text>
    </g>

    <!-- Chart Axes -->
    <line x1="50" y1="70" x2="900" y2="70" stroke="#334155" stroke-dasharray="2,2"/>
    <line x1="50" y1="140" x2="900" y2="140" stroke="#334155" stroke-dasharray="2,2"/>
    <line x1="50" y1="210" x2="900" y2="210" stroke="#334155" stroke-dasharray="2,2"/>
    <line x1="50" y1="270" x2="900" y2="270" stroke="#475569" stroke-width="1.5"/>

    <text x="40" y="74" font-family="sans-serif" font-size="10" fill="#64748B" text-anchor="end">500k</text>
    <text x="40" y="144" font-family="sans-serif" font-size="10" fill="#64748B" text-anchor="end">350k</text>
    <text x="40" y="214" font-family="sans-serif" font-size="10" fill="#64748B" text-anchor="end">150k</text>
    <text x="40" y="274" font-family="sans-serif" font-size="10" fill="#64748B" text-anchor="end">0</text>

    <!-- 11 Batches -->
    <!-- Prod Feeds 20261005..20261009 height ~ 200px (452k rows) -->
    <!-- Negative feeds 20261010..20261015 -->
    <!-- X offsets: 65, 142, 219, 296, 373, 450, 527, 604, 681, 758, 835 -->
    <g>
      <!-- 20261005: On Time (Exit 0) -->
      <rect x="65" y="80" width="48" height="190" fill="#10B981" rx="3"/>
      <text x="89" y="72" font-family="sans-serif" font-size="10" font-weight="bold" fill="#34D399" text-anchor="middle">452k</text>
      <text x="89" y="286" font-family="sans-serif" font-size="10" fill="#94A3B8" text-anchor="middle">10-05</text>
      <text x="89" y="300" font-family="sans-serif" font-size="9" fill="#10B981" text-anchor="middle">Exit 0</text>

      <!-- 20261006: On Time (Exit 0) -->
      <rect x="142" y="80" width="48" height="190" fill="#10B981" rx="3"/>
      <text x="166" y="72" font-family="sans-serif" font-size="10" font-weight="bold" fill="#34D399" text-anchor="middle">452k</text>
      <text x="166" y="286" font-family="sans-serif" font-size="10" fill="#94A3B8" text-anchor="middle">10-06</text>
      <text x="166" y="300" font-family="sans-serif" font-size="9" fill="#10B981" text-anchor="middle">Exit 0</text>

      <!-- 20261007: On Time (Exit 0) -->
      <rect x="219" y="80" width="48" height="190" fill="#10B981" rx="3"/>
      <text x="243" y="72" font-family="sans-serif" font-size="10" font-weight="bold" fill="#34D399" text-anchor="middle">452k</text>
      <text x="243" y="286" font-family="sans-serif" font-size="10" fill="#94A3B8" text-anchor="middle">10-07</text>
      <text x="243" y="300" font-family="sans-serif" font-size="9" fill="#10B981" text-anchor="middle">Exit 0</text>

      <!-- 20261008: LATE (Exit 0) -->
      <rect x="296" y="80" width="48" height="190" fill="#F59E0B" rx="3"/>
      <text x="320" y="72" font-family="sans-serif" font-size="10" font-weight="bold" fill="#FBBF24" text-anchor="middle">452k</text>
      <text x="320" y="286" font-family="sans-serif" font-size="10" fill="#94A3B8" text-anchor="middle">10-08</text>
      <text x="320" y="300" font-family="sans-serif" font-size="9" font-weight="bold" fill="#F59E0B" text-anchor="middle">LATE (0)</text>

      <!-- 20261009: On Time (Exit 0) -->
      <rect x="373" y="80" width="48" height="190" fill="#10B981" rx="3"/>
      <text x="397" y="72" font-family="sans-serif" font-size="10" font-weight="bold" fill="#34D399" text-anchor="middle">452k</text>
      <text x="397" y="286" font-family="sans-serif" font-size="10" fill="#94A3B8" text-anchor="middle">10-09</text>
      <text x="397" y="300" font-family="sans-serif" font-size="9" fill="#10B981" text-anchor="middle">Exit 0</text>

      <!-- 20261010: Truncated (Exit 11) -->
      <rect x="450" y="250" width="48" height="20" fill="#EF4444" rx="3"/>
      <text x="474" y="244" font-family="sans-serif" font-size="9" font-weight="bold" fill="#F87171" text-anchor="middle">1.25k</text>
      <text x="474" y="286" font-family="sans-serif" font-size="10" fill="#94A3B8" text-anchor="middle">10-10</text>
      <text x="474" y="300" font-family="sans-serif" font-size="9" font-weight="bold" fill="#EF4444" text-anchor="middle">Exit 11</text>
      <text x="474" y="312" font-family="sans-serif" font-size="8" fill="#64748B" text-anchor="middle">Checksum</text>

      <!-- 20261011: Rowcount (Exit 12) -->
      <rect x="527" y="245" width="48" height="25" fill="#EF4444" rx="3"/>
      <text x="551" y="239" font-family="sans-serif" font-size="9" font-weight="bold" fill="#F87171" text-anchor="middle">10k</text>
      <text x="551" y="286" font-family="sans-serif" font-size="10" fill="#94A3B8" text-anchor="middle">10-11</text>
      <text x="551" y="300" font-family="sans-serif" font-size="9" font-weight="bold" fill="#EF4444" text-anchor="middle">Exit 12</text>
      <text x="551" y="312" font-family="sans-serif" font-size="8" fill="#64748B" text-anchor="middle">RowCount</text>

      <!-- 20261012: Header (Exit 13) -->
      <rect x="604" y="245" width="48" height="25" fill="#EF4444" rx="3"/>
      <text x="628" y="239" font-family="sans-serif" font-size="9" font-weight="bold" fill="#F87171" text-anchor="middle">10k</text>
      <text x="628" y="286" font-family="sans-serif" font-size="10" fill="#94A3B8" text-anchor="middle">10-12</text>
      <text x="628" y="300" font-family="sans-serif" font-size="9" font-weight="bold" fill="#EF4444" text-anchor="middle">Exit 13</text>
      <text x="628" y="312" font-family="sans-serif" font-size="8" fill="#64748B" text-anchor="middle">Bad Header</text>

      <!-- 20261013: 1% Breach (Exit 0 w/ Rejects) -->
      <rect x="681" y="245" width="48" height="25" fill="#10B981" rx="3"/>
      <text x="705" y="239" font-family="sans-serif" font-size="9" font-weight="bold" fill="#34D399" text-anchor="middle">10k</text>
      <text x="705" y="286" font-family="sans-serif" font-size="10" fill="#94A3B8" text-anchor="middle">10-13</text>
      <text x="705" y="300" font-family="sans-serif" font-size="9" fill="#10B981" text-anchor="middle">Exit 0</text>
      <text x="705" y="312" font-family="sans-serif" font-size="8" fill="#F59E0B" text-anchor="middle">101 Rej</text>

      <!-- 20261014: >8% Breach (Exit 20) -->
      <rect x="758" y="245" width="48" height="25" fill="#EF4444" rx="3"/>
      <text x="782" y="239" font-family="sans-serif" font-size="9" font-weight="bold" fill="#F87171" text-anchor="middle">10k</text>
      <text x="782" y="286" font-family="sans-serif" font-size="10" fill="#94A3B8" text-anchor="middle">10-14</text>
      <text x="782" y="300" font-family="sans-serif" font-size="9" font-weight="bold" fill="#EF4444" text-anchor="middle">Exit 20</text>
      <text x="782" y="312" font-family="sans-serif" font-size="8" fill="#64748B" text-anchor="middle">DQ &gt; 5%</text>

      <!-- 20261015: Missing (Exit 10) -->
      <rect x="835" y="266" width="48" height="4" fill="#EF4444" rx="2"/>
      <text x="859" y="258" font-family="sans-serif" font-size="9" font-weight="bold" fill="#F87171" text-anchor="middle">0</text>
      <text x="859" y="286" font-family="sans-serif" font-size="10" fill="#94A3B8" text-anchor="middle">10-15</text>
      <text x="859" y="300" font-family="sans-serif" font-size="9" font-weight="bold" fill="#EF4444" text-anchor="middle">Exit 10</text>
      <text x="859" y="312" font-family="sans-serif" font-size="8" fill="#64748B" text-anchor="middle">Missing</text>
    </g>
  </g>

  <!-- Visual 2: Data Quality 12-Rule Compliance Pass % (Horizontal Bars) -->
  <g transform="translate(990, 235)" filter="url(#cardShadow)">
    <rect width="578" height="345" rx="10" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="24" y="28" font-family="sans-serif" font-size="14" font-weight="700" fill="#F8FAFC">12-Rule Data Quality Engine Compliance (%)</text>
    <text x="24" y="44" font-family="sans-serif" font-size="11" fill="#64748B">Evaluated in PySpark local mode across 5 dimensions • SLA Threshold: 99.0%–99.95%</text>

    <!-- 12 Rules Listed with Pass % -->
    <!-- Max bar width = 310px. Baseline = 99.0% -->
    <g transform="translate(24, 64)">
      <!-- Rule 1: DQ_CMP_001 -->
      <text x="0" y="16" font-family="monospace" font-size="10" fill="#94A3B8">DQ_CMP_001</text>
      <text x="90" y="16" font-family="sans-serif" font-size="11" fill="#E2E8F0">Mandatory Keys Non-Null</text>
      <rect x="260" y="5" width="220" height="13" fill="#10B981" rx="2"/>
      <text x="490" y="16" font-family="sans-serif" font-size="11" font-weight="bold" fill="#34D399">99.998%</text>

      <!-- Rule 2: DQ_CMP_002 -->
      <text x="0" y="38" font-family="monospace" font-size="10" fill="#94A3B8">DQ_CMP_002</text>
      <text x="90" y="38" font-family="sans-serif" font-size="11" fill="#E2E8F0">Underwriting Fields Populated</text>
      <rect x="260" y="27" width="215" height="13" fill="#10B981" rx="2"/>
      <text x="490" y="38" font-family="sans-serif" font-size="11" font-weight="bold" fill="#34D399">99.942%</text>

      <!-- Rule 3: DQ_UNQ_001 -->
      <text x="0" y="60" font-family="monospace" font-size="10" fill="#94A3B8">DQ_UNQ_001</text>
      <text x="90" y="60" font-family="sans-serif" font-size="11" fill="#E2E8F0">Unique Numeric ID / Dedup</text>
      <rect x="260" y="49" width="220" height="13" fill="#10B981" rx="2"/>
      <text x="490" y="60" font-family="sans-serif" font-size="11" font-weight="bold" fill="#34D399">99.998%</text>

      <!-- Rule 4: DQ_VAL_001 -->
      <text x="0" y="82" font-family="monospace" font-size="10" fill="#94A3B8">DQ_VAL_001</text>
      <text x="90" y="82" font-family="sans-serif" font-size="11" fill="#E2E8F0">Grade A-G &amp; Status Valid</text>
      <rect x="260" y="71" width="220" height="13" fill="#10B981" rx="2"/>
      <text x="490" y="82" font-family="sans-serif" font-size="11" font-weight="bold" fill="#34D399">99.998%</text>

      <!-- Rule 5: DQ_VAL_002 -->
      <text x="0" y="104" font-family="monospace" font-size="10" fill="#94A3B8">DQ_VAL_002</text>
      <text x="90" y="104" font-family="sans-serif" font-size="11" fill="#E2E8F0">US State Jurisdiction (51)</text>
      <rect x="260" y="93" width="220" height="13" fill="#10B981" rx="2"/>
      <text x="490" y="104" font-family="sans-serif" font-size="11" font-weight="bold" fill="#34D399">99.998%</text>

      <!-- Rule 6: DQ_VAL_003 -->
      <text x="0" y="126" font-family="monospace" font-size="10" fill="#F59E0B">DQ_VAL_003</text>
      <text x="90" y="126" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">DTI [0,100] &amp; Rate [5,36]</text>
      <rect x="260" y="115" width="202" height="13" fill="#F59E0B" rx="2"/>
      <text x="490" y="126" font-family="sans-serif" font-size="11" font-weight="bold" fill="#FBBF24">99.852%</text>

      <!-- Rule 7: DQ_VAL_004 -->
      <text x="0" y="148" font-family="monospace" font-size="10" fill="#94A3B8">DQ_VAL_004</text>
      <text x="90" y="148" font-family="sans-serif" font-size="11" fill="#E2E8F0">Loan Amnt &amp; 36/60M Tenor</text>
      <rect x="260" y="137" width="220" height="13" fill="#10B981" rx="2"/>
      <text x="490" y="148" font-family="sans-serif" font-size="11" font-weight="bold" fill="#34D399">99.998%</text>

      <!-- Rule 8: DQ_VAL_005 -->
      <text x="0" y="170" font-family="monospace" font-size="10" fill="#94A3B8">DQ_VAL_005</text>
      <text x="90" y="170" font-family="sans-serif" font-size="11" fill="#E2E8F0">Issue Date MMM-yyyy Format</text>
      <rect x="260" y="159" width="220" height="13" fill="#10B981" rx="2"/>
      <text x="490" y="170" font-family="sans-serif" font-size="11" font-weight="bold" fill="#34D399">99.998%</text>

      <!-- Rule 9: DQ_VAL_006 -->
      <text x="0" y="192" font-family="monospace" font-size="10" fill="#94A3B8">DQ_VAL_006</text>
      <text x="90" y="192" font-family="sans-serif" font-size="11" fill="#E2E8F0">FICO Score Bounds [300,850]</text>
      <rect x="260" y="181" width="220" height="13" fill="#10B981" rx="2"/>
      <text x="490" y="192" font-family="sans-serif" font-size="11" font-weight="bold" fill="#34D399">99.998%</text>

      <!-- Rule 10: DQ_CNS_001 -->
      <text x="0" y="214" font-family="monospace" font-size="10" fill="#94A3B8">DQ_CNS_001</text>
      <text x="90" y="214" font-family="sans-serif" font-size="11" fill="#E2E8F0">Funded Amnt &lt;= Loan Amnt</text>
      <rect x="260" y="203" width="220" height="13" fill="#10B981" rx="2"/>
      <text x="490" y="214" font-family="sans-serif" font-size="11" font-weight="bold" fill="#34D399">99.998%</text>

      <!-- Rule 11: DQ_CNS_002 -->
      <text x="0" y="236" font-family="monospace" font-size="10" fill="#94A3B8">DQ_CNS_002</text>
      <text x="90" y="236" font-family="sans-serif" font-size="11" fill="#E2E8F0">UPB &lt;= Funded &amp; Terminal 0</text>
      <rect x="260" y="225" width="220" height="13" fill="#10B981" rx="2"/>
      <text x="490" y="236" font-family="sans-serif" font-size="11" font-weight="bold" fill="#34D399">99.998%</text>

      <!-- Rule 12: DQ_TIM_001 -->
      <text x="0" y="258" font-family="monospace" font-size="10" fill="#94A3B8">DQ_TIM_001</text>
      <text x="90" y="258" font-family="sans-serif" font-size="11" fill="#E2E8F0">Payment Chronology &amp; SLA</text>
      <rect x="260" y="247" width="220" height="13" fill="#10B981" rx="2"/>
      <text x="490" y="258" font-family="sans-serif" font-size="11" font-weight="bold" fill="#34D399">100.00%</text>
    </g>
  </g>

  <!-- ROW 3: REJECT TAXONOMY & OPERATIONAL SLA CONTRACT TABLE -->
  <g transform="translate(32, 600)" filter="url(#cardShadow)">
    <rect width="1535" height="270" rx="10" fill="url(#cardGrad)" stroke="#334155" stroke-width="1"/>
    <text x="24" y="26" font-family="sans-serif" font-size="14" font-weight="700" fill="#F8FAFC">Vendor Feed Service Level Agreement (SLA) &amp; Operational Exit Code Contract</text>
    <text x="24" y="42" font-family="sans-serif" font-size="11" fill="#64748B">SOP reference: docs/RUNBOOK.md • Automated notifications routed to reports/alerts/ upon breach</text>

    <!-- Table of 6 Gates -->
    <rect x="20" y="55" width="1495" height="26" fill="#0F172A" rx="4"/>
    <text x="35" y="72" font-family="sans-serif" font-size="11" font-weight="700" fill="#94A3B8">STAGE / GATE</text>
    <text x="170" y="72" font-family="sans-serif" font-size="11" font-weight="700" fill="#94A3B8">TRIGGER / CRITERIA</text>
    <text x="450" y="72" font-family="sans-serif" font-size="11" font-weight="700" fill="#94A3B8">EXIT CODE</text>
    <text x="560" y="72" font-family="sans-serif" font-size="11" font-weight="700" fill="#94A3B8">STATUS LABEL</text>
    <text x="730" y="72" font-family="sans-serif" font-size="11" font-weight="700" fill="#94A3B8">QUARANTINE DESTINATION</text>
    <text x="1050" y="72" font-family="sans-serif" font-size="11" font-weight="700" fill="#94A3B8">L1/L2 REMEDIATION PROTOCOL</text>

    <!-- Row 1: Checksum -->
    <g transform="translate(20, 88)">
      <text x="15" y="16" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">1. Checksum Gate</text>
      <text x="150" y="16" font-family="sans-serif" font-size="11" fill="#CBD5E1">sha256sum does not match manifest SHA256 (corrupt or truncated)</text>
      <text x="430" y="16" font-family="monospace" font-size="11" font-weight="bold" fill="#EF4444">Exit 11</text>
      <rect x="540" y="2" width="135" height="18" rx="4" fill="#450A0A"/><text x="607" y="15" font-family="sans-serif" font-size="10" font-weight="bold" fill="#F87171" text-anchor="middle">REJECTED_CHECKSUM</text>
      <text x="710" y="16" font-family="monospace" font-size="10" fill="#94A3B8">data/rejects/file_level/</text>
      <text x="1030" y="16" font-family="sans-serif" font-size="11" fill="#94A3B8">Quarantine drop; notify vendor to re-transmit intact file</text>
      <line x1="0" y1="24" x2="1495" y2="24" stroke="#1E293B"/>
    </g>

    <!-- Row 2: Rowcount -->
    <g transform="translate(20, 118)">
      <text x="15" y="16" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">2. Line Count Gate</text>
      <text x="150" y="16" font-family="sans-serif" font-size="11" fill="#CBD5E1">wc -l data rows != manifest EXPECTED_ROWS (valid SHA-256)</text>
      <text x="430" y="16" font-family="monospace" font-size="11" font-weight="bold" fill="#EF4444">Exit 12</text>
      <rect x="540" y="2" width="135" height="18" rx="4" fill="#450A0A"/><text x="607" y="15" font-family="sans-serif" font-size="10" font-weight="bold" fill="#F87171" text-anchor="middle">REJECTED_ROWCOUNT</text>
      <text x="710" y="16" font-family="monospace" font-size="10" fill="#94A3B8">data/rejects/file_level/</text>
      <text x="1030" y="16" font-family="sans-serif" font-size="11" fill="#94A3B8">Verify generator script; request revised manifest from servicer</text>
      <line x1="0" y1="24" x2="1495" y2="24" stroke="#1E293B"/>
    </g>

    <!-- Row 3: Header -->
    <g transform="translate(20, 148)">
      <text x="15" y="16" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">3. Header Schema Gate</text>
      <text x="150" y="16" font-family="sans-serif" font-size="11" fill="#CBD5E1">Column count != 30 or column names drift from expected_columns.txt</text>
      <text x="430" y="16" font-family="monospace" font-size="11" font-weight="bold" fill="#EF4444">Exit 13</text>
      <rect x="540" y="2" width="135" height="18" rx="4" fill="#450A0A"/><text x="607" y="15" font-family="sans-serif" font-size="10" font-weight="bold" fill="#F87171" text-anchor="middle">REJECTED_HEADER</text>
      <text x="710" y="16" font-family="monospace" font-size="10" fill="#94A3B8">data/rejects/file_level/</text>
      <text x="1030" y="16" font-family="sans-serif" font-size="11" fill="#94A3B8">Raise upstream change ticket; block until schema alignment is agreed</text>
      <line x1="0" y1="24" x2="1495" y2="24" stroke="#1E293B"/>
    </g>

    <!-- Row 4: DQ Threshold -->
    <g transform="translate(20, 178)">
      <text x="15" y="16" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">4. Batch DQ Threshold</text>
      <text x="150" y="16" font-family="sans-serif" font-size="11" fill="#CBD5E1">PySpark row-level failure rate exceeds MAX_REJECT_PCT (5.0%)</text>
      <text x="430" y="16" font-family="monospace" font-size="11" font-weight="bold" fill="#EF4444">Exit 20</text>
      <rect x="540" y="2" width="155" height="18" rx="4" fill="#450A0A"/><text x="617" y="15" font-family="sans-serif" font-size="10" font-weight="bold" fill="#F87171" text-anchor="middle">REJECTED_DQ_THRESHOLD</text>
      <text x="710" y="16" font-family="monospace" font-size="10" fill="#94A3B8">data/rejects/file_level/</text>
      <text x="1030" y="16" font-family="sans-serif" font-size="11" fill="#94A3B8">Inspect scorecard; sample reason codes; escalate to vendor steward</text>
      <line x1="0" y1="24" x2="1495" y2="24" stroke="#1E293B"/>
    </g>

    <!-- Row 5: Arrival Cutoff -->
    <g transform="translate(20, 208)">
      <text x="15" y="16" font-family="sans-serif" font-size="11" font-weight="bold" fill="#F8FAFC">5. SLA Arrival Gate</text>
      <text x="150" y="16" font-family="sans-serif" font-size="11" fill="#CBD5E1">Feed file missing at 06:30 IST cron trigger (or arrival mtime &gt; 06:30 IST)</text>
      <text x="430" y="16" font-family="monospace" font-size="11" font-weight="bold" fill="#F59E0B">Exit 10 / 0</text>
      <rect x="540" y="2" width="135" height="18" rx="4" fill="#451A03"/><text x="607" y="15" font-family="sans-serif" font-size="10" font-weight="bold" fill="#F59E0B" text-anchor="middle">MISSING / LATE</text>
      <text x="710" y="16" font-family="monospace" font-size="10" fill="#94A3B8">reports/alerts/</text>
      <text x="1030" y="16" font-family="sans-serif" font-size="11" fill="#94A3B8">P2 escalation at 06:45 IST; ingest with LATE flag once landed</text>
    </g>
  </g>
</svg>"""


def main():
    p1 = OUT_DIR / "01_executive_portfolio_risk.svg"
    p2 = OUT_DIR / "02_vintage_delinquency_chargeoff.svg"
    p3 = OUT_DIR / "03_dq_governance_vendor_sla.svg"
    
    p1.write_text(xml_escape(create_page_1()), encoding="utf-8")
    p2.write_text(xml_escape(create_page_2()), encoding="utf-8")
    p3.write_text(xml_escape(create_page_3()), encoding="utf-8")
    
    print(f"Generated {p1} ({p1.stat().st_size:,} bytes)")
    print(f"Generated {p2} ({p2.stat().st_size:,} bytes)")
    print(f"Generated {p3} ({p3.stat().st_size:,} bytes)")

if __name__ == "__main__":
    main()
