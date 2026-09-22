# ISO U1 Yer İstasyonu

ESP32 kumandaya USB ile bağlanır, telemetriyi yapay ufuk ve sayısal
panellerle gösterir, GY-85 kalibrasyonunu tetikler.

## Kurulum

    brew install python-tk@3.14
    .env/bin/pip install pyserial pytest

## Çalıştırma

Repo kökünden:

    ./tools/run_navstation.sh

Bu betik nereden çağrılırsa çağrılsın doğru dizine geçip programı başlatır.
`navstation` bir Python paketi ve yalnız `tools/` içinden import edilebiliyor;
repo kökünden doğrudan `python -m navstation` demek
`No module named navstation` verir.

Doğrudan çalıştırmak istersen `tools/` dizininden:

    ../.env/bin/python -m navstation

Pencere bağlantısız açılır. Alt şeritteki listeden portu seç ve **BAGLAN**'a bas.
Liste bağlı değilken iki saniyede bir kendini tazeler, yani kumandayı program
açıkken taksan da görünür; **YENILE** elle taramak için.

Tek port varsa hazır seçili gelir. Bluetooth portları listeden elenir — seri
görünürler ama kumanda değillerdir.

Portu baştan biliyorsan atlayabilirsin:

    ./tools/run_navstation.sh --port /dev/cu.usbserial-XXXX

Port açılamazsa program çıkmaz; hatayı durum satırında gösterir ve başka bir
port seçebilirsin.

**Kumanda seri monitörü aynı anda açık olmamalı** — port tek kullanıcı kabul
eder. `pio device monitor` açıksa "Port acilamadi" alırsın.

**KES**'e basınca bağlantı kapanır, paneller sıfırlanır ve irtifa referansı
düşer; yeniden bağlandığında irtifa sıfırı o an yakalanır. Bekleyen bir
kalibrasyon veya DISARM onayı varsa KES pasif olur.

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
