"""Yer istasyonu penceresi: yapay ufuk, sayisal paneller, komut butonlari."""

import math
import time
import tkinter as tk
from tkinter import messagebox, ttk

from . import attitude, link

REFRESH_MS = 100
LINK_STALE_MS = 3000
CALIBRATION_TIMEOUT_MS = 5000
DISARM_TIMEOUT_MS = 3000
PORT_RESCAN_MS = 2000

HORIZON_SIZE = 320
HORIZON_RADIUS = 140
PIXELS_PER_DEGREE = 3.0

BG = "#101418"
FG = "#e6edf3"
DIM = "#6b7885"
SKY = "#2f7fd1"
GROUND = "#8a5a2b"
PLANE = "#ffd24a"


class NavStationWindow:
    def __init__(self, baud: int = 115200, initial_port: str | None = None):
        # Baglanti yasam dongusu pencerenin: bagla/kes operatorun elinde.
        self.link: link.SerialLink | None = None
        self.baud = baud
        self.initial_port = initial_port
        self.port_names: list[str] = []
        self.reference_pa: int | None = None
        self.calibration_deadline_ms: int | None = None
        self.calibration_baseline_flags: int = 0
        self.pending_calibration: str | None = None
        self.disarm_deadline_ms: int | None = None
        self.disarm_baseline_rx: int | None = None
        self.last_rx_count: int | None = None
        self.last_packet_wall_time: float | None = None

        self.root = tk.Tk()
        self.root.title("ISO U1 — Yer Istasyonu")
        self.root.configure(bg=BG)

        self._build_layout()

    # -- kurulum ----------------------------------------------------------

    def _build_layout(self) -> None:
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=12, pady=12)

        self.left = self._make_panel(body, "UCUS")
        self.left.pack(side="left", fill="y", padx=(0, 12))

        self.canvas = tk.Canvas(
            body, width=HORIZON_SIZE, height=HORIZON_SIZE,
            bg=BG, highlightthickness=0,
        )
        self.canvas.pack(side="left")

        self.right = self._make_panel(body, "DURUM")
        self.right.pack(side="left", fill="y", padx=(12, 0))

        self.left_values = self._make_rows(
            self.left,
            ["Batarya", "Batarya sic.", "ESC sic.", "Baro sic.", "Basinc", "Irtifa"],
        )
        self.right_values = self._make_rows(
            self.right,
            ["Pitch", "Roll", "Heading", "Jiro p/q/r", "Ivme x/y/z",
             "Sensorler", "Kalibrasyon", "Arming", "Paket", "Yas"],
        )

        self._build_bottom_bar()

    def _make_panel(self, parent: tk.Widget, title: str) -> tk.Frame:
        frame = tk.Frame(parent, bg=BG)
        tk.Label(frame, text=title, bg=BG, fg=DIM,
                 font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(0, 6))
        return frame

    def _make_rows(self, parent: tk.Frame, labels: list[str]) -> dict[str, tk.Label]:
        values: dict[str, tk.Label] = {}
        for name in labels:
            row = tk.Frame(parent, bg=BG)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=name, bg=BG, fg=DIM, width=12,
                     anchor="w").pack(side="left")
            value = tk.Label(row, text="--", bg=BG, fg=FG, width=14,
                             anchor="e", font=("TkFixedFont", 11))
            value.pack(side="right")
            values[name] = value
        return values

    def _build_bottom_bar(self) -> None:
        bar = tk.Frame(self.root, bg=BG)
        bar.pack(fill="x", padx=12, pady=(0, 12))

        self.port_combo = ttk.Combobox(bar, state="readonly", width=24, values=())
        self.port_combo.pack(side="left")

        self.refresh_button = tk.Button(
            bar, text="YENILE", command=self._refresh_ports)
        self.refresh_button.pack(side="left", padx=6)

        self.connect_button = tk.Button(
            bar, text="BAGLAN", command=self._on_connect_toggle)
        self.connect_button.pack(side="left", padx=(0, 12))

        self.calibrate_button = tk.Button(
            bar, text="KALIBRE ET", command=self._on_calibrate, state="disabled")
        self.calibrate_button.pack(side="left")

        self.clear_button = tk.Button(
            bar, text="KALIBRASYONU SIL", command=self._on_clear_calibration,
            state="disabled")
        self.clear_button.pack(side="left", padx=6)

        self.disarm_button = tk.Button(
            bar, text="DISARM", command=self._on_disarm, state="disabled")
        self.disarm_button.pack(side="left")

        self.status = tk.Label(bar, text="Baglaniyor...", bg=BG, fg=DIM, anchor="w")
        self.status.pack(side="left", fill="x", expand=True, padx=12)

    # -- baglanti ---------------------------------------------------------

    def _refresh_ports(self) -> None:
        ports = link.available_ports()
        if ports == self.port_names:
            return

        self.port_names = ports
        self.port_combo.configure(values=tuple(ports))

        if self.port_combo.get() not in ports:
            # Tek aday varsa secili gelsin; operator her acilista ayni
            # tiklamayi yapmak zorunda kalmasin.
            self.port_combo.set(ports[0] if len(ports) == 1 else "")

    def _schedule_port_rescan(self) -> None:
        # Bagli degilken liste kendi kendine tazelenir: kumandayi taktiginda
        # YENILE'ye basmayi unutup "niye listede yok" dememek icin.
        if self.link is None:
            self._refresh_ports()
        self.root.after(PORT_RESCAN_MS, self._schedule_port_rescan)

    def _on_connect_toggle(self) -> None:
        if self.link is not None:
            self._disconnect()
            return

        port = self.port_combo.get().strip()
        if not port:
            self.status.configure(text="Once bir port sec")
            return
        self._connect(port)

    def _connect(self, port: str) -> None:
        candidate = link.SerialLink(port, self.baud)
        if not candidate.open():
            # Hata durum satirinda kalir ve pencere acik kalir; amac zaten
            # baska bir port secebilmek.
            self.status.configure(text=f"Port acilamadi: {candidate.last_error}")
            return

        self.link = candidate
        self._reset_session_state()
        self.connect_button.configure(text="KES", state="normal")
        self.port_combo.configure(state="disabled")
        self.refresh_button.configure(state="disabled")
        self.status.configure(text=f"{port} baglandi, telemetri bekleniyor...")

    def _disconnect(self) -> None:
        if self.link is not None:
            self.link.close()
            self.link = None

        self._reset_session_state()
        self.connect_button.configure(text="BAGLAN", state="normal")
        self.port_combo.configure(state="readonly")
        self.refresh_button.configure(state="normal")
        self.status.configure(text="Baglanti kesildi - port sec ve BAGLAN'a bas")

    def _reset_session_state(self) -> None:
        # Her baglanti yeni bir oturum: irtifa sifiri yeniden yakalanir,
        # bayatlik sayaclari ve bekleyen onaylar temizlenir.
        self.reference_pa = None
        self.last_rx_count = None
        self.last_packet_wall_time = None
        self.calibration_deadline_ms = None
        self.pending_calibration = None
        self.disarm_deadline_ms = None
        self.disarm_baseline_rx = None
        for label in (*self.left_values.values(), *self.right_values.values()):
            label.configure(text="--", fg=DIM)

    def shutdown(self) -> None:
        """Pencere kapandiktan sonra portu birak."""
        if self.link is not None:
            self.link.close()
            self.link = None

    # -- komutlar ---------------------------------------------------------

    def _on_calibrate(self) -> None:
        if self.link is None:
            return

        confirmed = messagebox.askokcancel(
            "Kalibrasyon",
            "Ucak duz zeminde, hareketsiz ve motor kapali mi?\n\n"
            "Kalibrasyon sirasinda STM32 flash'a yazar ve 1-2 saniye\n"
            "kontrol paketi islemez.",
        )
        if not confirmed:
            return

        telemetry = self.link.latest_telemetry()
        self.calibration_baseline_flags = telemetry.flags if telemetry else 0

        if self.link.send_command("CAL"):
            self.pending_calibration = "CAL"
            self.calibration_deadline_ms = CALIBRATION_TIMEOUT_MS
            self.status.configure(text="Kalibre ediliyor...")
        else:
            self.status.configure(text=f"Komut gonderilemedi: {self.link.last_error}")

    def _on_clear_calibration(self) -> None:
        if self.link is None:
            return
        if not messagebox.askokcancel("Kalibrasyon", "Kalibrasyon silinsin mi?"):
            return

        telemetry = self.link.latest_telemetry()
        self.calibration_baseline_flags = telemetry.flags if telemetry else 0

        if self.link.send_command("CALCLR"):
            self.pending_calibration = "CALCLR"
            self.calibration_deadline_ms = CALIBRATION_TIMEOUT_MS
            self.status.configure(text="Kalibrasyon siliniyor...")
        else:
            self.status.configure(text=f"Komut gonderilemedi: {self.link.last_error}")

    def _on_disarm(self) -> None:
        if self.link is None:
            return
        if self.link.send_command("DISARM"):
            telemetry = self.link.latest_telemetry()
            self.disarm_baseline_rx = telemetry.rx_count if telemetry else None
            self.disarm_deadline_ms = DISARM_TIMEOUT_MS
            self.status.configure(text="DISARM gonderildi, onay bekleniyor...")
        else:
            self.status.configure(text=f"DISARM gonderilemedi: {self.link.last_error}")

    # -- dongu ------------------------------------------------------------

    def run(self) -> None:
        self._refresh_ports()
        if self.initial_port:
            self.port_combo.set(self.initial_port)
            self._connect(self.initial_port)
        else:
            self.status.configure(text="Port sec ve BAGLAN'a bas")
        self._schedule_port_rescan()
        self._tick()
        self.root.mainloop()

    def _tick(self) -> None:
        # Tek bir hatali kare yenileme dongusunu kalici olarak durdurmamali:
        # pencere acik kalir, degerler donar ve hicbir uyari gorunmezdi.
        try:
            self._refresh()
        except Exception as exc:
            self.status.configure(text=f"Cizim hatasi: {exc}")
        finally:
            self.root.after(REFRESH_MS, self._tick)

    def _refresh(self) -> None:
        if self.link is None:
            self._draw_horizon(0.0, 0.0)
            self._set_buttons_enabled(False)
            return

        telemetry = self.link.latest_telemetry()

        if telemetry is not None and telemetry.rx_count != self.last_rx_count:
            self.last_rx_count = telemetry.rx_count
            self.last_packet_wall_time = time.monotonic()

        age_s = (time.monotonic() - self.last_packet_wall_time
                 if self.last_packet_wall_time is not None else None)
        stale = age_s is None or age_s * 1000 > LINK_STALE_MS

        if telemetry is not None:
            self._update_panels(telemetry, age_s)
            self._draw_horizon(*attitude.pitch_roll_deg(
                telemetry.ax, telemetry.ay, telemetry.az))
            self._update_buttons(telemetry, stale)
            self._check_calibration(telemetry)
            self._check_disarm(telemetry)
        else:
            self._draw_horizon(0.0, 0.0)
            self._set_buttons_enabled(False)

        # Bayat linkte paneller soluklasir, degerler ekranda kalir.
        colour = DIM if stale else FG
        for label in (*self.left_values.values(), *self.right_values.values()):
            label.configure(fg=colour)

        if stale:
            self.status.configure(text="LINK YOK")

    def _check_calibration(self, telemetry: link.Telemetry) -> None:
        if self.calibration_deadline_ms is None:
            return

        expected = self.pending_calibration == "CAL"
        now_calibrated = bool(telemetry.flags & link.FLAG_CALIBRATED)
        was_calibrated = bool(self.calibration_baseline_flags & link.FLAG_CALIBRATED)

        # Sadece anlik degere bakmak yanlis onay verir: bayrak zaten istenen
        # konumdaysa ucak hicbir sey yapmadan "tamam" gorunurdu. Gercek bir
        # gecis ariyoruz.
        if was_calibrated != expected and now_calibrated == expected:
            self.calibration_deadline_ms = None
            self.pending_calibration = None
            self.status.configure(
                text="Kalibrasyon tamam" if expected else "Kalibrasyon silindi")
            return

        self.calibration_deadline_ms -= REFRESH_MS
        if self.calibration_deadline_ms <= 0:
            self.calibration_deadline_ms = None
            # Bayrak bastan istenen konumdaysa bu kanaldan otomatik onay
            # mumkun degil; operatoru yanlis yonlendirmeyelim.
            no_edge_possible = was_calibrated == expected
            self.pending_calibration = None
            if no_edge_possible:
                self.status.configure(
                    text="Komut gonderildi, otomatik onay yok - pitch/roll sifira indi mi bak")
            else:
                self.status.configure(text="Onay gelmedi, tekrar dene")

    def _check_disarm(self, telemetry: link.Telemetry) -> None:
        if self.disarm_deadline_ms is None:
            return

        # Telemetri 1 Hz, arayuz 10 Hz. Butona basildigi anda ekranda olan
        # pakete bakip karar vermek yanlis alarm uretir; yalnizca komuttan
        # SONRA gelen paketler sayilir.
        fresh = (self.disarm_baseline_rx is None
                 or telemetry.rx_count != self.disarm_baseline_rx)

        if fresh and not telemetry.flags & link.FLAG_ARMED:
            self.disarm_deadline_ms = None
            self.disarm_baseline_rx = None
            self.status.configure(text="DISARM onaylandi")
            return

        self.disarm_deadline_ms -= REFRESH_MS
        if self.disarm_deadline_ms <= 0:
            self.disarm_deadline_ms = None
            self.disarm_baseline_rx = None
            if fresh:
                self.status.configure(text="UCAK HALA ARMED - DISARM'a tekrar bas")
            else:
                self.status.configure(text="Telemetri gelmedi - DISARM dogrulanamadi")

    # -- cizim ------------------------------------------------------------

    def _update_panels(self, t: link.Telemetry, age_s: float | None) -> None:
        has_baro = bool(t.flags & link.FLAG_BARO)
        if self.reference_pa is None and has_baro and t.pressure_pa > 0:
            self.reference_pa = t.pressure_pa

        self.left_values["Batarya"].configure(text=f"{t.voltage_mv / 1000:.2f} V")
        self.left_values["Batarya sic."].configure(text=_temp(t.batt_temp_centi))
        self.left_values["ESC sic."].configure(text=_temp(t.esc_temp_centi))

        self.left_values["Baro sic."].configure(
            text=_temp(t.baro_temp_centi) if has_baro else "--")
        self.left_values["Basinc"].configure(
            text=f"{t.pressure_pa} Pa" if has_baro else "--")
        altitude = attitude.relative_altitude_m(t.pressure_pa, self.reference_pa or 0)
        self.left_values["Irtifa"].configure(
            text=f"{altitude:+.1f} m" if has_baro else "--")

        pitch, roll = attitude.pitch_roll_deg(t.ax, t.ay, t.az)
        has_accel = bool(t.flags & link.FLAG_ACCEL)
        self.right_values["Pitch"].configure(text=f"{pitch:+.1f}" if has_accel else "--")
        self.right_values["Roll"].configure(text=f"{roll:+.1f}" if has_accel else "--")
        self.right_values["Ivme x/y/z"].configure(
            text=(f"{attitude.accel_to_g(t.ax):+.2f} "
                  f"{attitude.accel_to_g(t.ay):+.2f} "
                  f"{attitude.accel_to_g(t.az):+.2f}") if has_accel else "--")

        has_mag = bool(t.flags & link.FLAG_MAG)
        self.right_values["Heading"].configure(
            text=f"{attitude.heading_deg(t.heading_decideg):.1f}" if has_mag else "--")

        has_gyro = bool(t.flags & link.FLAG_GYRO)
        self.right_values["Jiro p/q/r"].configure(
            text=(f"{attitude.gyro_to_dps(t.gx):+.0f} "
                  f"{attitude.gyro_to_dps(t.gy):+.0f} "
                  f"{attitude.gyro_to_dps(t.gz):+.0f}") if has_gyro else "--")

        present = "".join([
            "A" if has_accel else "-",
            "G" if has_gyro else "-",
            "M" if has_mag else "-",
            "B" if has_baro else "-",
        ])
        self.right_values["Sensorler"].configure(text=present)
        self.right_values["Kalibrasyon"].configure(
            text="VAR" if t.flags & link.FLAG_CALIBRATED else "YOK")
        self.right_values["Arming"].configure(
            text="ARMED" if t.flags & link.FLAG_ARMED else "DISARMED")
        self.right_values["Paket"].configure(text=str(t.rx_count))
        self.right_values["Yas"].configure(
            text=f"{age_s:.1f} s" if age_s is not None else "--")

    def _update_buttons(self, t: link.Telemetry, stale: bool) -> None:
        armed = bool(t.flags & link.FLAG_ARMED)
        busy = (self.calibration_deadline_ms is not None
                or self.disarm_deadline_ms is not None)
        connected = self.link is not None and self.link.is_open
        can_calibrate = connected and not armed and not busy and not stale

        self.calibrate_button.configure(state="normal" if can_calibrate else "disabled")
        self.clear_button.configure(state="normal" if can_calibrate else "disabled")
        self.disarm_button.configure(state="normal" if connected else "disabled")
        # Bekleyen onay varken KES pasif: yarida kesip operatoru belirsiz
        # birakmayalim.
        self.connect_button.configure(state="disabled" if busy else "normal")

    def _set_buttons_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.calibrate_button.configure(state=state)
        self.clear_button.configure(state=state)
        self.disarm_button.configure(state=state)

    def _draw_horizon(self, pitch: float, roll: float) -> None:
        c = self.canvas
        c.delete("all")

        cx = cy = HORIZON_SIZE / 2
        r = HORIZON_RADIUS

        angle = math.radians(-roll)
        offset = pitch * PIXELS_PER_DEGREE

        # Ufuk cizgisinin merkezi, pitch kadar kaymis halde.
        hx = cx + offset * math.sin(angle)
        hy = cy + offset * math.cos(angle)

        span = r * 3
        dx = span * math.cos(angle)
        dy = -span * math.sin(angle)
        nx = span * math.sin(angle)
        ny = span * math.cos(angle)

        c.create_polygon(
            hx - dx, hy - dy, hx + dx, hy + dy,
            hx + dx - nx, hy + dy - ny, hx - dx - nx, hy - dy - ny,
            fill=SKY, outline="")
        c.create_polygon(
            hx - dx, hy - dy, hx + dx, hy + dy,
            hx + dx + nx, hy + dy + ny, hx - dx + nx, hy - dy + ny,
            fill=GROUND, outline="")
        c.create_line(hx - dx, hy - dy, hx + dx, hy + dy, fill=FG, width=2)

        # Pitch merdiveni, 10 derecede bir.
        for step in range(-30, 31, 10):
            if step == 0:
                continue
            d = (pitch - step) * PIXELS_PER_DEGREE
            mx = cx + d * math.sin(angle)
            my = cy + d * math.cos(angle)
            half = 28 if step % 20 else 44
            c.create_line(mx - half * math.cos(angle), my + half * math.sin(angle),
                          mx + half * math.cos(angle), my - half * math.sin(angle),
                          fill=FG, width=1)

        # Yuvarlak maske: tkinter'da kirpma yok, arka plan renginde bir halka ciz.
        # Tk, cizgi kalinligini yolun iki yanina esit dagitir. Maskenin ic kenari
        # tam HORIZON_RADIUS'ta bitmeli: yol yaricapi = R + kalinlik/2.
        # Dis kenar (R + kalinlik) tuvalin kosesini (320*sqrt(2)/2 = 227) asmali.
        mask_width = 200
        mask_r = HORIZON_RADIUS + mask_width / 2
        c.create_oval(cx - mask_r, cy - mask_r, cx + mask_r, cy + mask_r,
                      outline=BG, width=mask_width)
        c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=DIM, width=2)

        # Roll gostergesi: tepede sabit ucgen ok.
        c.create_polygon(cx, cy - r + 4, cx - 9, cy - r + 20, cx + 9, cy - r + 20,
                         fill=PLANE, outline="")

        # Sabit ucak sembolu.
        c.create_line(cx - 50, cy, cx - 16, cy, fill=PLANE, width=3)
        c.create_line(cx + 16, cy, cx + 50, cy, fill=PLANE, width=3)
        c.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, outline=PLANE, width=2)


def _temp(centi: int) -> str:
    if centi == link.TEMP_ABSENT:
        return "--"
    return f"{centi / 100:.1f} C"
