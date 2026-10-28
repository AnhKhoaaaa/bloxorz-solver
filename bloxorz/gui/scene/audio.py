"""Procedural 16-bit PCM WAV Audio Synthesizer using Python's standard `wave`, `struct`, and `math`."""
from __future__ import annotations

import io
import math
import os
import random
import shutil
import struct
import subprocess
import tempfile
import threading
import wave


class ProceduralAudioEngine:
    """Synthesizes and plays Minecraft-inspired 16-bit PCM WAV sound effects procedurally.

    Generates four primary sound profiles required by the specification:
    1. `step`: Crisp wood-on-stone percussive thud when the Oak Log rolls.
    2. `switch`: Sharp mechanical Redstone pressure-plate click.
    3. `fall`: Low rushing wind / tumbling pitch sweep when falling into the void.
    4. `win`: Radiant harmonic arpeggio fanfare (C5 -> E5 -> G5 -> C6) on End Portal entry.
    """

    SAMPLE_RATE = 22050

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._wav_bytes: dict[str, bytes] = {}
        self._wav_files: dict[str, str] = {}
        self._temp_dir = tempfile.mkdtemp(prefix="bloxorz_sfx_")
        self._candidate_players: list[list[str]] = self._detect_candidates()
        self._working_player: list[str] | None = None
        self._prebuild_all()

    @staticmethod
    def _detect_candidates() -> list[list[str]]:
        """Detect lightweight native audio players in priority order."""
        candidates = []
        for binary, args in (
            ("pw-play", ["pw-play"]),
            ("paplay", ["paplay"]),
            ("aplay", ["aplay", "-q"]),
            ("ffplay", ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]),
        ):
            if shutil.which(binary):
                candidates.append(args)
        return candidates

    @classmethod
    def _pack_wav(cls, samples: list[float]) -> bytes:
        """Encode normalized [-1.0, 1.0] float samples into a 16-bit mono PCM WAV byte buffer."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit signed integer PCM
            wf.setframerate(cls.SAMPLE_RATE)
            clamped = [max(-32767, min(32767, int(s * 32767.0))) for s in samples]
            wf.writeframes(struct.pack(f"<{len(clamped)}h", *clamped))
        return buf.getvalue()

    def _prebuild_all(self) -> None:
        """Synthesize all procedural sound effects upfront."""
        rng = random.Random(42)
        sr = self.SAMPLE_RATE

        # 1. Wood/Stone Step (0.095s): Percussive oak thump + crisp stone transient click
        n_step = int(sr * 0.095)
        step_samples: list[float] = []
        for i in range(n_step):
            t = i / sr
            env = math.exp(-t * 42.0)
            freq = 148.0 * math.exp(-t * 14.0) + 52.0
            wood_body = math.sin(2.0 * math.pi * freq * t)
            stone_click = (rng.uniform(-1.0, 1.0) * math.exp(-t * 110.0)) * 0.55
            step_samples.append((wood_body * 0.65 + stone_click) * env * 0.55)
        self._register("step", step_samples)

        # 2. Mechanical Pressure Plate Switch Click (0.085s): Dual-transient Redstone click
        n_sw = int(sr * 0.085)
        sw_samples: list[float] = []
        for i in range(n_sw):
            t = i / sr
            click1 = math.sin(2.0 * math.pi * 1180.0 * t) * math.exp(-t * 95.0)
            t2 = max(0.0, t - 0.024)
            click2 = (
                math.sin(2.0 * math.pi * 1680.0 * t2) * math.exp(-t2 * 85.0)
                if t >= 0.024
                else 0.0
            )
            metallic = rng.uniform(-0.3, 0.3) * math.exp(-t * 120.0)
            sw_samples.append((click1 * 0.6 + click2 * 0.7 + metallic) * 0.55)
        self._register("switch", sw_samples)

        # 3. Void Fall Wind & Pitch Drop (0.55s): Descending resonant sweep + rushing wind noise
        n_fall = int(sr * 0.55)
        fall_samples: list[float] = []
        phase = 0.0
        lp_noise = 0.0
        for i in range(n_fall):
            t = i / sr
            env = math.sin(min(1.0, t / 0.06) * (math.pi / 2.0)) * math.exp(-t * 3.8)
            freq = 310.0 * math.exp(-t * 3.2) + 42.0
            phase += 2.0 * math.pi * freq / sr
            raw_noise = rng.uniform(-1.0, 1.0)
            lp_noise = 0.88 * lp_noise + 0.12 * raw_noise
            sample = (0.48 * math.sin(phase) + 0.52 * lp_noise) * env * 0.5
            fall_samples.append(sample)
        self._register("fall", fall_samples)

        # 4. Victory End Portal Fanfare Chime (0.85s): C5 - E5 - G5 - B5 - C6 shimmering chord
        n_win = int(sr * 0.85)
        win_samples: list[float] = []
        notes = [
            (0.00, 523.25),  # C5
            (0.09, 659.25),  # E5
            (0.18, 783.99),  # G5
            (0.27, 987.77),  # B5
            (0.36, 1046.50),  # C6
        ]
        for i in range(n_win):
            t = i / sr
            acc = 0.0
            for onset, freq in notes:
                if t >= onset:
                    dt = t - onset
                    env = math.exp(-dt * 4.5) * (1.0 - math.exp(-dt * 120.0))
                    # Fundamental + 2nd & 3rd crystal harmonics
                    tone = (
                        0.65 * math.sin(2.0 * math.pi * freq * dt)
                        + 0.25 * math.sin(2.0 * math.pi * (freq * 2.0) * dt)
                        + 0.10 * math.sin(2.0 * math.pi * (freq * 3.0) * dt)
                    )
                    acc += tone * env
            win_samples.append(acc * 0.26)
        self._register("win", win_samples)

    def _register(self, name: str, samples: list[float]) -> None:
        wav_data = self._pack_wav(samples)
        self._wav_bytes[name] = wav_data
        file_path = os.path.join(self._temp_dir, f"{name}.wav")
        try:
            with open(file_path, "wb") as f:
                f.write(wav_data)
            self._wav_files[name] = file_path
        except OSError:
            pass

    def get_wav_bytes(self, name: str) -> bytes:
        """Return raw 16-bit PCM WAV bytes for inspection or testing."""
        return self._wav_bytes.get(name, b"")

    def play(self, name: str) -> None:
        """Play a synthesized sound effect asynchronously without blocking the 60 FPS loop."""
        if not self.enabled or name not in self._wav_files or not self._candidate_players:
            return
        filepath = self._wav_files[name]

        def _worker() -> None:
            # If a known working player is cached, attempt playback first
            if self._working_player is not None:
                try:
                    res = subprocess.run(
                        [*self._working_player, filepath],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=1.5,
                        check=False,
                    )
                    if res.returncode == 0:
                        return
                except Exception:
                    pass
                self._working_player = None

            # Fallback across candidate players until one succeeds
            for cand in self._candidate_players:
                try:
                    res = subprocess.run(
                        [*cand, filepath],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=1.5,
                        check=False,
                    )
                    if res.returncode == 0:
                        self._working_player = cand
                        return
                except Exception:
                    continue

        threading.Thread(target=_worker, daemon=True).start()

    def play_step(self) -> None:
        self.play("step")

    def play_switch(self) -> None:
        self.play("switch")

    def play_fall(self) -> None:
        self.play("fall")

    def play_win(self) -> None:
        self.play("win")
