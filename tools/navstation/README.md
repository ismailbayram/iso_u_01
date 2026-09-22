# ISO U1 Yer İstasyonu

ESP32 kumandaya USB ile bağlanır, telemetriyi yapay ufuk ve sayısal
panellerle gösterir, GY-85 kalibrasyonunu tetikler.

## Kurulum

    brew install python-tk@3.14
    .env/bin/pip install pyserial pytest

## Çalıştırma

Portu bul:

    ls /dev/cu.usbserial-* /dev/cu.SLAB_USBtoUART 2>/dev/null

Sonra `tools/` dizininden:

    ../.env/bin/python -m navstation --port /dev/cu.usbserial-XXXX

Kumanda seri monitörü aynı anda açık olmamalı — port tek kullanıcı kabul eder.

## Kalibrasyon

**KALİBRE ET** butonu uçağın o anki IMU okumalarını sıfır kabul eder ve
sonucu STM32 flash'ına yazar.

Koşullar:

- Uçak düz zeminde ve hareketsiz olmalı.
- Motor kapalı olmalı. STM32 armed durumdayken komutu reddeder, buton da pasifleşir.
- Flash yazımı sırasında STM32 1-2 saniye kontrol paketi işlemez. Pervane sökülü olmalı.

Onay telemetriden gelir ve telemetri 1 Hz olduğu için 1-2 saniye sürer.
5 saniyede gelmezse buton "Onay gelmedi" der; tekrar basmak zararsızdır.

Pusula kalibre edilmez — sıfırlansaydı kuzeyi değil kalibrasyon anındaki
yönü gösterirdi.

## Arming

Motor, uçağa güç verildiğinde dönmez. Çalıştırmak için kumandadan:

1. İki çubuğu da aşağı çek
2. Bırak
3. Tekrar aşağı çek ve yarım saniye tut

Kumanda arm olunca iki yükselen ton, disarm olunca tek alçak ton çalar.

Disarm: güç kesme, 5 saniyeden uzun link kaybı, veya bu programdaki
**DISARM** butonu. Uçuşta çubukla disarm yoktur.

## Testler

    cd tools && ../.env/bin/python -m pytest navstation/tests/ -v

## İrtifa referansı

İrtifa mutlak değil, göreli. Kumanda kendi referansını açılışta, bu program
kendi referansını bağlandığı anda yakalar — ikisi farklı zamanlarda
başlatıldıysa OLED ile bu ekran aynı uçak için farklı irtifa gösterir.
Uçuştan önce ikisini de aynı anda başlatmak en temizi.
