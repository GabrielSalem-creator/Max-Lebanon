import math

GM = 3.986e14
g0 = 9.81
r1 = 6.371e6 + 400e3  # LEO
r2 = 3.844e8           # Moon distance

v_esc_LEO = math.sqrt(2 * GM / r1)
v_LEO = math.sqrt(GM / r1)

# Hohmann (baseline - minimum energy, SLOWEST)
a_hoh = (r1 + r2) / 2
v_TLI_hoh = math.sqrt(GM * (2/r1 - 1/a_hoh))
dv_hoh = v_TLI_hoh - v_LEO
T_hoh = math.pi * math.sqrt(a_hoh**3 / GM) / 86400

# Fast transfers - different energy levels
# For a transfer that hits r2 with semi-major axis a > a_hoh:
# Time to reach r2 along that orbit is less than half-period

def fast_transfer_time(dv_extra_km):
    """Extra delta-v in km/s on top of escape velocity gives hyperbolic departure"""
    v_dep = v_LEO + (dv_hoh + dv_extra_km*1000)
    # Energy
    E = 0.5 * v_dep**2 - GM/r1
    a = -GM / (2*E)  # negative for hyperbola, positive for ellipse
    if a > 0:
        # Still elliptical - use eccentric anomaly to find time to reach r2
        e = 1 - r1/a  # perigee condition
        if r2 <= a*(1+e):  # can reach r2
            cos_nu2 = (a*(1-e**2)/r2 - 1) / e
            if abs(cos_nu2) <= 1:
                nu2 = math.acos(cos_nu2)
                E2 = 2 * math.atan(math.sqrt((1-e)/(1+e)) * math.tan(nu2/2))
                if E2 < 0:
                    E2 += 2*math.pi
                t = math.sqrt(a**3/GM) * (E2 - e*math.sin(E2))
                return t/3600, a, e, v_dep
    return None, a, 0, v_dep

print("=== FAST LUNAR TRAJECTORIES WITH NUCLEAR PROPULSION ===")
print(f"Hohmann (minimum energy): {T_hoh*24:.1f} hours = {T_hoh:.2f} days | delta-v: {dv_hoh/1000:.2f} km/s")
print()

for extra in [0.3, 0.6, 1.0, 1.5, 2.0, 3.0]:
    result, a, e, v_dep = fast_transfer_time(extra)
    total_dv = dv_hoh/1000 + extra
    Isp_c, Isp_n = 450, 900
    mr_c = math.exp(total_dv*1000 / (Isp_c * g0))
    mr_n = math.exp(total_dv*1000 / (Isp_n * g0))

    if result:
        print(f"Extra burn +{extra} km/s | Total TLI: {total_dv:.2f} km/s | Time: {result:.1f} hours = {result/24:.2f} days")
        print(f"  Chemical propellant (Isp 450): {(mr_c-1)*1000:.0f} kg per 1000 kg payload → BARELY POSSIBLE" if mr_c < 5 else f"  Chemical propellant (Isp 450): {(mr_c-1)*1000:.0f} kg → IMPRACTICAL ({mr_c:.1f}x payload)")
        print(f"  Nuclear thermal (Isp 900):     {(mr_n-1)*1000:.0f} kg per 1000 kg payload → FEASIBLE" if mr_n < 3 else f"  Nuclear thermal (Isp 900):     {(mr_n-1)*1000:.0f} kg per 1000 kg payload")
        print()

# Brachistochrone - constant acceleration
print("=== CONSTANT THRUST (BRACHISTOCHRONE) - NUCLEAR ONLY ===")
print("Accelerate halfway, flip and decelerate. Shortest possible trip time.")
for accel_g in [0.05, 0.1, 0.2, 0.3]:
    a = accel_g * g0
    half_dist = r2 / 2
    t_half = math.sqrt(2 * half_dist / a)
    t_total = 2 * t_half
    v_peak = a * t_half
    total_dv = 2 * v_peak
    mr_n = math.exp(total_dv / (900 * g0))
    print(f"Accel {accel_g}g: trip time {t_total/3600:.1f} hours | peak speed {v_peak/1000:.1f} km/s | nuclear mass ratio {mr_n:.1f}x")
