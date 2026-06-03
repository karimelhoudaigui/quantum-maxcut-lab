import numpy as np

from pulser import Pulse, Sequence
from pulser.devices import MockDevice
from pulser.waveforms import ConstantWaveform, RampWaveform

from .pulser_core import build_xy_register


def build_xy_adiabatic_sequence(
    positions,
    omega_prep,
    prep_duration,
    omega_hold,
    hold_duration,
    omega_max,
    ramp_up_duration,
    anneal_duration,
    scale=15.5,
):
    reg = build_xy_register(positions, scale=scale)

    seq = Sequence(reg, MockDevice)
    seq.declare_channel("mw", "mw_global")

    prep_pulse = Pulse.ConstantPulse(
        duration=int(prep_duration),
        amplitude=float(omega_prep),
        detuning=0.0,
        phase=np.pi / 2,
    )
    seq.add(prep_pulse, "mw")

    if ramp_up_duration > 0:
        amp_up = RampWaveform(int(ramp_up_duration), 0.0, float(omega_max))
        det_up = ConstantWaveform(int(ramp_up_duration), 0.0)
        seq.add(Pulse(amp_up, det_up, phase=0.0), "mw")

    if hold_duration > 0:
        hold_pulse = Pulse.ConstantPulse(
            duration=int(hold_duration),
            amplitude=float(omega_hold),
            detuning=0.0,
            phase=0.0,
        )
        seq.add(hold_pulse, "mw")

    if anneal_duration > 0:
        amp_down = RampWaveform(int(anneal_duration), float(omega_max), 0.0)
        det_down = ConstantWaveform(int(anneal_duration), 0.0)
        seq.add(Pulse(amp_down, det_down, phase=0.0), "mw")

    seq.measure("XY")
    return seq


def build_xy_annealing_sequence(positions, omega_max, T):
    reg = build_xy_register(positions)

    seq = Sequence(reg, MockDevice)
    seq.declare_channel("mw", "mw_global")

    half_T = int(T // 2)

    amp_up = RampWaveform(half_T, 0.0, omega_max)
    amp_down = RampWaveform(T - half_T, omega_max, 0.0)

    det_up = ConstantWaveform(half_T, 0.0)
    det_down = ConstantWaveform(T - half_T, 0.0)

    seq.add(Pulse(amp_up, det_up, phase=0.0), "mw")
    seq.add(Pulse(amp_down, det_down, phase=0.0), "mw")

    seq.measure("XY")
    return seq


def build_xy_piecewise_sequence(positions, pulse_params, pulse_duration=250):
    reg = build_xy_register(positions)

    seq = Sequence(reg, MockDevice)
    seq.declare_channel("mw", "mw_global")

    pulse_params = np.asarray(pulse_params, dtype=float)
    assert len(pulse_params) % 3 == 0

    n_pulses = len(pulse_params) // 3
    for k in range(n_pulses):
        amp = float(pulse_params[3 * k + 0])
        det = float(pulse_params[3 * k + 1])
        phase = float(pulse_params[3 * k + 2])

        pulse = Pulse.ConstantPulse(
            duration=int(pulse_duration),
            amplitude=amp,
            detuning=det,
            phase=phase,
        )
        seq.add(pulse, "mw")

    seq.measure("XY")
    return seq
