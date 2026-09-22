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

| Özellik | Merkez | Ölçü |
|---|---|---|
| Sol joystick | (26.94, 50.32) | Ø30.5 |
| Sağ joystick | (108.69, 51.32) | Ø31.0 |
| Ekran penceresi | (107.19, 113.32) | 38.0 × 12.5 |
| Kapak vidası (sol) | (4.19, 67.47) | Ø4 |
| Kapak vidası (sağ) | (130.19, 67.47) | Ø4 |

### 3.4 Üst kenar profili (kapak dış hattı, D çerçevesinde)

Üst kenar düz değil; ortasında basamaklı bir bant ve onun içinde bir kablo yuvası var:

- y = 136.0 (tam kenar), x < 39.4 ve x > 94.6 aralıklarında
- x ≈ 39.4 → 45.7 arasında pahlanarak y = 128.3'e iner
- y = 128.3 bandı x ≈ 45.7 … 89.3 arası
- x ≈ 89.3 → 94.6 arasında pahlanarak y = 136.0'ya çıkar
- Bandın içinde **x = 63.0 … 74.6, y = 120.3'e kadar inen yuva** — micro-USB kablosu
  (11.6 mm genişlik, 15.7 mm derinlik, merkez x = 68.8)

Gövde tarafında da aynı bandın karşılığı var (üst duvar z = 0…16 aralığında y = 129.0'a
çekilmiş).

### 3.5 Eski ekran desteği (kaldırılacak)

Gövdede x = 122.8…133.5, y = 107.6…119.8, z = 7.4…14.4 ölçülerinde bir blok var. Ekranın
yalnızca sağ ucunu destekliyor; yamukluğun sebebi bu. Yeni tasarımda kaldırılıyor, yerine
Bölüm 5'teki tabla geçiyor.

## 4. Yeni gövde

### 4.1 İç hacim

Kart cebi, direk deseninin ağırlık merkezine (68.00, 67.63) oturtulmuş **136.0 × 136.0 mm**
kare. D çerçevesinde x = 0.0 … 136.0, y = −0.37 … 135.63. 133 mm'lik kartın çevresinde her
yönde ≥ 1.5 mm boşluk kalır. Eski cep 132.0 × 133.7 idi ve karta göre dardı.

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
- Joystick delikleri: ikisi de **Ø33**, merkezleri **(26.94, 50.82)** ve **(108.69, 50.82)**.
  Eski deliklerin Y'si 1 mm kaçıktı (50.32 / 51.32); ortak Y'ye alınıp çap 33'e çıkarılınca
  ikisi de içinde kalıyor ve göze simetrik geliyor. X değerleri ölçülen haliyle korunuyor.
- Her joystick deliğinin çevresinde **Ø46, 1.2 mm derin küresel çukur** (başparmak yuvası).
- Üst kenar profili ve USB yuvası: 3.4'teki koordinatlarla birebir.
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

Gövde tarafı Ø6 kule + Ø2.5 pilot, kapak tarafı Ø3.4 geçme + Ø6 × 2.0 havşa. Kuleler dış
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

- Kapak alt yüzünde **39.2 × 13.2 mm, z = 17.0 … 21.0 (4 mm derin) cep**. Modülün PCB üst
  yüzü bu cebin tavanına dayanır.
- Cebin içinden geçen pencere **36.5 × 10.5 mm** — çevrede 1.35 mm dudak kalır, modül
  yukarı düşmez, PCB kenarı gizlenir.
- Kapak üst yüzünde pencerenin çevresinde **46 × 20 mm, 1.0 mm gömme panel alanı**. Düz
  basılmış bu çerçeve göz için referans olur; modülde kalan birkaç onda derecelik kaçıklık
  okunmaz.
- Hepsi 3.3'teki (107.19, 113.32) merkezine hizalı.

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
derinlik 7 mm. Ek olarak her kabzanın kök yüzünde 1 adet Ø4 × 6 hizalama pimi, gövde
tabanındaki Ø4.2 × 6.5 körlü deliğe oturur — kabza dönmez, kesme yükü vidadan alınır.

| Parça | Vida 1 | Vida 2 | Pim |
|---|---|---|---|
| Sol kabza | (12.0, 8.0) | (38.0, 4.0) | (26.0, 4.0) |
| Sağ kabza | (124.0, 8.0) | (98.0, 4.0) | (110.0, 4.0) |

Üçü de kabzanın z = −20'deki düz kök izinin ve gövdenin taban yüzeyinin ortak alanı
içindedir. Pedler z = −20 … −12 bandında kalır; 3.2'deki kart direkleri (z = −18.5 … 0)
ile aynı XY bölgesinde olsalar bile ikisi tek gövde olarak birleşir, çakışma sorunu
oluşmaz. 4.4'teki kapak vidası kuleleri (y = 30 ve 105, z = 16 … 23) çok uzakta.

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
3. Ekran penceresinin merkezi — sapma > 0.30 mm ise hata.
4. USB yuvasının X aralığı ve üst kenar bandının Y basamakları — sapma > 0.30 mm ise hata.
5. Yeni kapağın joystick delikleri, eski kapağın deliklerini tamamen kapsıyor mu.

Ayrıca geometri kontrolü: her parça su geçirmez (`is_watertight`) ve tek gövde
(`body_count == 1`) olmalı.

### 8.2 Montaj sırası

1. `screen_shim`'i karta yapıştır, OLED modülünü üstüne bastır.
2. Kartı gövdenin dört direğine 4 × M3 sac vidası ile tuttur.
3. Kapağı geçir, 4 × M3 × 16 ile sık.
4. Kabzaları 2 × M3 × 14 ile gövdeye bağla.
