"""Yer istasyonu penceresi: yapay ufuk, sayisal paneller, komut butonlari."""

import math
import time
import tkinter as tk
from tkinter import messagebox, ttk

from . import attitude, hud, link
from .hud import (ACCENT, BG, DANGER, DIM, EDGE, EDGE_HI, FG, GROUND_FAR,
                  GROUND_NEAR, OK, PANEL, PLANE, SKY_HIGH, SKY_LOW, WARN)

REFRESH_MS = 100
LINK_STALE_MS = 3000
CALIBRATION_TIMEOUT_MS = 5000
DISARM_TIMEOUT_MS = 3000
PORT_RESCAN_MS = 2000

# Baslangic tuval boyutu; pencere tam ekran oldugunda cizim gercek tuval
# olculerinden yeniden hesaplanir, bu sabitler yalniz ilk yerlesim icin.
HORIZON_SIZE = 320
HORIZON_RADIUS = 140
# Gostergenin kenarina denk gelen egim aci. Yaricap degistikce derece basina
# piksel bundan turetilir, boylece ufuk her boyutta ayni orani gosterir.
HORIZON_DEGREES_VISIBLE = 46.0
# Halkanin disinda yatis olcegine yer kalsin.
HORIZON_MARGIN_PX = 40
HEADING_TAPE_PX = 46
# Pusula seridinin her iki yanda gosterdigi derece.
TAPE_DEGREES_VISIBLE = 45.0
HEADER_PX = 60

CARDINALS = {0: "K", 90: "D", 180: "G", 270: "B"}
COMPASS_POINTS = ("K", "KD", "D", "GD", "G", "GB", "B", "KB")


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
        # Ust seridin son karedeki girdileri; serit her karede bunlardan cizilir.
        self.shown_telemetry: link.Telemetry | None = None
        self.shown_age_s: float | None = None
        self.shown_stale = True

        self.root = tk.Tk()
        self.root.title("ISO U1 — Yer Istasyonu")
        self.root.configure(bg=BG)
        self.root.attributes("-fullscreen", True)
        # Tam ekranda pencere cercevesi yok; cikis yolu olmadan birakmayalim.
        self.root.bind("<Escape>", lambda _event: self._set_fullscreen(False))
        self.root.bind("<F11>", lambda _event: self._toggle_fullscreen())

        self._build_layout()

    def _set_fullscreen(self, enabled: bool) -> None:
        self.root.attributes("-fullscreen", enabled)

    def _toggle_fullscreen(self) -> None:
        self._set_fullscreen(not self.root.attributes("-fullscreen"))

    # -- kurulum ----------------------------------------------------------

    def _build_layout(self) -> None:
        self._style_widgets()

        self.header = tk.Canvas(self.root, height=HEADER_PX, bg=BG,
                                highlightthickness=0)
        self.header.pack(fill="x", padx=16, pady=(12, 0))

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self.left = self._make_column(body, "SISTEM")
        self.left.pack(side="left", fill="y", padx=(0, 12))

        self.canvas = tk.Canvas(
            body, width=HORIZON_SIZE, height=HORIZON_SIZE,
            bg=BG, highlightthickness=0,
        )
        self.canvas.pack(side="left", fill="both", expand=True)

        self.right = self._make_column(body, "UCUS")
        self.right.pack(side="left", fill="y", padx=(12, 0))

        self.tiles = {
            "battery": self._add_tile(self.left, "BATARYA", hud.icon_battery),
            "batt_temp": self._add_tile(self.left, "BATARYA SICAKLIK", hud.icon_thermometer),
            "esc_temp": self._add_tile(self.left, "ESC SICAKLIK", hud.icon_thermometer),
            "baro_temp": self._add_tile(self.left, "BARO SICAKLIK", hud.icon_thermometer),
            "pressure": self._add_tile(self.left, "BASINC", hud.icon_gauge),
            "altitude": self._add_tile(self.left, "IRTIFA", hud.icon_altitude),
            "pitch": self._add_tile(self.right, "PITCH", hud.icon_pitch),
            "roll": self._add_tile(self.right, "ROLL", hud.icon_roll),
            "heading": self._add_tile(self.right, "YON", hud.icon_compass),
            "gyro": self._add_tile(self.right, "JIRO  p / q / r", hud.icon_gyro,
                                   hud.VALUE_FONT_SMALL),
            "accel": self._add_tile(self.right, "IVME  x / y / z", hud.icon_accel,
                                    hud.VALUE_FONT_SMALL),
        }

        self._build_bottom_bar()

    def _style_widgets(self) -> None:
        # Tek ttk widget'i port listesi; 'aqua' temasi renk kabul etmiyor.
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "Hud.TCombobox", fieldbackground=PANEL, background=PANEL,
            foreground=FG, arrowcolor=ACCENT, bordercolor=EDGE_HI,
            lightcolor=PANEL, darkcolor=PANEL, selectbackground=PANEL,
            selectforeground=FG, padding=6)
        style.map(
            "Hud.TCombobox",
            fieldbackground=[("disabled", BG), ("readonly", PANEL)],
            foreground=[("disabled", DIM)],
            arrowcolor=[("disabled", DIM)],
            bordercolor=[("disabled", EDGE), ("focus", ACCENT)])
        self.root.option_add("*TCombobox*Listbox.background", PANEL)
        self.root.option_add("*TCombobox*Listbox.foreground", FG)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", BG)
        self.root.option_add("*TCombobox*Listbox.font", hud.LABEL_FONT)

    def _make_column(self, parent: tk.Widget, title: str) -> tk.Frame:
        frame = tk.Frame(parent, bg=BG)
        heading = tk.Frame(frame, bg=BG)
        heading.pack(fill="x", pady=(0, 8))
        tk.Label(heading, text="//", bg=BG, fg=ACCENT,
                 font=hud.LABEL_FONT).pack(side="left")
        tk.Label(heading, text=title, bg=BG, fg=DIM,
                 font=hud.LABEL_FONT).pack(side="left", padx=(4, 8))
        tk.Frame(heading, bg=EDGE, height=1).pack(side="left", fill="x", expand=True)
        return frame

    def _add_tile(self, parent: tk.Frame, title: str, icon,
                  value_font=hud.VALUE_FONT) -> hud.Tile:
        tile = hud.Tile(parent, title, icon, value_font)
        tile.pack(pady=4)
        return tile

    def _build_bottom_bar(self) -> None:
        tk.Frame(self.root, bg=EDGE, height=1).pack(fill="x", padx=16)
        bar = tk.Frame(self.root, bg=BG)
        bar.pack(fill="x", padx=16, pady=12)

        tk.Label(bar, text="PORT", bg=BG, fg=DIM,
                 font=hud.SMALL_FONT).pack(side="left", padx=(0, 8))
        self.port_combo = ttk.Combobox(bar, state="readonly", width=26, values=(),
                                       style="Hud.TCombobox", font=hud.LABEL_FONT)
        self.port_combo.pack(side="left")

        self.refresh_button = hud.HudButton(
            bar, text="YENILE", command=self._refresh_ports, tone=DIM)
        self.refresh_button.pack(side="left", padx=8)

        self.connect_button = hud.HudButton(
            bar, text="BAGLAN", command=self._on_connect_toggle, tone=ACCENT)
        self.connect_button.pack(side="left", padx=(0, 24))

        self.calibrate_button = hud.HudButton(
            bar, text="KALIBRE ET", command=self._on_calibrate, tone=WARN,
            state="disabled")
        self.calibrate_button.pack(side="left")

        self.clear_button = hud.HudButton(
            bar, text="KALIBRASYONU SIL", command=self._on_clear_calibration,
            tone=WARN, state="disabled")
        self.clear_button.pack(side="left", padx=8)

        # Acil durum butonu sagda, diger komutlardan ayri: yanlislikla
        # KALIBRE ET yerine basilmasin, aranirken de hemen bulunsun.
        self.disarm_button = hud.HudButton(
            bar, text="DISARM", command=self._on_disarm, tone=DANGER,
            state="disabled")
        self.disarm_button.pack(side="right")

        self.status = tk.Label(bar, text="Baglaniyor...", bg=BG, fg=ACCENT,
                               anchor="w", font=hud.LABEL_FONT)
        self.status.pack(side="left", fill="x", expand=True, padx=16)

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
        self.shown_telemetry = None
        self.shown_age_s = None
        self.shown_stale = True
        for tile in self.tiles.values():
            tile.reset()

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
            self._draw_header()
            self._set_buttons_enabled(False)
            return

        telemetry = self.link.latest_telemetry()

        if telemetry is not None and telemetry.rx_count != self.last_rx_count:
            self.last_rx_count = telemetry.rx_count
            self.last_packet_wall_time = time.monotonic()

        age_s = (time.monotonic() - self.last_packet_wall_time
                 if self.last_packet_wall_time is not None else None)
        stale = age_s is None or age_s * 1000 > LINK_STALE_MS

        self.shown_telemetry = telemetry
        self.shown_age_s = age_s
        self.shown_stale = stale

        if telemetry is not None:
            self._update_panels(telemetry, age_s)
            heading = (attitude.heading_deg(telemetry.heading_decideg)
                       if telemetry.flags & link.FLAG_MAG else None)
            self._draw_horizon(*attitude.pitch_roll_deg(
                telemetry.ax, telemetry.ay, telemetry.az), heading)
            self._update_buttons(telemetry, stale)
            self._check_calibration(telemetry)
            self._check_disarm(telemetry)
        else:
            self._draw_horizon(0.0, 0.0)
            self._set_buttons_enabled(False)

        # Bayat linkte paneller soluklasir, degerler ekranda kalir.
        for tile in self.tiles.values():
            tile.set_live(not stale)
        self._draw_header()

        if stale:
            self.status.configure(text="LINK YOK")
        self.status.configure(fg=DANGER if stale else ACCENT)

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
        tiles = self.tiles
        has_baro = bool(t.flags & link.FLAG_BARO)
        if self.reference_pa is None and has_baro and t.pressure_pa > 0:
            self.reference_pa = t.pressure_pa

        volts = t.voltage_mv / 1000
        charge = hud.clamp01((volts - hud.BATTERY_EMPTY_V)
                             / (hud.BATTERY_FULL_V - hud.BATTERY_EMPTY_V))
        colour = hud.battery_colour(charge)
        tiles["battery"].show(f"{volts:.2f}", "V", f"%{charge * 100:.0f}",
                              colour, fraction=charge, level=charge)

        self._show_temperature(tiles["batt_temp"], t.batt_temp_centi)
        self._show_temperature(tiles["esc_temp"], t.esc_temp_centi)
        self._show_temperature(
            tiles["baro_temp"], t.baro_temp_centi if has_baro else link.TEMP_ABSENT)

        if has_baro:
            # Deniz seviyesi 1013 hPa; ibre 950-1050 araliginda oynar.
            hpa = t.pressure_pa / 100
            tiles["pressure"].show(f"{hpa:.1f}", "hPa", colour=ACCENT,
                                   level=(hpa - 950) / 100)
            altitude = attitude.relative_altitude_m(t.pressure_pa, self.reference_pa or 0)
            tiles["altitude"].show(f"{altitude:+.1f}", "m", "GORELI", ACCENT)
        else:
            tiles["pressure"].show("--", sub="SENSOR YOK", colour=DIM)
            tiles["altitude"].show("--", sub="SENSOR YOK", colour=DIM)

        pitch, roll = attitude.pitch_roll_deg(t.ax, t.ay, t.az)
        if t.flags & link.FLAG_ACCEL:
            tiles["pitch"].show(f"{pitch:+.1f}", "deg", _nose(pitch), ACCENT, level=pitch)
            tiles["roll"].show(f"{roll:+.1f}", "deg", _bank(roll), ACCENT, level=roll)
            tiles["accel"].show(
                f"{attitude.accel_to_g(t.ax):+.2f} "
                f"{attitude.accel_to_g(t.ay):+.2f} "
                f"{attitude.accel_to_g(t.az):+.2f}", sub="g", colour=ACCENT)
        else:
            for key in ("pitch", "roll", "accel"):
                tiles[key].show("--", sub="SENSOR YOK", colour=DIM)

        if t.flags & link.FLAG_MAG:
            heading = attitude.heading_deg(t.heading_decideg)
            point = COMPASS_POINTS[round(heading / 45) % len(COMPASS_POINTS)]
            tiles["heading"].show(f"{heading:05.1f}", "deg", point, ACCENT, level=heading)
        else:
            tiles["heading"].show("--", sub="SENSOR YOK", colour=DIM)

        if t.flags & link.FLAG_GYRO:
            tiles["gyro"].show(
                f"{attitude.gyro_to_dps(t.gx):+.0f} "
                f"{attitude.gyro_to_dps(t.gy):+.0f} "
                f"{attitude.gyro_to_dps(t.gz):+.0f}", sub="deg/s", colour=ACCENT)
        else:
            tiles["gyro"].show("--", sub="SENSOR YOK", colour=DIM)

    @staticmethod
    def _show_temperature(tile: hud.Tile, centi: int) -> None:
        if centi == link.TEMP_ABSENT:
            tile.show("--", sub="SENSOR YOK", colour=DIM)
            return
        celsius = centi / 100
        colour = hud.temperature_colour(celsius)
        state = {hud.OK: "NORMAL", WARN: "SICAK", DANGER: "KRITIK"}[colour]
        # Olcek 0-90 C: LiPo ve ESC icin 60'in ustu zaten tehlike bolgesi.
        tile.show(f"{celsius:.1f}", "C", state, colour,
                  fraction=celsius / 90, level=celsius / 90)

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

    def _draw_header(self) -> None:
        c = self.header
        c.delete("all")
        width = c.winfo_width()
        height = HEADER_PX
        if width < 2:
            return
        mid = height / 2 - 2

        c.create_line(0, height - 1, width, height - 1, fill=EDGE)
        c.create_line(0, height - 1, 260, height - 1, fill=ACCENT, width=3)
        title = c.create_text(0, mid, text="ISO-U1", anchor="w",
                              font=hud.TITLE_FONT, fill=ACCENT)
        x = c.bbox(title)[2] + 10
        subtitle = c.create_text(x, mid + 1, text="YER ISTASYONU", anchor="w",
                                 font=hud.LABEL_FONT, fill=DIM)
        x = max(c.bbox(subtitle)[2] + 40, 300)

        t = self.shown_telemetry
        connected = self.link is not None
        if not connected:
            x = hud.pill(c, x, mid, "BAGLI DEGIL", DIM)
        elif self.shown_stale:
            x = hud.pill(c, x, mid, "LINK YOK", DANGER, filled=_blink())
        else:
            x = hud.pill(c, x, mid, "LINK OK", OK)

        if t is not None:
            if t.flags & link.FLAG_ARMED:
                # Motor donebilir: ekranda kacirilmayacak kadar bagirsin.
                x = hud.pill(c, x + 10, mid, "ARMED", DANGER, filled=_blink())
            else:
                x = hud.pill(c, x + 10, mid, "DISARMED", OK)
            if t.flags & link.FLAG_CALIBRATED:
                x = hud.pill(c, x + 10, mid, "KAL VAR", OK)
            else:
                x = hud.pill(c, x + 10, mid, "KAL YOK", WARN)

            x += 24
            for letter, flag in (("A", link.FLAG_ACCEL), ("G", link.FLAG_GYRO),
                                 ("M", link.FLAG_MAG), ("B", link.FLAG_BARO)):
                present = bool(t.flags & flag)
                x = hud.pill(c, x, mid, letter, ACCENT if present else DANGER,
                             filled=present, font=hud.SMALL_FONT) + 4

        right = width
        clock = c.create_text(right, mid, text=time.strftime("%H:%M:%S"), anchor="e",
                              font=hud.TITLE_FONT, fill=FG)
        right = c.bbox(clock)[0] - 24
        age = f"{self.shown_age_s:.1f}s" if self.shown_age_s is not None else "--"
        for label, value in (("YAS", age),
                             ("PAKET", str(t.rx_count) if t is not None else "--")):
            item = c.create_text(right, mid, text=value, anchor="e",
                                 font=hud.LABEL_FONT, fill=FG)
            right = c.bbox(item)[0] - 6
            item = c.create_text(right, mid, text=label, anchor="e",
                                 font=hud.SMALL_FONT, fill=DIM)
            right = c.bbox(item)[0] - 20

    def _draw_horizon(self, pitch: float, roll: float,
                      heading: float | None = None) -> None:
        c = self.canvas
        c.delete("all")

        # Olculer tuvalden okunuyor: pencere tam ekran ve gosterge onunla
        # birlikte buyuyor, sabit bir boyut varsayilamaz.
        width = c.winfo_width()
        height = c.winfo_height()
        if width < 2 or height < 2:
            return  # tuval henuz yerlesmedi, bir sonraki karede cizilir

        top = HEADING_TAPE_PX + 12
        cx = width / 2
        cy = top + (height - top) / 2
        r = min(width, height - top) / 2 - HORIZON_MARGIN_PX
        if r <= 0:
            return

        # Derece basina piksel yaricaptan turetilir; ufuk her boyutta ayni
        # aci araligini gosterir.
        ppd = r / HORIZON_DEGREES_VISIBLE
        scale = r / HORIZON_RADIUS

        angle = math.radians(-roll)
        offset = pitch * ppd

        # Ufuk cizgisinin merkezi, pitch kadar kaymis halde.
        hx = cx + offset * math.sin(angle)
        hy = cy + offset * math.cos(angle)

        span = max(width, height) * 1.5
        # Ufuk boyunca birim vektor ve gokyuzune bakan normal.
        tx, ty = math.cos(angle), -math.sin(angle)
        ux, uy = -math.sin(angle), -math.cos(angle)

        def band(d0: float, d1: float, colour: str) -> None:
            # Ufka paralel, gokyuzu yonunde d0..d1 piksel uzaklikta serit.
            ax, ay = hx + ux * d0, hy + uy * d0
            bx, by = hx + ux * d1, hy + uy * d1
            c.create_polygon(
                ax - tx * span, ay - ty * span, ax + tx * span, ay + ty * span,
                bx + tx * span, by + ty * span, bx - tx * span, by - ty * span,
                fill=colour, outline="")

        # Ufka yaklastikca aydinlanan gok ve koyulasan yer: tk'da gradyan yok,
        # birkac serit yetiyor.
        band(0, span, SKY_HIGH)
        band(0, r * 0.55, _mix(SKY_HIGH, SKY_LOW, 0.5))
        band(0, r * 0.25, SKY_LOW)
        band(-span, 0, GROUND_FAR)
        band(-r * 0.4, 0, GROUND_NEAR)
        c.create_line(hx - tx * span, hy - ty * span, hx + tx * span, hy + ty * span,
                      fill=FG, width=2)

        # Pitch merdiveni: 10 derecede bir etiketli, 5'lerde kisa cizgi.
        for step in range(-40, 41, 5):
            if step == 0:
                continue
            d = (pitch - step) * ppd
            mx = cx + d * math.sin(angle)
            my = cy + d * math.cos(angle)
            major = step % 10 == 0
            half = (44 if major else 18) * scale
            c.create_line(mx - half * tx, my - half * ty, mx + half * tx, my + half * ty,
                          fill=FG, width=2 if major else 1,
                          dash=() if step > 0 else (6, 4))
            if major:
                for side in (-1, 1):
                    lx = mx + side * (half + 16 * scale) * tx
                    ly = my + side * (half + 16 * scale) * ty
                    c.create_text(lx, ly, text=str(abs(step)), fill=FG,
                                  font=(hud.MONO, min(13, max(8, int(9 * scale))), "bold"),
                                  angle=-roll)

        # Yuvarlak maske: tkinter'da kirpma yok, arka plan renginde bir halka
        # ciziliyor. Tk cizgi kalinligini yolun iki yanina esit dagittigi icin
        # maskenin ic kenari tam r'de bitmeli (yol yaricapi = r + kalinlik/2),
        # dis kenari da tuvalin kosesini asmali.
        corner = math.hypot(width, height) + 10
        mask_width = max(corner - r, 2.0)
        mask_r = r + mask_width / 2
        c.create_oval(cx - mask_r, cy - mask_r, cx + mask_r, cy + mask_r,
                      outline=BG, width=mask_width)

        # Cerceve: ince parlak halka ve disinda koyu bir bilezik.
        c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=ACCENT, width=2)
        outer = r + 30
        c.create_oval(cx - outer, cy - outer, cx + outer, cy + outer,
                      outline=EDGE, width=1)

        # Yatis olcegi halkanin disinda sabit; isaretci ufukla birlikte doner.
        for mark in (-60, -45, -30, -20, -10, 0, 10, 20, 30, 45, 60):
            a = math.radians(mark)
            length = 14 if mark % 30 == 0 else 8
            inner = r + 6
            c.create_line(cx + inner * math.sin(a), cy - inner * math.cos(a),
                          cx + (inner + length) * math.sin(a),
                          cy - (inner + length) * math.cos(a),
                          fill=FG if mark % 30 == 0 else DIM, width=2)
        c.create_polygon(cx, cy - r - 6, cx - 8, cy - r - 20, cx + 8, cy - r - 20,
                         fill=FG, outline="")
        tip = r - 4
        px, py = cx + ux * tip, cy + uy * tip
        base = tip - 16 * scale
        bx, by = cx + ux * base, cy + uy * base
        wing = 9 * scale
        c.create_polygon(px, py, bx - tx * wing, by - ty * wing, bx + tx * wing,
                         by + ty * wing, fill=PLANE, outline=BG)

        # Sabit ucak sembolu, koyu kenarli ki gok ve yer uzerinde okunsun.
        w_out, w_in, drop = 70 * scale, 22 * scale, 12 * scale
        for colour, thickness in ((BG, 7), (PLANE, 4)):
            c.create_line(cx - w_out, cy, cx - w_in, cy, cx - w_in / 2, cy + drop,
                          fill=colour, width=thickness, joinstyle="miter")
            c.create_line(cx + w_out, cy, cx + w_in, cy, cx + w_in / 2, cy + drop,
                          fill=colour, width=thickness, joinstyle="miter")
        dot = 4 * scale
        c.create_oval(cx - dot, cy - dot, cx + dot, cy + dot, fill=PLANE, outline=BG)

        self._draw_heading_tape(cx, 4, min(width - 20, 2 * r + 60), heading)
        self._draw_corner_brackets(width, height)

    def _draw_heading_tape(self, cx: float, top: float, width: float,
                           heading: float | None) -> None:
        c = self.canvas
        x0, x1 = cx - width / 2, cx + width / 2
        y0, y1 = top, top + HEADING_TAPE_PX
        hud.chamfer(c, x0, y0, x1, y1, 10, fill=hud.PANEL, outline=EDGE)
        if heading is None:
            c.create_text(cx, (y0 + y1) / 2, text="PUSULA YOK", fill=DIM,
                          font=hud.LABEL_FONT)
            return

        ppd = width / (2 * TAPE_DEGREES_VISIBLE)
        mark = math.floor((heading - TAPE_DEGREES_VISIBLE) / 5) * 5
        while mark <= heading + TAPE_DEGREES_VISIBLE:
            x = cx + (mark - heading) * ppd
            if x0 + 8 <= x <= x1 - 8:
                major = mark % 10 == 0
                c.create_line(x, y1 - 2, x, y1 - (14 if major else 7),
                              fill=FG if major else DIM, width=1)
                if mark % 30 == 0:
                    bearing = mark % 360
                    text = CARDINALS.get(bearing, f"{bearing // 10:02d}")
                    c.create_text(x, y0 + 14, text=text, font=hud.LABEL_FONT,
                                  fill=WARN if bearing in CARDINALS else FG)
            mark += 5

        c.create_polygon(cx, y1 - 12, cx - 7, y1 + 2, cx + 7, y1 + 2,
                         fill=ACCENT, outline="")
        hud.chamfer(c, cx - 36, y0 + 2, cx + 36, y0 + 26, 6, fill=BG, outline=ACCENT)
        c.create_text(cx, y0 + 14, text=f"{heading:03.0f}", font=hud.LABEL_FONT,
                      fill=ACCENT)

    def _draw_corner_brackets(self, width: float, height: float) -> None:
        c = self.canvas
        size, inset = 26, 2
        for x, y, sx, sy in ((inset, inset, 1, 1), (width - inset, inset, -1, 1),
                             (inset, height - inset, 1, -1),
                             (width - inset, height - inset, -1, -1)):
            c.create_line(x, y + sy * size, x, y, x + sx * size, y,
                          fill=EDGE_HI, width=2)


def _blink() -> bool:
    # Yari saniyelik yanip sonme; ayri bir zamanlayici gerektirmiyor.
    return int(time.monotonic() * 2) % 2 == 0


def _mix(a: str, b: str, t: float) -> str:
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ca, cb))


def _nose(pitch: float) -> str:
    if abs(pitch) < 2:
        return "DUZ"
    return "BURUN YUKARI" if pitch > 0 else "BURUN ASAGI"


def _bank(roll: float) -> str:
    if abs(roll) < 2:
        return "DUZ"
    return "SAG" if roll > 0 else "SOL"
