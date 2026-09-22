# Kumanda Kutusu v2 — Tasarım

Tarih: 2026-09-22
Durum: onay bekliyor
İlgili dosyalar: `mechanical/controller/old/kumanda_alt.stl`, `mechanical/controller/old/kumanda_ust.stl`

## 1. Amaç

ISO U1 kumandasının mevcut iki parçalı kutusu (`kumanda_alt` + `kumanda_ust`) iki sebeple
yenileniyor:

1. **OLED ekran yamuk duruyor.** Modül 2.54 mm header üstüne dikili ve kutu içinde onu
   sadece sağ uçtan destekleyen tek bir blok var. Tek taraflı destek modülü hem Z'de
   yatırıyor hem planda döndürüyor.
2. **Gövde çirkin.** 135 × 136.7 mm düz kare levha, keskin köşeler, altından çıkan iki düz
   ray, kabartma yazı. Elde tutulacak bir şeye benzemiyor.

Elektronik kartına dokunulmuyor: 133 mm'lik delikli pertinaks, üstündeki bileşen yerleri ve
4 × M3 montaj deliği aynen kalıyor. Bu yüzden tasarımın serbest olduğu tek yer dış kabuk,
tutuş ve ekran desteği.

## 2. Kapsam dışı

- **Kartı yeniden dizmek.** Joystickler, ESP32 ve OLED şu anki yerlerinde kalıyor. Kutu
  onlara uyuyor, tersi değil.
- **OLED modülünü header'dan sökmek.** Kullanıcı sökmeyecek. Ekranın lehim noktalarının
  pencereden görünmesi kabul edildi.
- **Batarya.** Kumanda ESP32'nin micro-USB girişinden besleniyor. İç hacimde batarya,
  şarj kartı veya güç anahtarı için yer ayrılmıyor.
- **Anten ve USB çıkışının yeri.** Mevcut tasarımda oturuyor; 4.4'te olduğu gibi eski
  parçadan birebir kopyalanıyor, yeniden yorumlanmıyor.

## 3. Ölçüm: eski parçadan çıkarılan veriler

Bütün koordinatlar **D çerçevesinde**: XY orijini eski `kumanda_alt` gövdesinin sınır
kutusunun minimum köşesi (dünya koordinatında 135.15, 14.11), Z orijini kart oturma düzlemi
(direk üstleri). X sağa, Y ekran kenarına doğru, Z yukarı.

`kumanda_ust` dosyasının XY orijini `kumanda_alt`'tan (0.31, −0.07) mm kayık. Bu kayma el
çizimi kaynaklı ve tolerans içinde; aşağıdaki kapak kaynaklı ölçüler D'ye çevrilmiş halde
verilmiştir.

### 3.1 Z düzlemleri

| Düzlem | z (mm) |
|---|---|
| Gövde dış tabanı | −20.0 |
| İç zemin (üst yüz) | −18.5 |
| Kart oturma düzlemi (direk üstü) | 0.0 |
| Kart üst yüzü (1.6 mm pertinaks) | 1.6 |
| Gövde duvar üstü | 16.0 |
| OLED modülünün oturduğu tavan omzu | 17.0 |
| Kapak plakasının alt yüzü | 21.0 |
| Kapak üst yüzü | 22.5 |

Eski toplam yükseklik: −36.51 … 22.5 = 59.0 mm. Bunun 16.5 mm'si içi boş rayların
oluşturduğu ölü hacim.

### 3.2 Kart montaj direkleri (Ø5 dış, Ø3 delik, üst yüz z = 0)

| # | x | y |
|---|---|---|
| 1 | 11.75 | 10.96 |
| 2 | 124.74 | 10.66 |
| 3 | 12.46 | 124.34 |
| 4 | 123.04 | 124.54 |

Ağırlık merkezi: (68.00, 67.63). Desen dik değil — X aralıkları 112.99 ve 110.58, Y
aralıkları 113.38 ve 113.88. Delikler karta zaten açılmış olduğu için bu dört koordinat
**aynen** korunacak, düzeltilmeyecek.

### 3.3 Kapak kesikleri (D çerçevesinde)

Değerler `trimesh.Trimesh.section` ile z = 19.0 düzleminden, kapalı çevrimlerin sınır
kutularından okunmuştur:

| Özellik | Merkez | Ölçü |
|---|---|---|
| Sol joystick | (27.19, 50.61) | Ø30.0 |
| Sağ joystick | (108.90, 51.39) | Ø30.0 |
| Ekran deliği | (107.44, 113.77) | 37.5 × 12.2 |
| Ekran omzu | (107.44, 113.77) | 39.5 × 14.2 |
| Kapak vidası (sol) | (4.22, 67.44) | Ø2.5 |
| Kapak vidası (sağ) | (130.20, 67.44) | Ø2.5 |

### 3.4 Üst kenardaki anten / USB kanalı

Üst kenarın ortası oyuk. Gövde duvarı x ≈ 46 … 89 arasında **y = 129.0**'a kadar geri
çekilmiş ve kanal tüm yükseklik boyunca dışarı açık; iki yanında x ≈ 36 → 46 ve x ≈ 89 →
104 arasında pah var. SMA konnektörünün anteni ve ESP32'nin micro-USB kablosu buradan
çıkıyor. Kapakta ek olarak x = 63.0 … 74.6 arasında **y = 120.3**'e inen, kabloyu yukarı
bükmeye yarayan daha derin bir yuva var.

Kullanıcı bu bölgenin oturduğunu söylüyor, dolayısıyla **yorumlanmıyor, boolean ile
kopyalanıyor**:

```
KANAL_BOLGESI = kutu(x = 28 … 108, y = 126.0 … 136.07, z = −21 … 24)
kanal_negatifi = KANAL_BOLGESI − eski_govde_kati
```

`eski_govde_kati`, `kumanda_alt.stl`'in D çerçevesine ötelenmiş (−135.15, −14.11, 0) hali.
Bu negatif hem yeni gövdeden hem yeni kapaktan çıkarılır; eski parçanın o bölgede açık
bıraktığı her hacim yeni parçada da açık kalır.

Yeni gövdenin dış kenarı y = 138.63'te, eskisi ise y = 136.07'deydi. Aradaki 2.56 mm'lik
şeridi de açmak için ikinci bir kesim uygulanır:

```
kanal_uzantisi = kutu(x = 36.27 … 103.94, y = 136.07 … 145, z = −21 … 24)
```

Kapağa ayrıca kablo yuvası eklenir:

```
kablo_yuvasi = kutu(x = 62.69 … 74.29, y = 120.37 … 145, z = 20 … 24)
```

### 3.5 Eski ekran desteği (kaldırılacak)

Gövdede x = 122.8…133.5, y = 107.6…119.8, z = 7.4…14.4 ölçülerinde bir blok var. Ekranın
yalnızca sağ ucunu destekliyor; yamukluğun sebebi bu. Yeni tasarımda kaldırılıyor, yerine
Bölüm 5'teki tabla geçiyor.

## 4. Yeni gövde

### 4.1 İç hacim

Kart cebi, direk deseninin ağırlık merkezine (68.00, 67.63) oturtulmuş **136.0 × 136.0 mm**
kare, plan köşeleri **R4**. D çerçevesinde x = 0.0 … 136.0, y = −0.37 … 135.63. 133 mm'lik
kartın çevresinde her yönde ≥ 1.5 mm boşluk kalır. Eski cep 132.0 × 133.7 idi ve karta göre
dardı.

Köşe yarıçapı 4 mm ile sınırlı: kartın köşesi cebin köşesinden (1.5, 1.5) içeride, yani
yuvarlatma yayının merkezine 3.54 mm uzaklıkta. R6 kullanılsaydı yay kartın dört köşesini
keserdi.

Kart, 3.2'deki dört direğe (Ø5 dış, M3 sac vidası için Ø2.6 pilot delik, üst yüz z = 0)
oturur.

### 4.2 Dış hat

- Duvar: sol ve sağda **7.0 mm**, üst ve altta **3.0 mm**. Sol/sağ kalınlığı kapak vidası
  kulelerini duvarın içinde taşımak için; böylece cep temiz bir dikdörtgen kalır ve kartın
  kenarına hiçbir çıkıntı girmez (eski tasarımda vida kuleleri cebe 5.8 mm taşıyordu).
- Dış gövde: **150.0 × 142.0 mm**, toplam yükseklik z = −20 … 23, yani **43 mm** (eski 59).
- Plan köşeleri **R14**.
- Yan duvarlar aşağı doğru **5° içe eğimli** (draft). Kalınlık değişmez, siluet incelir.
- Üst ve alt kenarlar **R3** yuvarlatılmış.

Geometri, üst ve alt dış hat boyunca dizilmiş r = 3 mm küre kümesinin dışbükey kabuğu
(`Manifold.hull`) olarak kurulur: taper, R14 plan köşesi ve R3 kenar yuvarlaması tek
işlemde çıkar.

### 4.3 Kapak

- Plaka kalınlığı **2.0 mm**; alt yüz z = 21.0, üst yüz **z = 23.0**.
- Etek gövde duvarının dışını sarar, z = 11.0'a kadar iner (duvar üstü 16.0, örtüşme 5 mm).
  Etek 2.0 mm kalın, gövde ile arasında 0.2 mm geçme boşluğu var; kapağın dış ölçüsü bu
  yüzden **154.4 × 146.4 mm**. Kapak, takımın en büyük parçasıdır.
- Joystick delikleri: ikisi de **Ø33**, merkezleri **(27.19, 51.00)** ve **(108.90, 51.00)**.
  Eski deliklerin Y'si 0.78 mm kaçıktı (50.61 / 51.39); ortak Y = 51.00'a alınıp çap 30'dan
  33'e çıkarılınca eski deliklerin ikisi de yenisinin içinde kalıyor ve göze simetrik
  geliyor. X değerleri ölçülen haliyle korunuyor.
- Her joystick deliğinin çevresinde **Ø46, 1.2 mm derin küresel çukur** (başparmak yuvası).
- Anten / USB kanalı: 3.4'teki boolean kuralıyla, kablo yuvası dahil.
- Yazılar **0.6 mm gömme**: "ISO U1" kapağın alt bölgesine (merkez x = 68, y ≈ 20),
  "İstikbal Göklerdedir" gövdenin alt dış yüzüne. Kabartma iptal — mevcut baskıda tüylenmiş.

### 4.4 Kapak vidaları

4 adet **M3 × 16** sac vidası, sol ve sağ duvarın (7 mm) içindeki kulelere:

| # | x | y |
|---|---|---|
| 1 | −2.5 | 30.0 |
| 2 | −2.5 | 105.0 |
| 3 | 138.5 | 30.0 |
| 4 | 138.5 | 105.0 |

Gövde tarafı Ø6 kule + Ø2.5 pilot, kapak tarafı Ø3.4 geçme + Ø6 × 0.8 havşa. Havşa sığ:
kapak plakası 2.0 mm ve daha derin bir havşa plakayı tümden deler, vida başına yatak
kalmaz. Başlar 0.8 mm gömülü durur, tam sıfır değil. Kuleler dış
kabuğa göre kırpılır (4.2'deki küre kabuğu ile kesişim), böylece 5°'lik eğim yüzünden
duvardan dışarı taşmazlar. Kule x merkezi cebin kenarından 2.5 mm dışarıda; Ø6 kule cebe
0.5 mm girer, kartın kenarına 1.0 mm boşluk kalır.

Eski tasarımdaki 2 vida yerine 4 vida: 150 mm'lik kapağın ortadan açılmaması için.

## 5. Ekran desteği — `screen_shim`

OLED modülü header'dan sökülmüyor. Modülü düzlemde tutmak için kartın üstüne, modülün
altına giren ayrı bir tabla basılıyor; kullanıcı modülü elle bu tablaya bastırıyor.

- Dış ölçü **38.4 × 12.4 mm**, modülün PCB ölçüsüne (38 × 12) 0.4 mm boşluklu.
- **U kesit**: 3.0 mm genişliğinde çerçeve, bir uzun kenar tamamen açık. Açık kenar header
  pin sırasına ve lehim damlalarına bakar, kalan üç kenar modülü taşır. Yamukluğun sebebi
  tek noktadan destekti; üç kenar bunu bitirir.
- Üst yüzün çevresinde 1.0 mm yüksek, 0.8 mm kalın konumlandırma dudağı — modül kaymaz.
- **Yükseklik:** modülün PCB üst yüzü kapağın z = 17.0 omzuna dayanmalı. PCB 1.6 mm, alt
  yüzü z = 15.4. Kart üst yüzü z = 1.6. Tabla yüksekliği = 15.4 − 1.6 = **13.8 mm**.
- Header yığını toleranslı olduğu için üç boy basılır: **13.3 / 13.8 / 14.3 mm**
  (`screen_shim_133.stl`, `_138.stl`, `_143.stl`). Oturan kullanılır.
- Karta çift taraflı bant veya birkaç damla yapıştırıcı ile sabitlenir. Ayak bölgesine denk
  gelen bir lehim damlası varsa kullanıcı o köşeyi keser — U çerçevesi buna izin verir.

Kapak tarafı:

- Kapak plakasının alt yüzünden aşağı sarkan **44.2 × 18.2 mm dış ölçülü bilezik**,
  z = 16.0 … 21.0.
- Bileziğin içinde iki kademeli delik: **39.2 × 13.2 mm yuva z = 16.0 … 17.0** ve üstünde
  **36.5 × 10.5 mm pencere z = 17.0 … 23.0**. Modül aşağıdan yuvaya girer, PCB üst yüzü
  z = 17.0'daki omuza dayanır; çevrede 1.35 mm dudak kalır, modül yukarı geçmez ve PCB
  kenarı gizlenir. Yuvanın 1 mm'lik derinliği modülü yanal olarak da tutar.
- Kapak üst yüzünde pencerenin çevresinde **46 × 20 mm, 1.0 mm gömme panel alanı**. Düz
  basılmış bu çerçeve göz için referans olur; modülde kalan birkaç onda derecelik kaçıklık
  okunmaz.
- Hepsi 3.3'teki (107.44, 113.77) merkezine hizalı.

## 6. Kabzalar

- Gövdenin alt iki köşesinden dışa ve aşağı doğru kıvrılan iki lob.
- Geometri: kavis boyunca dizilmiş 5 kürenin dışbükey kabuğu, **z = −20 düzleminde
  kesilmiş**. Kesme düzlemi gövdenin dış taban yüzeyi; kabzanın gövdeye bakan yüzü böylece
  **düz** olur.
- Sol kabza küre zinciri (merkez x, y, z ve yarıçap, D çerçevesinde):

  | x | y | z | r |
  |---|---|---|---|
  | 30.0 | 14.0 | −22.0 | 16.0 |
  | 20.0 | 3.0 | −24.0 | 14.0 |
  | 8.0 | −8.0 | −26.0 | 12.0 |
  | −5.0 | −17.0 | −28.0 | 10.0 |
  | −17.0 | −25.0 | −30.0 | 8.0 |

  Sağ kabza bu zincirin x = 68.0 düzlemine göre aynası (x' = 136.0 − x).
- Sonuçlanan sınırlar: en alçak nokta **z = −38**, en dış nokta **x = −25** (sağda 161),
  yani her kabza gövdeden **18 mm** taşar. Kabzalarla toplam genişlik **186 mm**, toplam
  yükseklik **61 mm**.
- Kesit çapı kökte 32 mm, uçta 16 mm; gövdenin altından ölçülen derinlik 18 mm.
- Duvar 2.5 mm, içi boş (dış kabuk ile yarıçapları 2.5 mm küçültülmüş iç kabuk arasındaki
  fark), gövdeye bakan yüzü açık.
- **Fileto yok.** Kabza ayrı parça olduğu için gövde ile arasında düz bir ayrım çizgisi
  kalır. Geçişin sert görünmemesi için zincirin kök küresi en büyük (r = 16) seçilmiştir;
  lob birleşme yerinde en geniş halindedir.

### 6.1 Bağlantı

Her kabza gövdeye **2 × M3 × 14** ile bağlanır. Vidalar kabzanın içinden +Z yönünde geçip
gövdenin taban plakasındaki yerel pedlere girer: ped Ø10, z = −20 … −12, pilot delik Ø2.5,
derinlik 7 mm.

| Parça | Vida 1 | Vida 2 |
|---|---|---|
| Sol kabza | (12.0, 8.0) | (38.0, 4.0) |
| Sağ kabza | (124.0, 8.0) | (98.0, 4.0) |

İkisi de kabzanın z = −20'deki düz kök izinin ve gövdenin taban yüzeyinin ortak alanı
içindedir. Pedler z = −20 … −12 bandında kalır; 3.2'deki kart direkleri (z = −18.5 … 0)
ile aynı XY bölgesinde olsalar bile ikisi tek gövde olarak birleşir, çakışma sorunu
oluşmaz. 4.4'teki kapak vidası kuleleri (y = 30 ve 105, z = 16 … 23) çok uzakta.

**Hizalama pimi yok.** Kabza düz kök yüzü tablada basıldığı için kök yüzünden dışarı
çıkacak bir pim bası düzleminin altına düşerdi. İki vida zaten dönmeyi engelliyor.

Kabzanın kökü z = −30 … −20 arasında **dolu** basılır; vida yuvaları bu dolu bölgede durur,
böylece serbest kule sorunu oluşmaz. Vida başı için Ø6.5 havşa z = −30 … −26, geçme deliği
Ø3.4 z = −26 … −20. Kalan hacim (z < −30) 2.5 mm duvarlı ve içi boştur.

## 7. Üretim ve baskı yönü

| Parça | Baskı yönü | Destek |
|---|---|---|
| `controller_shell` | Ağzı yukarı, tabanı tablada | Yok |
| `controller_lid` | Üst yüzü tablada | Yok |
| `controller_grip_left` / `_right` | Düz kök yüzü (z = −20 kesiti) tablada | Yok |
| `screen_shim_*` | Düz | Yok |

**Kabzalar neden ayrı parça:** kabza gövdeden aşağı doğru uzanıyor. Gövde ağzı yukarı
basıldığında kabzanın her katmanı havaya sarkar; gövde ters çevrildiğinde ise 136 mm'lik iç
zemin tavan olur ve köprülenemez. Hangi yönde dizilirse dizilsin tek parça destek istiyor.
Ayrı basılan kabza, düz kök yüzü tablada dururken yukarı doğru daralan bir kubbedir ve hiç
destek almaz; ayrıca ergonomi tutmazsa yalnız kabza yeniden basılıyor ve istenirse TPU veya
farklı renk kullanılabiliyor.

Tabla gereksinimi: en büyük parça `controller_lid`, 154.4 × 146.4 mm. 220 × 220 tablaya
sığar.

## 8. Uygulama

`mechanical/controller/controller_case.py` — projedeki diğer parçalarla aynı kalıp
(`manifold3d` + `numpy` + `trimesh`, modül başında docstring, `build_*()` fonksiyonları,
`main()` içinde argparse).

Üretilen dosyalar:

- `controller_shell.stl`
- `controller_lid.stl`
- `controller_grip_left.stl`, `controller_grip_right.stl`
- `screen_shim_133.stl`, `screen_shim_138.stl`, `screen_shim_143.stl`
- `controller_case_preview.png`

Bölüm 3'teki bütün ölçüler dosyanın başında adlandırılmış sabitler olarak durur; hiçbiri
fonksiyon gövdesine gömülmez.

### 8.1 Doğrulama

`--check mechanical/controller/old/` bayrağı eski iki STL'i okur ve şunları karşılaştırır:

1. Kart direklerinin XY merkezleri — sapma > 0.10 mm ise hata.
2. Joystick deliklerinin X merkezleri — sapma > 0.30 mm ise hata. (Y kasıtlı olarak
   değiştiği için kontrol edilmez.)
3. Ekran deliğinin ve omzunun merkezi — sapma > 0.30 mm ise hata.
4. Eski gövdenin 3.4'teki kanal bölgesinde açık bıraktığı hacim, yeni gövde ve yeni kapakta
   da tamamen açık mı — kesişim hacmi > 1 mm³ ise hata.
5. Yeni kapağın joystick delikleri, eski kapağın deliklerini tamamen kapsıyor mu.

Ayrıca geometri kontrolü: her parça su geçirmez (`is_watertight`) ve tek gövde
(`body_count == 1`) olmalı.

### 8.2 Montaj sırası

1. `screen_shim`'i karta yapıştır, OLED modülünü üstüne bastır.
2. Kartı gövdenin dört direğine 4 × M3 sac vidası ile tuttur.
3. Kapağı geçir, 4 × M3 × 16 ile sık.
4. Kabzaları 2 × M3 × 14 ile gövdeye bağla.
