#!/usr/bin/env python3
"""Deterministic first-order Earth-to-LEO cargo architecture envelope model.

Scope:
- two-body Earth gravity;
- rotating atmosphere;
- U.S. Standard Atmosphere 1976 layer equations to 84.852 km, exponential tail above;
- constant ballistic coefficient drag;
- Sutton-Graves stagnation-point convective heating;
- accelerator kinematics and throughput/power scaling.

This is an architecture-envelope model, not CFD, TPS certification, guidance design,
electromagnetic launcher detailed design, or a claim of demonstrated system performance.
"""
from __future__ import annotations
import argparse
import json
import math

MU = 3.986004418e14
R_EARTH = 6_371_000.0
R_GEOPOTENTIAL = 6_356_766.0
OMEGA_EARTH = 7.2921159e-5
G0 = 9.80665
R_AIR = 287.05287
SUTTON_GRAVES_EARTH = 1.74153e-4
SECONDS_PER_YEAR = 365.25 * 24.0 * 3600.0

BASE_H = (0.0, 11000.0, 20000.0, 32000.0, 47000.0, 51000.0, 71000.0, 84852.0)
LAPSE = (-0.0065, 0.0, 0.0010, 0.0028, 0.0, -0.0028, -0.0020)

def _base_state():
    temps = [288.15]
    pressures = [101325.0]
    for i, lapse in enumerate(LAPSE):
        hb, hn = BASE_H[i], BASE_H[i + 1]
        tb, pb = temps[i], pressures[i]
        if lapse == 0.0:
            tn = tb
            pn = pb * math.exp(-G0 * (hn - hb) / (R_AIR * tb))
        else:
            tn = tb + lapse * (hn - hb)
            pn = pb * (tn / tb) ** (-G0 / (R_AIR * lapse))
        temps.append(tn)
        pressures.append(pn)
    return tuple(temps), tuple(pressures)

BASE_T, BASE_P = _base_state()

def atmosphere(geometric_altitude_m: float):
    h = max(0.0, geometric_altitude_m)
    H = R_GEOPOTENTIAL * h / (R_GEOPOTENTIAL + h)
    if H >= BASE_H[-1]:
        t = BASE_T[-1]
        p = BASE_P[-1] * math.exp(-G0 * (H - BASE_H[-1]) / (R_AIR * t))
        return p / (R_AIR * t), t, p
    i = max(j for j in range(len(BASE_H) - 1) if H >= BASE_H[j])
    hb, tb, pb, lapse = BASE_H[i], BASE_T[i], BASE_P[i], LAPSE[i]
    if lapse == 0.0:
        t = tb
        p = pb * math.exp(-G0 * (H - hb) / (R_AIR * tb))
    else:
        t = tb + lapse * (H - hb)
        p = pb * (t / tb) ** (-G0 / (R_AIR * lapse))
    return p / (R_AIR * t), t, p

def ideal_tangential_orbit(release_altitude_m: float, apogee_altitude_m: float):
    rp = R_EARTH + release_altitude_m
    ra = R_EARTH + apogee_altitude_m
    a = 0.5 * (rp + ra)
    vp = math.sqrt(MU * (2.0 / rp - 1.0 / a))
    va = math.sqrt(MU * (2.0 / ra - 1.0 / a))
    vc = math.sqrt(MU / ra)
    rotation = OMEGA_EARTH * rp
    return {
        "perigee_inertial_speed_m_s": vp,
        "equatorial_rotation_m_s": rotation,
        "required_ground_relative_tangential_speed_m_s": vp - rotation,
        "ideal_apogee_circularization_delta_v_m_s": vc - va,
    }

def _derivative(state, beta):
    x, y, vx, vy = state
    r = math.hypot(x, y)
    rho, _, _ = atmosphere(r - R_EARTH)
    ax = -MU * x / r**3
    ay = -MU * y / r**3
    air_vx, air_vy = -OMEGA_EARTH * y, OMEGA_EARTH * x
    rel_vx, rel_vy = vx - air_vx, vy - air_vy
    rel_v = math.hypot(rel_vx, rel_vy)
    if rel_v > 0.0 and rho > 0.0:
        drag = 0.5 * rho * rel_v * rel_v / beta
        ax -= drag * rel_vx / rel_v
        ay -= drag * rel_vy / rel_v
    return vx, vy, ax, ay

def _rk4(state, dt, beta):
    k1 = _derivative(state, beta)
    s2 = tuple(state[i] + 0.5 * dt * k1[i] for i in range(4))
    k2 = _derivative(s2, beta)
    s3 = tuple(state[i] + 0.5 * dt * k2[i] for i in range(4))
    k3 = _derivative(s3, beta)
    s4 = tuple(state[i] + dt * k3[i] for i in range(4))
    k4 = _derivative(s4, beta)
    return tuple(state[i] + dt * (k1[i] + 2*k2[i] + 2*k3[i] + k4[i]) / 6.0 for i in range(4))

def trajectory(exit_altitude_m, ground_relative_speed_m_s, flight_path_angle_deg,
               ballistic_coefficient_kg_m2, nose_radius_m, dt_s=0.05, max_time_s=5000.0):
    r0 = R_EARTH + exit_altitude_m
    gamma = math.radians(flight_path_angle_deg)
    vrot = OMEGA_EARTH * r0
    state = (
        r0,
        0.0,
        ground_relative_speed_m_s * math.sin(gamma),
        ground_relative_speed_m_s * math.cos(gamma) + vrot,
    )
    previous_radial = None
    peak_q = peak_heat = peak_drag = heat_load = 0.0
    elapsed = 0.0
    apogee_state = None

    while elapsed < max_time_s:
        x, y, vx, vy = state
        r = math.hypot(x, y)
        h = r - R_EARTH
        rho, _, _ = atmosphere(h)
        air_vx, air_vy = -OMEGA_EARTH * y, OMEGA_EARTH * x
        rel_vx, rel_vy = vx - air_vx, vy - air_vy
        rel_v = math.hypot(rel_vx, rel_vy)
        q = 0.5 * rho * rel_v**2
        heat = SUTTON_GRAVES_EARTH * math.sqrt(max(rho, 0.0) / nose_radius_m) * rel_v**3
        drag = q / ballistic_coefficient_kg_m2
        peak_q = max(peak_q, q)
        peak_heat = max(peak_heat, heat)
        peak_drag = max(peak_drag, drag)
        heat_load += heat * dt_s
        radial = (x * vx + y * vy) / r

        if previous_radial is not None and previous_radial > 0.0 and radial <= 0.0 and h > exit_altitude_m + 1000.0:
            apogee_state = state
            break
        previous_radial = radial
        state = _rk4(state, dt_s, ballistic_coefficient_kg_m2)
        elapsed += dt_s

    if apogee_state is None:
        raise RuntimeError("Apogee not reached before max_time_s")

    x, y, vx, vy = apogee_state
    r = math.hypot(x, y)
    h = r - R_EARTH
    er = (x / r, y / r)
    et = (-y / r, x / r)
    radial_v = vx * er[0] + vy * er[1]
    tangential_v = vx * et[0] + vy * et[1]
    circular_v = math.sqrt(MU / r)
    circularization = math.hypot(radial_v, circular_v - tangential_v)

    return {
        "apogee_altitude_km": h / 1000.0,
        "apogee_circularization_delta_v_m_s": circularization,
        "peak_dynamic_pressure_MPa": peak_q / 1e6,
        "peak_drag_g": peak_drag / G0,
        "peak_convective_heat_kW_cm2": peak_heat / 1e7,
        "integrated_convective_heat_MJ_cm2": heat_load / 1e10,
        "time_to_apogee_s": elapsed,
    }

def accelerator_and_throughput(payload_mass_kg, gross_mass_kg, ground_relative_speed_m_s,
                               acceleration_g, throughput_tonnes_year, electrical_efficiency):
    acceleration = acceleration_g * G0
    track_length = ground_relative_speed_m_s**2 / (2.0 * acceleration)
    acceleration_time = ground_relative_speed_m_s / acceleration
    force = gross_mass_kg * acceleration
    peak_mechanical_power = force * ground_relative_speed_m_s

    shots_per_year = throughput_tonnes_year * 1000.0 / payload_mass_kg
    launch_interval = SECONDS_PER_YEAR / shots_per_year
    gross_mass_flow = throughput_tonnes_year * 1000.0 / SECONDS_PER_YEAR * (gross_mass_kg / payload_mass_kg)
    avg_mechanical_power = 0.5 * gross_mass_flow * ground_relative_speed_m_s**2
    avg_electrical_power = avg_mechanical_power / electrical_efficiency

    return {
        "track_length_km": track_length / 1000.0,
        "acceleration_time_s": acceleration_time,
        "pod_force_MN": force / 1e6,
        "peak_mechanical_power_GW": peak_mechanical_power / 1e9,
        "mechanical_energy_per_shot_TJ": 0.5 * gross_mass_kg * ground_relative_speed_m_s**2 / 1e12,
        "shots_per_day": shots_per_year / 365.25,
        "launch_interval_s": launch_interval,
        "average_pods_in_accelerator": acceleration_time / launch_interval,
        "average_mechanical_power_GW": avg_mechanical_power / 1e9,
        "average_electrical_power_GW": avg_electrical_power / 1e9,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload-t", type=float, required=True)
    ap.add_argument("--gross-t", type=float, required=True)
    ap.add_argument("--diameter-m", type=float, required=True)
    ap.add_argument("--cd", type=float, required=True)
    ap.add_argument("--nose-radius-m", type=float, required=True)
    ap.add_argument("--exit-alt-km", type=float, required=True)
    ap.add_argument("--exit-speed-kms", type=float, required=True, help="Ground/atmosphere-relative speed")
    ap.add_argument("--angle-deg", type=float, required=True)
    ap.add_argument("--accel-g", type=float, required=True)
    ap.add_argument("--throughput-mtpy", type=float, required=True, help="Million payload tonnes/year")
    ap.add_argument("--electrical-efficiency", type=float, default=0.70)
    args = ap.parse_args()

    payload = args.payload_t * 1000.0
    gross = args.gross_t * 1000.0
    area = math.pi * args.diameter_m**2 / 4.0
    beta = gross / (args.cd * area)
    speed = args.exit_speed_kms * 1000.0
    result = {
        "inputs": vars(args),
        "ballistic_coefficient_kg_m2": beta,
        "ideal_400km_tangential_reference": ideal_tangential_orbit(args.exit_alt_km*1000.0, 400000.0),
        "trajectory": trajectory(args.exit_alt_km*1000.0, speed, args.angle_deg, beta, args.nose_radius_m),
        "accelerator_throughput": accelerator_and_throughput(
            payload, gross, speed, args.accel_g, args.throughput_mtpy*1e6, args.electrical_efficiency
        ),
        "scope_warning": "First-order architecture envelope only. Constant Cd/beta, point mass, no lift, no detailed shock/CFD/TPS/launcher electromagnetic design."
    }
    print(json.dumps(result, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
