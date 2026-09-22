#include <Adafruit_BMP280.h>
#include <Arduino.h>
#include <DallasTemperature.h>
#include <LoRa_E22.h>
#include <OneWire.h>
#include <Servo.h>
#include <Wire.h>
#include "radio_protocol.h"
#include "arming.h"
#include "calibration.h"

// applyFailsafe dosyada readGy85'ten sonra tanimli; kalibrasyon
// fonksiyonlari (dosyanin ustunde) onu cagirdigi icin ileri bildirim.
void applyFailsafe();

#ifndef USE_GPS
#define USE_GPS 0
#endif

#if USE_GPS
#include <TinyGPSPlus.h>
#endif

#define ADXL345_ADDRESS 0x53
#define ADXL345_POWER_CTL 0x2D
#define ADXL345_DATAX0 0x32

#define ITG3205_ADDRESS 0x68
#define ITG3205_PWR_MGMT 0x3E
#define ITG3205_DATA_REG 0x1D

#define QMC5883L_ADDRESS 0x0D
#define QMC5883L_DATA_REG 0x00

// Breakout'larda CSB/SDO kart uzerinde cekili oldugu icin adres modele gore
// degisiyor; ikisi de denenir.
#define BMP280_ADDRESS_PRIMARY 0x76
#define BMP280_ADDRESS_SECONDARY 0x77

Servo myESC;
Servo servoAIL;
Servo servoELE;
Servo servoRUD;
#define PIN_ESC PA1
#define PIN_SERVO_AIL PA6
#define PIN_SERVO_ELE PA7
#define PIN_SERVO_RUD PB0
#define PIN_LED PC13
#define PIN_DS18_BATT PA5
#define PIN_DS18_ESC PB1
#define PIN_VBAT_SENSE PA4
#if USE_GPS
#define PIN_GPS_TX PA2
#define PIN_GPS_RX PA3
#endif

#define LORA_M0 PA15
#define LORA_M1 PA12
#define LORA_AUX PA11
LoRa_E22 e22(&Serial1, LORA_AUX, LORA_M0, LORA_M1, UART_BPS_RATE_9600);

const int MIN_THROTTLE = 1100;
const int MAX_THROTTLE = 1940;
// Kumanda cubugunun tam salinimi servoyu 0-180 arasi suruyordu; bu kadar buyuk
// bir yol kumanda yuzeylerinin plastik baglantilarini zorluyor. Merkez 90 derece
// sabit kalacak sekilde yolu yariya indiriyoruz: 45-135 derece.
const int SERVO_CENTER_DEG = 90;
const int SERVO_TRAVEL_DEG = 45;
const int SERVO_MIN_DEG = SERVO_CENTER_DEG - SERVO_TRAVEL_DEG;
const int SERVO_MAX_DEG = SERVO_CENTER_DEG + SERVO_TRAVEL_DEG;

// applyOutputs() bu degerleri onbellek olarak kullanip gereksiz servo
// yazimlarini eliyor. applyFailsafe() servolari fiziksel olarak merkeze
// aldigi icin onbellegi de oradan guncellemek zorunda; yoksa cubuk ayni
// yerdeyse servo bir daha hic komut almaz.
int lastServoAIL = SERVO_CENTER_DEG;
int lastServoELE = SERVO_CENTER_DEG;
int lastServoRUD = SERVO_CENTER_DEG;

// Ust bacak = besleme kablosuna seri eklenen 330k.
// Alt bacak = kart uzerindeki R7 (47k), PA4 ile GND arasinda.
const float VBAT_DIVIDER_R_TOP = 330000.0f;
const float VBAT_DIVIDER_R_BOTTOM = 47000.0f;
const float ADC_REF_V = 3.3f;
const float ADC_MAX_COUNTS = 4095.0f;

using radio::ControlPacket;
using radio::TelemetryPacket;
using radio::TelemetryRequestPacket;

ControlPacket receivedPacket;
unsigned long lastTelemetryTime = 0;
unsigned long lastPacketTime = 0;

const unsigned long RX_TIMEOUT_MS = 300;
// Link uzun sure giderse disarm et. 300 ms'lik failsafe gazi zaten minimuma
// cekiyor; bu esik ancak baglanti gercekten koptuysa devreye girer.
const unsigned long DISARM_ON_LINK_LOSS_MS = 5000;

// Boot'ta PC13'te basilan kurulum kodlari.
const uint8_t LORA_STATUS_BEGIN_FAILED = 1;
const uint8_t LORA_STATUS_CONFIG_READ_FAILED = 2;
const uint8_t LORA_STATUS_CONFIG_WRITTEN = 3;
const uint8_t LORA_STATUS_CONFIG_OK = 4;

const unsigned long TELEMETRY_REQ_TIMEOUT_MS = 3000;
arming::GestureDetector armDetector;

// Kalibrasyon kaydi flash sektor 7'de (0x08060000, 128 KB). Firmware 41 KB
// ve sektor 0-2'de duruyor; sektor 7 firmware buyuse bile cakismaz.
#define CALIBRATION_FLASH_ADDRESS 0x08060000UL
#define CALIBRATION_FLASH_SECTOR FLASH_SECTOR_7
// Sektor 7 ancak 512 KB flash'li yongada var. Ucuz BlackPill'lerin bir kismi
// F411CC (256 KB) ya da klon yonga tasiyor; o yongalarda bu adresi OKUMAK
// bile bus fault uretir ve setup burada olur, LoRa hic kurulmaz.
#define CALIBRATION_FLASH_MIN_KB 512
bool calibrationFlashOk = true;

int16_t accelOffsetX = 0;
int16_t accelOffsetY = 0;
int16_t gyroBiasX = 0;
int16_t gyroBiasY = 0;
int16_t gyroBiasZ = 0;
bool calibrationLoaded = false;

// Kalibrasyon orneklemesi loop()'u bloklamaz: her turda suresi gelen bir
// ornek alinir. Normal IMU araligi 50 ms, burada 5 ms kullaniliyor.
const unsigned long CAL_SAMPLE_INTERVAL_MS = 5;
const uint8_t CAL_SAMPLE_TARGET = 16;
bool calSampling = false;
uint8_t calSampleCount = 0;
int32_t calAccumAx = 0, calAccumAy = 0;
int32_t calAccumGx = 0, calAccumGy = 0, calAccumGz = 0;
unsigned long lastCalSampleMs = 0;

uint8_t pendingCommand = 0;
uint8_t lastCommandSeq = 0;
bool commandSeqValid = false;

uint8_t payloadBuffer[64];
uint8_t payloadIndex = 0;
uint8_t parserState = 0;
uint8_t incomingPacketType = 0;
uint8_t incomingPayloadLength = 0;
bool telemetryRequested = false;
uint8_t lastTelemetryReqSeq = 0;

OneWire oneWireBatt(PIN_DS18_BATT);
DallasTemperature ds18Batt(&oneWireBatt);
OneWire oneWireEsc(PIN_DS18_ESC);
DallasTemperature ds18Esc(&oneWireEsc);

unsigned long lastTempRequestMs = 0;
const unsigned long TEMP_CONVERSION_INTERVAL_MS = 300;
int16_t battTempCentiC = INT16_MIN;
int16_t escTempCentiC = INT16_MIN;

int16_t imuAx = 0, imuAy = 0, imuAz = 0;
int16_t imuGx = 0, imuGy = 0, imuGz = 0;
int16_t imuHeading = 0;
unsigned long lastImuReadMs = 0;
const unsigned long IMU_READ_INTERVAL_MS = 50;

Adafruit_BMP280 bmp;
static bool bmpFound = false;
uint32_t baroPressurePa = 0;
int16_t baroTempCentiC = INT16_MIN;
unsigned long lastBaroReadMs = 0;
const unsigned long BARO_READ_INTERVAL_MS = 100;

#if USE_GPS
TinyGPSPlus gps;
#endif
int32_t gpsLatE7 = 0;
int32_t gpsLonE7 = 0;
uint8_t gpsFix = 0;
uint8_t gpsSats = 0;

void sendFrame(uint8_t packetType, const void *payload, uint8_t payloadLength);

// Yonganin gercek flash boyutu (KB). Kart tanimina degil, silikona sorar.
static uint32_t flashSizeKb()
{
    return (uint32_t)(*(volatile uint16_t *)FLASHSIZE_BASE);
}

void loadCalibrationFromFlash()
{
    if (flashSizeKb() < CALIBRATION_FLASH_MIN_KB)
    {
        // Kayit alani bu yongada yok. Okumaya kalkmak setup'i oldururdu.
        calibrationFlashOk = false;
        calibrationLoaded = false;
        return;
    }

    calibration::Record record;
    memcpy(&record, (const void *)CALIBRATION_FLASH_ADDRESS, sizeof(record));

    if (!calibration::isValid(record))
    {
        calibrationLoaded = false;
        return;
    }

    accelOffsetX = record.accelOffsetX;
    accelOffsetY = record.accelOffsetY;
    gyroBiasX = record.gyroBiasX;
    gyroBiasY = record.gyroBiasY;
    gyroBiasZ = record.gyroBiasZ;
    calibrationLoaded = true;
}

// DIKKAT: sektor silme ~1-2 saniye surer ve bu sirada flash veriyolu
// durdugu icin kod calismaz. Cagiran taraf once gazi minimuma cekmeli.
bool saveCalibrationToFlash()
{
    if (!calibrationFlashOk)
    {
        return false;
    }

    calibration::Record record{};
    record.magic = calibration::MAGIC;
    record.version = calibration::VERSION;
    record.accelOffsetX = accelOffsetX;
    record.accelOffsetY = accelOffsetY;
    record.gyroBiasX = gyroBiasX;
    record.gyroBiasY = gyroBiasY;
    record.gyroBiasZ = gyroBiasZ;
    calibration::finalize(record);

    // Sektor silme sirasinda kesmeler calismaz ve stm32duino'nun Servo'su
    // kesme tabanli oldugu icin sinyal hatlari o anki seviyede donar.
    // Surekli HIGH gecerli bir darbe degil; analog servoyu durduruculara
    // dayayip kilitli rotor akimina sokabilir. Hatlari birakiyoruz:
    // sinyal yoklugu servolarin pozisyonlarini korumasi demek.
    servoAIL.detach();
    servoELE.detach();
    servoRUD.detach();
    digitalWrite(PIN_SERVO_AIL, LOW);
    digitalWrite(PIN_SERVO_ELE, LOW);
    digitalWrite(PIN_SERVO_RUD, LOW);

    HAL_FLASH_Unlock();

    FLASH_EraseInitTypeDef erase = {};
    erase.TypeErase = FLASH_TYPEERASE_SECTORS;
    erase.Sector = CALIBRATION_FLASH_SECTOR;
    erase.NbSectors = 1;
    erase.VoltageRange = FLASH_VOLTAGE_RANGE_3;

    bool ok = true;
    uint32_t sectorError = 0;
    if (HAL_FLASHEx_Erase(&erase, &sectorError) != HAL_OK)
    {
        Serial.print("[CAL] sektor silme hatasi: ");
        Serial.println(sectorError);
        ok = false;
    }
    else
    {
        // Record packed oldugu icin hizalamasi 1; dogrudan uint32_t olarak okumak
        // tanimsiz davranis. Once hizali bir tampona kopyalaniyor.
        const uint32_t wordCount = sizeof(calibration::Record) / 4;
        uint32_t words[sizeof(calibration::Record) / 4];
        memcpy(words, &record, sizeof(calibration::Record));
        for (uint32_t i = 0; i < wordCount; i++)
        {
            if (HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD,
                                  CALIBRATION_FLASH_ADDRESS + i * 4,
                                  words[i]) != HAL_OK)
            {
                ok = false;
                break;
            }
        }
    }

    HAL_FLASH_Lock();

    servoAIL.attach(PIN_SERVO_AIL);
    servoELE.attach(PIN_SERVO_ELE);
    servoRUD.attach(PIN_SERVO_RUD);
    // Servo::attach() iceride pinMode(pin, OUTPUT) yapiyor. Kart servo
    // sinyallerini 4.7k pull-up ile 5 V'a cektigi icin acik kollektore geri
    // almak zorundayiz; yoksa seviye cevirici kayboluyor.
    pinMode(PIN_SERVO_AIL, OUTPUT_OPEN_DRAIN);
    pinMode(PIN_SERVO_ELE, OUTPUT_OPEN_DRAIN);
    pinMode(PIN_SERVO_RUD, OUTPUT_OPEN_DRAIN);
    servoAIL.write(SERVO_CENTER_DEG);
    servoELE.write(SERVO_CENTER_DEG);
    servoRUD.write(SERVO_CENTER_DEG);
    lastServoAIL = SERVO_CENTER_DEG;
    lastServoELE = SERVO_CENTER_DEG;
    lastServoRUD = SERVO_CENTER_DEG;
    return ok;
}

void startCalibration()
{
    calSampling = true;
    calSampleCount = 0;
    calAccumAx = 0;
    calAccumAy = 0;
    calAccumGx = 0;
    calAccumGy = 0;
    calAccumGz = 0;
    lastCalSampleMs = 0;
}

void clearCalibration()
{
    // Devam eden ornekleme iptal: yoksa ~80 ms sonra serviceCalibration
    // hem RAM'i hem flash'i tekrar yazip bu silmeyi sessizce geri alirdi.
    calSampling = false;
    accelOffsetX = 0;
    accelOffsetY = 0;
    gyroBiasX = 0;
    gyroBiasY = 0;
    gyroBiasZ = 0;
    calibrationLoaded = false;
    applyFailsafe();
    // Gecerli ama tum ofsetleri sifir olan bir kayit yazilir. Bir sonraki
    // boot'ta yuklenir; STATUS_CALIBRATED ofsetlerin hepsi sifir oldugu
    // icin yine de set edilmez.
    calibrationLoaded = saveCalibrationToFlash();
    if (!calibrationLoaded)
    {
        Serial.println("[CAL] silme icin flash yazimi basarisiz");
    }
    lastPacketTime = millis();
    // Durus boyunca jest zamanlamasi guvenilmez; pilot jesti bastan yapsin.
    armDetector.reset(millis());
}

void applyOutputs(const ControlPacket &packet)
{
    const int center = 2048;
    const int deadband = 45;
    const float filterAlpha = 0.35f;
    static float filteredLX = 2048.0f;
    static float filteredLY = 0.0f;
    static float filteredRX = 2048.0f;
    static float filteredRY = 2048.0f;

    filteredLX = filteredLX + filterAlpha * ((float)packet.LX - filteredLX);
    filteredLY = filteredLY + filterAlpha * ((float)packet.LY - filteredLY);
    filteredRX = filteredRX + filterAlpha * ((float)packet.RX - filteredRX);
    filteredRY = filteredRY + filterAlpha * ((float)packet.RY - filteredRY);

    int lx = (int)filteredLX;
    int ly = (int)filteredLY;
    int rx = (int)filteredRX;
    int ry = (int)filteredRY;

    if (abs(lx - center) < deadband)
    {
        lx = center;
    }
    if (abs(rx - center) < deadband)
    {
        rx = center;
    }
    if (abs(ry - center) < deadband)
    {
        ry = center;
    }

    int s1 = map(constrain(rx, 0, 4095), 0, 4095, SERVO_MIN_DEG, SERVO_MAX_DEG);
    int s2 = map(constrain(ry, 0, 4095), 0, 4095, SERVO_MIN_DEG, SERVO_MAX_DEG);
    int s3 = map(constrain(lx, 0, 4095), 0, 4095, SERVO_MIN_DEG, SERVO_MAX_DEG);
    int escUs = map(constrain(ly, 0, 4095), 0, 4095, MIN_THROTTLE, MAX_THROTTLE);

    // Disarm durumunda gaz cubugu nerede olursa olsun ESC minimumda kalir.
    // Bu ayni zamanda ESC'nin kendi arming'ini duzgun yapmasini saglar.
    myESC.writeMicroseconds(armDetector.isArmed() ? escUs : MIN_THROTTLE);

    if (abs(s1 - lastServoAIL) >= 2)
    {
        servoAIL.write(s1);
        lastServoAIL = s1;
    }
    if (abs(s2 - lastServoELE) >= 2)
    {
        servoELE.write(s2);
        lastServoELE = s2;
    }
    if (abs(s3 - lastServoRUD) >= 2)
    {
        servoRUD.write(s3);
        lastServoRUD = s3;
    }
}

void applyFailsafe()
{
    myESC.writeMicroseconds(MIN_THROTTLE);
    servoAIL.write(SERVO_CENTER_DEG);
    servoELE.write(SERVO_CENTER_DEG);
    servoRUD.write(SERVO_CENTER_DEG);
    lastServoAIL = SERVO_CENTER_DEG;
    lastServoELE = SERVO_CENTER_DEG;
    lastServoRUD = SERVO_CENTER_DEG;
}

bool parseIncomingByte(uint8_t b)
{
    switch (parserState)
    {
    case 0:
        if (b == radio::PREAMBLE_1)
        {
            parserState = 1;
        }
        break;
    case 1:
        if (b == radio::PREAMBLE_2)
        {
            parserState = 2;
        }
        else if (b == radio::PREAMBLE_1)
        {
            parserState = 1;
        }
        else
        {
            parserState = 0;
        }
        break;
    case 2:
        incomingPacketType = b;
        parserState = 3;
        break;
    case 3:
        incomingPayloadLength = b;
        payloadIndex = 0;
        if (incomingPayloadLength == 0 || incomingPayloadLength > sizeof(payloadBuffer))
        {
            parserState = 0;
        }
        else
        {
            parserState = 4;
        }
        break;
    case 4:
        payloadBuffer[payloadIndex++] = b;
        if (payloadIndex >= incomingPayloadLength)
        {
            parserState = 5;
        }
        break;
    case 5:
    {
        uint8_t checksum = radio::computeFrameChecksum(incomingPacketType, incomingPayloadLength, payloadBuffer);
        parserState = 0;
        if (checksum == b && incomingPacketType == radio::PACKET_TYPE_CONTROL && incomingPayloadLength == sizeof(ControlPacket))
        {
            memcpy(&receivedPacket, payloadBuffer, sizeof(ControlPacket));
            return true;
        }
        if (checksum == b && incomingPacketType == radio::PACKET_TYPE_TELEMETRY_REQ && incomingPayloadLength == sizeof(TelemetryRequestPacket))
        {
            TelemetryRequestPacket req;
            memcpy(&req, payloadBuffer, sizeof(TelemetryRequestPacket));
            lastTelemetryReqSeq = req.sequence;
            telemetryRequested = true;
        }
        if (checksum == b && incomingPacketType == radio::PACKET_TYPE_COMMAND &&
            incomingPayloadLength == sizeof(radio::CommandPacket))
        {
            radio::CommandPacket cmd;
            memcpy(&cmd, payloadBuffer, sizeof(cmd));

            if (cmd.command == radio::COMMAND_DISARM)
            {
                // Acil durdurma tekrar elemesinden MUAF. Iki kez disarm etmek
                // zararsiz, ama bir sequence carpismasi yuzunden yutulmasi
                // pilotun disarm sandigi bir ucakta pervaneyi canli birakir.
                // Ayrica tek yuvali pendingCommand'a hic girmiyor ki
                // sonradan gelen baska bir komut onu ezmemeli.
                lastCommandSeq = cmd.sequence;
                commandSeqValid = true;
                // Acil durdurmadan sonra kuyruktaki flash komutu calismamali:
                // 1-2 saniyelik durus tam da radyoyu en cok istedigimiz anda
                // sagir birakir.
                pendingCommand = 0;
                armDetector.disarm(millis());
                applyFailsafe();
            }
            else if (!commandSeqValid || cmd.sequence != lastCommandSeq)
            {
                // Yalniz flash yazan komutlar icin tekrar elemesi: ayni
                // sequence iki kez uygulanirsa ikinci bir silme cevrimi ve
                // 1-2 saniyelik durus olusur.
                lastCommandSeq = cmd.sequence;
                commandSeqValid = true;
                pendingCommand = cmd.command;
            }
        }
        break;
    }
    default:
        parserState = 0;
        break;
    }
    return false;
}

float getBatteryVoltage()
{
    uint32_t sum = 0;
    for (int i = 0; i < 8; i++)
    {
        sum += analogRead(PIN_VBAT_SENSE);
    }
    float adcCounts = (float)sum / 8.0f;
    float vSense = (adcCounts / ADC_MAX_COUNTS) * ADC_REF_V;
    return vSense * ((VBAT_DIVIDER_R_TOP + VBAT_DIVIDER_R_BOTTOM) / VBAT_DIVIDER_R_BOTTOM);
}

void updateDs18Temperatures()
{
    if (millis() - lastTempRequestMs < TEMP_CONVERSION_INTERVAL_MS)
    {
        return;
    }

    lastTempRequestMs = millis();

    float battC = ds18Batt.getTempCByIndex(0);
    float escC = ds18Esc.getTempCByIndex(0);

    battTempCentiC = (battC == DEVICE_DISCONNECTED_C) ? INT16_MIN : (int16_t)(battC * 100.0f);
    escTempCentiC = (escC == DEVICE_DISCONNECTED_C) ? INT16_MIN : (int16_t)(escC * 100.0f);

    ds18Batt.requestTemperatures();
    ds18Esc.requestTemperatures();
}

static bool adxlFound = false;
static bool itgFound = false;
static bool qmcFound = false;

static bool probeI2C(uint8_t addr)
{
    Wire.beginTransmission(addr);
    return Wire.endTransmission() == 0;
}

void initGy85()
{
    adxlFound = probeI2C(ADXL345_ADDRESS);
    itgFound = probeI2C(ITG3205_ADDRESS);
    qmcFound = probeI2C(QMC5883L_ADDRESS);

    if (adxlFound)
    {
        Wire.beginTransmission(ADXL345_ADDRESS);
        Wire.write(ADXL345_POWER_CTL);
        Wire.write(0x08);
        Wire.endTransmission();
    }

    if (itgFound)
    {
        Wire.beginTransmission(ITG3205_ADDRESS);
        Wire.write(0x16);
        Wire.write(0x18);
        Wire.endTransmission();
        Wire.beginTransmission(ITG3205_ADDRESS);
        Wire.write(ITG3205_PWR_MGMT);
        Wire.write(0x01);
        Wire.endTransmission();
    }

    if (qmcFound)
    {
        Wire.beginTransmission(QMC5883L_ADDRESS);
        Wire.write(0x0B);
        Wire.write(0x01);
        Wire.endTransmission();
        Wire.beginTransmission(QMC5883L_ADDRESS);
        Wire.write(0x20);
        Wire.write(0x40);
        Wire.endTransmission();
        Wire.beginTransmission(QMC5883L_ADDRESS);
        Wire.write(0x21);
        Wire.write(0x01);
        Wire.endTransmission();
        Wire.beginTransmission(QMC5883L_ADDRESS);
        Wire.write(0x09);
        Wire.write(0x01);
        Wire.endTransmission();
    }
}

void initBmp280()
{
    bmpFound = bmp.begin(BMP280_ADDRESS_PRIMARY) || bmp.begin(BMP280_ADDRESS_SECONDARY);
    if (!bmpFound)
    {
        return;
    }

    bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,
                    Adafruit_BMP280::SAMPLING_X2,
                    Adafruit_BMP280::SAMPLING_X16,
                    Adafruit_BMP280::FILTER_X16,
                    Adafruit_BMP280::STANDBY_MS_63);
}

void readBmp280()
{
    if (!bmpFound)
    {
        return;
    }

    float pressure = bmp.readPressure();
    float temperature = bmp.readTemperature();

    if (pressure > 0.0f)
    {
        baroPressurePa = (uint32_t)pressure;
        baroTempCentiC = (int16_t)(temperature * 100.0f);
    }
}

void readGy85(int16_t &ax, int16_t &ay, int16_t &az,
              int16_t &gx, int16_t &gy, int16_t &gz,
              int16_t &heading)
{
    if (adxlFound)
    {
        Wire.beginTransmission(ADXL345_ADDRESS);
        Wire.write(ADXL345_DATAX0);
        Wire.endTransmission(false);
        Wire.requestFrom(ADXL345_ADDRESS, 6);
        if (Wire.available() >= 6)
        {
            uint8_t xLo = Wire.read(), xHi = Wire.read();
            uint8_t yLo = Wire.read(), yHi = Wire.read();
            uint8_t zLo = Wire.read(), zHi = Wire.read();
            ax = (int16_t)(xLo | (xHi << 8)) / 4;
            ay = (int16_t)(yLo | (yHi << 8)) / 4;
            az = (int16_t)(zLo | (zHi << 8)) / 4;
        }
        Wire.endTransmission(true);
    }

    if (itgFound)
    {
        Wire.beginTransmission(ITG3205_ADDRESS);
        Wire.write(ITG3205_DATA_REG);
        Wire.endTransmission(false);
        Wire.requestFrom(ITG3205_ADDRESS, 6);
        if (Wire.available() >= 6)
        {
            uint8_t xHi = Wire.read(), xLo = Wire.read();
            uint8_t yHi = Wire.read(), yLo = Wire.read();
            uint8_t zHi = Wire.read(), zLo = Wire.read();
            gx = (int16_t)((xHi << 8) | xLo);
            gy = (int16_t)((yHi << 8) | yLo);
            gz = (int16_t)((zHi << 8) | zLo);
        }
        Wire.endTransmission(true);
    }

    if (qmcFound)
    {
        Wire.beginTransmission(QMC5883L_ADDRESS);
        Wire.write(QMC5883L_DATA_REG);
        Wire.endTransmission(false);
        Wire.requestFrom(QMC5883L_ADDRESS, 6);
        if (Wire.available() >= 6)
        {
            uint8_t xLo = Wire.read(), xHi = Wire.read();
            uint8_t yLo = Wire.read(), yHi = Wire.read();
            Wire.read();
            Wire.read();
            int16_t mx = (int16_t)(xLo | (xHi << 8));
            int16_t my = (int16_t)(yLo | (yHi << 8));
            heading = (int16_t)(atan2((float)my * 0.092f, (float)mx * 0.092f) * 1800.0f / PI);
            if (heading < 0) heading += 3600;
        }
        Wire.endTransmission(true);
    }
}

void serviceCalibration()
{
    if (!calSampling)
    {
        return;
    }

    // Komut geldiginde disarm'di ama ornekleme ~80 ms suruyor ve bu sirada
    // pilot jesti tamamlayabilir. Flash yazimi tum MCU'yu 1-2 saniye
    // durdurdugu icin armed durumda asla baslamamali.
    if (armDetector.isArmed())
    {
        calSampling = false;
        Serial.println("[CAL] armed olundu, kalibrasyon iptal");
        return;
    }

    if (millis() - lastCalSampleMs < CAL_SAMPLE_INTERVAL_MS)
    {
        return;
    }
    lastCalSampleMs = millis();

    int16_t ax = 0, ay = 0, az = 0, gx = 0, gy = 0, gz = 0, heading = 0;
    readGy85(ax, ay, az, gx, gy, gz, heading);

    calAccumAx += ax;
    calAccumAy += ay;
    calAccumGx += gx;
    calAccumGy += gy;
    calAccumGz += gz;
    calSampleCount++;

    if (calSampleCount < CAL_SAMPLE_TARGET)
    {
        return;
    }

    accelOffsetX = (int16_t)(calAccumAx / CAL_SAMPLE_TARGET);
    accelOffsetY = (int16_t)(calAccumAy / CAL_SAMPLE_TARGET);
    gyroBiasX = (int16_t)(calAccumGx / CAL_SAMPLE_TARGET);
    gyroBiasY = (int16_t)(calAccumGy / CAL_SAMPLE_TARGET);
    gyroBiasZ = (int16_t)(calAccumGz / CAL_SAMPLE_TARGET);
    calSampling = false;

    // Flash yazimi kodu ~1-2 saniye durdurur. Once gazi minimuma cek,
    // sonra donuste sahte failsafe tetiklenmesin diye saati tazele.
    applyFailsafe();
    calibrationLoaded = saveCalibrationToFlash();
    if (!calibrationLoaded)
    {
        // Flash'a yazilamadiysa RAM'deki ofsetleri de birak; telemetride
        // "kalibre degil" derken duzeltilmis veri gondermek yaniltici olur.
        accelOffsetX = 0;
        accelOffsetY = 0;
        gyroBiasX = 0;
        gyroBiasY = 0;
        gyroBiasZ = 0;
        Serial.println("[CAL] flash yazimi basarisiz, ofsetler sifirlandi");
    }
    lastPacketTime = millis();
    // Durus boyunca jest zamanlamasi guvenilmez; pilot jesti bastan yapsin.
    armDetector.reset(millis());
}

static int16_t subtractClamped(int16_t value, int16_t offset)
{
    const int32_t result = (int32_t)value - (int32_t)offset;
    if (result > INT16_MAX) return INT16_MAX;
    if (result < INT16_MIN) return INT16_MIN;
    return (int16_t)result;
}

uint8_t buildStatusFlags()
{
    uint8_t flags = 0;
    if (adxlFound) flags |= radio::STATUS_ACCEL_OK;
    if (itgFound) flags |= radio::STATUS_GYRO_OK;
    if (qmcFound) flags |= radio::STATUS_MAG_OK;
    if (bmpFound) flags |= radio::STATUS_BARO_OK;
    if (calibrationLoaded &&
        (accelOffsetX != 0 || accelOffsetY != 0 ||
         gyroBiasX != 0 || gyroBiasY != 0 || gyroBiasZ != 0))
    {
        flags |= radio::STATUS_CALIBRATED;
    }
    if (armDetector.isArmed()) flags |= radio::STATUS_ARMED;
    return flags;
}

void sendFrame(uint8_t packetType, const void *payload, uint8_t payloadLength)
{
    const uint8_t *payloadBytes = (const uint8_t *)payload;
    Serial1.write(radio::PREAMBLE_1);
    Serial1.write(radio::PREAMBLE_2);
    Serial1.write(packetType);
    Serial1.write(payloadLength);
    Serial1.write(payloadBytes, payloadLength);
    Serial1.write(radio::computeFrameChecksum(packetType, payloadLength, payloadBytes));
}

// BlackPill'in kart ustu LED'i PC13'te ve aktif dusuk.
void ledWrite(bool on)
{
    digitalWrite(PIN_LED, on ? LOW : HIGH);
}

// Setup'in her asamasindan sonra bir isaret. Takildigi yerde sayim durur,
// boylece hangi adimda oldugu disaridan gorulur. Her 5. isaret uzun yanar
// ki sayarken kaybolmayalim: uzun = 5, 10, ...
uint8_t bootStage = 0;

void bootMark()
{
    bootStage++;
    const bool longPulse = (bootStage % 5) == 0;
    ledWrite(true);
    delay(longPulse ? 500 : 120);
    ledWrite(false);
    delay(380);
}

// Boot'ta durum kodunu yanip sonerek bildirir. Sadece setup'ta cagrilir,
// bloklamasi sorun degil.
void blinkStatusCode(uint8_t count)
{
    for (uint8_t i = 0; i < count; i++)
    {
        ledWrite(true);
        delay(200);
        ledWrite(false);
        delay(200);
    }
    delay(700);
}

// Calisirken link durumunu gosterir:
//   1 Hz yavas yanip sonme -> kontrol paketi gelmiyor (failsafe)
//   sabit yanik            -> kontrol geliyor, telemetri istegi gelmiyor
//   saniyede cift blink    -> ikisi de geliyor
void updateStatusLed()
{
    const unsigned long now = millis();
    const bool controlAlive = (now - lastPacketTime) <= RX_TIMEOUT_MS;
    const bool telemetryAlive =
        lastTelemetryTime != 0 && (now - lastTelemetryTime) <= TELEMETRY_REQ_TIMEOUT_MS;

    if (!controlAlive)
    {
        ledWrite((now / 500) % 2 == 0);
    }
    else if (!telemetryAlive)
    {
        ledWrite(true);
    }
    else
    {
        const unsigned long phase = now % 1000;
        ledWrite(phase < 100 || (phase >= 200 && phase < 300));
    }
}

// PC13 LED'inde boot'ta kac kez yanip sonecegi. Ucakta baska teshis
// kanali yok: seri cikis PA2'de ve okumak icin USB-TTL gerekiyor.
uint8_t loraSetupStatus = LORA_STATUS_BEGIN_FAILED;

void setupLoRaWithLibrary()
{
    // Hangi yoldan cikarsak cikalim modulu normal moda birakiyoruz.
    // getConfiguration() modulu program moduna aliyor; yarida donulurse
    // modul orada kalir ve hic RF uretmez.
    if (!e22.begin())
    {
        loraSetupStatus = LORA_STATUS_BEGIN_FAILED;
        e22.setMode(MODE_0_NORMAL);
        return;
    }

    ResponseStructContainer c = e22.getConfiguration();
    if (c.status.code != E22_SUCCESS)
    {
        c.close();
        loraSetupStatus = LORA_STATUS_CONFIG_READ_FAILED;
        e22.setMode(MODE_0_NORMAL);
        return;
    }

    Configuration cfg = *(Configuration *)c.data;
    c.close();

    bool changed = false;

    if (cfg.SPED.uartBaudRate != UART_BPS_9600)
    {
        cfg.SPED.uartBaudRate = UART_BPS_9600;
        changed = true;
    }

    if (cfg.SPED.airDataRate != AIR_DATA_RATE_110_384)
    {
        cfg.SPED.airDataRate = AIR_DATA_RATE_110_384;
        changed = true;
    }

    if (cfg.TRANSMISSION_MODE.WORTransceiverControl != WOR_RECEIVER)
    {
        cfg.TRANSMISSION_MODE.WORTransceiverControl = WOR_RECEIVER;
        changed = true;
    }

    if (changed)
    {
        e22.setConfiguration(cfg, WRITE_CFG_PWR_DWN_SAVE);
        loraSetupStatus = LORA_STATUS_CONFIG_WRITTEN;
    }
    else
    {
        loraSetupStatus = LORA_STATUS_CONFIG_OK;
    }

    e22.setMode(MODE_0_NORMAL);
}

void setup()
{
    Serial.begin(115200);
    delay(100);

    pinMode(PIN_LED, OUTPUT);
    bootMark();  // 1 setup'a girildi
    pinMode(PIN_ESC, OUTPUT_OPEN_DRAIN);
    pinMode(PIN_VBAT_SENSE, INPUT_ANALOG);
    analogReadResolution(12);
    bootMark();  // 2 pin ayarlari
    pinMode(LORA_M0, OUTPUT);
    pinMode(LORA_M1, OUTPUT);
    pinMode(LORA_AUX, INPUT);

    digitalWrite(LORA_M0, LOW);
    digitalWrite(LORA_M1, LOW);
    delay(200);

    myESC.attach(PIN_ESC, MIN_THROTTLE, MAX_THROTTLE);
    myESC.writeMicroseconds(MIN_THROTTLE);

    servoAIL.attach(PIN_SERVO_AIL);
    servoELE.attach(PIN_SERVO_ELE);
    servoRUD.attach(PIN_SERVO_RUD);
    pinMode(PIN_SERVO_AIL, OUTPUT_OPEN_DRAIN);
    pinMode(PIN_SERVO_ELE, OUTPUT_OPEN_DRAIN);
    pinMode(PIN_SERVO_RUD, OUTPUT_OPEN_DRAIN);

    servoAIL.write(SERVO_CENTER_DEG);
    servoELE.write(SERVO_CENTER_DEG);
    servoRUD.write(SERVO_CENTER_DEG);
    bootMark();  // 3 ESC ve servolar

    ds18Batt.begin();
    ds18Esc.begin();
    ds18Batt.setWaitForConversion(false);
    ds18Esc.setWaitForConversion(false);
    ds18Batt.setResolution(10);
    ds18Esc.setResolution(10);
    ds18Batt.requestTemperatures();
    ds18Esc.requestTemperatures();
    lastTempRequestMs = millis();
    bootMark();  // 4 DS18B20

    Wire.setSCL(PB6);
    Wire.setSDA(PB7);
    Wire.begin();
    bootMark();  // 5 I2C veriyolu (UZUN)
    initGy85();
    bootMark();  // 6 GY-85
    initBmp280();
    bootMark();  // 7 BMP280
    loadCalibrationFromFlash();
    bootMark();  // 8 kalibrasyon flash
    Serial.print("[SETUP] Kalibrasyon: ");
    Serial.println(calibrationLoaded ? "yuklendi" : "yok");
    Serial.print("[SETUP] BMP280: ");
    Serial.println(bmpFound ? "OK" : "NA");
    Serial.print("[SETUP] GY-85: ADXL=");
    Serial.print(adxlFound ? "OK" : "NA");
    Serial.print(" ITG=");
    Serial.print(itgFound ? "OK" : "NA");
    Serial.print(" QMC=");
    Serial.println(qmcFound ? "OK" : "NA");

    Serial1.setTx(PA9);
    Serial1.setRx(PA10);
    bootMark();  // 9 Serial1 pinleri

#if USE_GPS
    Serial2.setTx(PIN_GPS_TX);
    Serial2.setRx(PIN_GPS_RX);
    Serial2.begin(9600);
#endif

    setupLoRaWithLibrary();
    bootMark();  // 10 LoRa kurulumu (UZUN)
    delay(1200);
    // LoRa kurulum sonucu PC13'te: 1 begin hatasi, 2 config okunamadi,
    // 3 ayar yazildi, 4 ayar zaten uygun.
    blinkStatusCode(loraSetupStatus);
    if (!calibrationFlashOk)
    {
        // 5 blink: yonga 512 KB'tan kucuk, kalibrasyon kaliciligi kapali.
        delay(500);
        blinkStatusCode(5);
    }

    armDetector.reset(millis());
    lastPacketTime = millis();
}

void loop()
{
    updateDs18Temperatures();

    if (pendingCommand != 0)
    {
        const uint8_t command = pendingCommand;
        pendingCommand = 0;

        switch (command)
        {
        case radio::COMMAND_CALIBRATE_LEVEL:
            // Armed'ken reddedilir: flash yazimi kodu saniyelerce durdurur.
            if (!armDetector.isArmed())
            {
                startCalibration();
            }
            break;
        case radio::COMMAND_CLEAR_CALIBRATION:
            if (!armDetector.isArmed())
            {
                clearCalibration();
            }
            break;
        // COMMAND_DISARM artik parseIncomingByte'da, paket alinir alinmaz
        // isleniyor (bkz. yukarida commandSeqValid blogu); burada tekrar
        // islenmiyor.
        default:
            break;
        }
    }

    serviceCalibration();

    uint8_t bytesProcessed = 0;
    while (Serial1.available() && bytesProcessed < 32)
    {
        if (parseIncomingByte((uint8_t)Serial1.read()))
        {
            lastPacketTime = millis();
            // Jest, STM32'nin kendi filtresinden ONCE, ham paket degerleriyle
            // cozuluyor; cift filtrelemenin gecikmesine takilmasin.
            armDetector.update(receivedPacket.LY, receivedPacket.RY, millis());
            applyOutputs(receivedPacket);
        }
        bytesProcessed++;
    }

#if USE_GPS
    while (Serial2.available())
    {
        gps.encode(Serial2.read());
    }
    if (gps.location.isUpdated() && gps.location.isValid())
    {
        gpsLatE7 = (int32_t)(gps.location.lat() * 10000000.0);
        gpsLonE7 = (int32_t)(gps.location.lng() * 10000000.0);
        gpsFix = 1;
    }
    else if (gps.location.age() > 5000)
    {
        gpsFix = 0;
    }
    gpsSats = gps.satellites.isValid() ? (uint8_t)constrain(gps.satellites.value(), 0, 255) : 0;
#endif

    if (telemetryRequested)
    {
        if (millis() - lastImuReadMs >= IMU_READ_INTERVAL_MS)
        {
            readGy85(imuAx, imuAy, imuAz, imuGx, imuGy, imuGz, imuHeading);
            lastImuReadMs = millis();
        }

        if (millis() - lastBaroReadMs >= BARO_READ_INTERVAL_MS)
        {
            readBmp280();
            lastBaroReadMs = millis();
        }

        TelemetryPacket telemetry;
        telemetry.voltageMv = (uint16_t)(getBatteryVoltage() * 1000.0f);
        telemetry.battTempCentiC = battTempCentiC;
        telemetry.escTempCentiC = escTempCentiC;
        telemetry.mpuAx = subtractClamped(imuAx, accelOffsetX);
        telemetry.mpuAy = subtractClamped(imuAy, accelOffsetY);
        telemetry.mpuAz = imuAz;
        telemetry.mpuGx = subtractClamped(imuGx, gyroBiasX);
        telemetry.mpuGy = subtractClamped(imuGy, gyroBiasY);
        telemetry.mpuGz = subtractClamped(imuGz, gyroBiasZ);
        telemetry.compassHeading = imuHeading;
        telemetry.gpsLatE7 = gpsLatE7;
        telemetry.gpsLonE7 = gpsLonE7;
        telemetry.gpsFix = gpsFix;
        telemetry.gpsSats = gpsSats;
        telemetry.pressurePa = baroPressurePa;
        telemetry.baroTempCentiC = baroTempCentiC;
        telemetry.statusFlags = buildStatusFlags();

        sendFrame(radio::PACKET_TYPE_TELEMETRY, &telemetry, sizeof(TelemetryPacket));

        telemetryRequested = false;
        lastTelemetryTime = millis();
    }

    if (millis() - lastPacketTime > RX_TIMEOUT_MS)
    {
        applyFailsafe();
    }

    if (millis() - lastPacketTime > DISARM_ON_LINK_LOSS_MS)
    {
        armDetector.disarm(millis());
    }

    updateStatusLed();
}
