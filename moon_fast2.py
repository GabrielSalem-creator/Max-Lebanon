import math

GM = 3.986e14
g0 = 9.81
r1 = 6.371e6 + 400e3
r2 = 3.844e8

v_LEO = math.sqrt(GM / r1)
v_esc = math.sqrt(2 * GM / r1)

def time_to_moon_hyperbolic(v_dep):
    """Time to reach Moon distance on hyperbolic trajectory from LEO"""
    E = 0.5 * v_dep**2 - GM/r1
    if E <= 0:
        return None  # elliptical, use other method
    a = GM / (2*E)   # semi-major axis of hyperbola (positive)
    e = 1 + r1/a     # eccentricity
    # r = a(e*cosh(H) - 1)
    # Solve: a(e*cosh(H) - 1) = r2
    arg = (r2/a + 1) / e
    if arg < 1:
        return None
    H = math.log(arg + math.sqrt(arg**2 - 1))  # arccosh
    t = math.sqrt(a**3/GM) * (e*math.sinh(H) - H)
    return t/3600  # hours

def time_to_moon_elliptical(v_dep):
    """Time to reach Moon distance on elliptical trajectory (sub-escape)"""
    E = 0.5 * v_dep**2 - GM/r1
    if E >= 0:
        return None  # hyperbolic
    a = -GM / (2*E)  # semi-major axis (positive)
    e = 1 - r1/a     # eccentricity (perigee at r1, e>0 means r1 is periapsis)
    if r2 > a*(1+e):
        return None  # can't reach Moon on this orbit
    cos_nu = (a*(1-e**2)/r2 - 1)/e
    if abs(cos_nu) > 1:
        return None
    nu = math.acos(cos_nu)
    E_anom = 2*math.atan(math.sqrt((1-e)/(1+e)) * math.tan(nu/2))
    if E_anom < 0:
        E_anom += 2*math.pi
    t = math.sqrt(a**3/GM) * (E_anom - e*math.sin(E_anom))
    return t/3600

print("=== NUCLEAR vs CHEMICAL — WHAT NUCLEAR ACTUALLY BUYS YOU ===")
print()
print("Chemical stuck at Hohmann because more delta-v = impossible mass ratios.")
print("Nuclear can AFFORD to burn harder. Here's what that means:")
print()

Isp_c = 450
Isp_n = 900

print(f"{'Delta-v (TLI)':>15} | {'Trip time':>12} | {'Chemical mass ratio':>20} | {'Nuclear mass ratio':>18} | {'Chemical feasible?':>18}")
print("-"*95)

# Hohmann baseline
a_hoh = (r1+r2)/2
v_TLI_hoh = math.sqrt(GM*(2/r1 - 1/a_hoh))
dv_hoh = v_TLI_hoh - v_LEO

dv_tests = [dv_hoh, dv_hoh+500, dv_hoh+1000, dv_hoh+1500, dv_hoh+2000, dv_hoh+3000]

for dv in dv_tests:
    v_dep = v_LEO + dv
    if v_dep < v_esc:
        t = time_to_moon_elliptical(v_dep)
    else:
        t = time_to_moon_hyperbolic(v_dep)

    if t is None:
        continue

    # Include LOI delta-v of 1 km/s for full mission leg
    total_dv = dv + 1000
    mr_c = math.exp(total_dv / (Isp_c * g0))
    mr_n = math.exp(total_dv / (Isp_n * g0))
    feasible_c = "YES" if mr_c < 4 else ("HARD" if mr_c < 8 else "NO")
    feasible_n = "YES" if mr_n < 4 else "HARD"

    print(f"{dv/1000:>13.2f} km/s | {t:>9.1f} hrs | {mr_c:>18.2f}x | {mr_n:>16.2f}x | {feasible_c:>10} | Nuclear: {feasible_n}")

print()
print("=== BOTTOM LINE ===")
print()
print("Nuclear (Isp 900s) vs Chemical (Isp 450s) for a 2-day trip:")
dv_2day = dv_hoh + 1500  # roughly enough for ~2 day trip
total_2day = dv_2day + 1000
mr_c_2day = math.exp(total_2day / (Isp_c * g0))
mr_n_2day = math.exp(total_2day / (Isp_n * g0))
print(f"Chemical needs {mr_c_2day:.1f}x propellant = {(mr_c_2day-1)*10000:.0f} kg propellant for 10-tonne spacecraft")
print(f"Nuclear needs  {mr_n_2day:.1f}x propellant = {(mr_n_2day-1)*10000:.0f} kg propellant for 10-tonne spacecraft")
print(f"Nuclear saves {(1 - (mr_n_2day-1)/(mr_c_2day-1))*100:.0f}% of the propellant mass on the FAST path")
