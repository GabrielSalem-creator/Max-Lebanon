import math

GM = 3.986e14
g0 = 9.81
r1 = 6.371e6 + 400e3
r2 = 3.844e8

v_LEO = math.sqrt(GM / r1)
a_t = (r1 + r2) / 2
v_TLI = math.sqrt(GM * (2/r1 - 1/a_t))
dv_TLI = v_TLI - v_LEO
T = math.pi * math.sqrt(a_t**3 / GM) / 86400

Isp_c, Isp_n = 450, 900
dv_space = dv_TLI + 1000
mr_c = math.exp(dv_space / (Isp_c * g0))
mr_n = math.exp(dv_space / (Isp_n * g0))

energy_U235 = (6.022e23 / 0.235) * 200e6 * 1.6e-19
thrust_NERVA = 111000
mass_flow = thrust_NERVA / (Isp_n * g0)
total_dv = 9400 + dv_TLI + 1000 + 1700

print("LEO velocity: " + str(round(v_LEO/1000, 2)) + " km/s")
print("TLI burn delta-v: " + str(round(dv_TLI/1000, 2)) + " km/s")
print("Transfer time: " + str(round(T, 2)) + " days")
print("Total mission delta-v (Earth surface to Moon surface): " + str(round(total_dv)) + " m/s = " + str(round(total_dv/1000, 1)) + " km/s")
print("")
print("--- ROCKET EQUATION COMPARISON ---")
print("Chemical rocket mass ratio: " + str(round(mr_c, 3)))
print("  For 1000 kg payload: " + str(round((mr_c-1)*1000)) + " kg propellant needed")
print("Nuclear thermal mass ratio: " + str(round(mr_n, 3)))
print("  For 1000 kg payload: " + str(round((mr_n-1)*1000)) + " kg propellant needed")
print("Nuclear saves: " + str(round(((mr_c - mr_n) / (mr_c-1)) * 100, 1)) + "% propellant mass")
print("")
print("--- NUCLEAR ENERGY ---")
print("Energy in 1 kg U-235: " + str(round(energy_U235/1e12, 0)) + " terajoules")
print("Equivalent TNT: " + str(round(energy_U235/4.2e9)) + " tonnes")
print("NERVA engine thrust: 111 kN")
print("NERVA propellant flow rate: " + str(round(mass_flow, 2)) + " kg/s of liquid hydrogen")
print("Burn time for 1000 kg H2: " + str(round(1000/mass_flow, 0)) + " seconds")
