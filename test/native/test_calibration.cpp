#include <cassert>
#include <cstdio>
#include <cstring>
#include "calibration.h"

int main()
{
    assert(sizeof(calibration::Record) == 20);
    // Flash word olarak yazildigi icin boyut 4'un kati olmali.
    assert(sizeof(calibration::Record) % 4 == 0);

    calibration::Record r{};
    r.magic = calibration::MAGIC;
    r.version = calibration::VERSION;
    r.accelOffsetX = -12;
    r.accelOffsetY = 34;
    r.gyroBiasX = 5;
    r.gyroBiasY = -6;
    r.gyroBiasZ = 7;
    calibration::finalize(r);

    assert(calibration::isValid(r));

    // Tek alan bozulursa gecersiz olmali.
    calibration::Record bad = r;
    bad.accelOffsetX = 0;
    assert(!calibration::isValid(bad));

    // Yanlis magic gecersiz.
    calibration::Record wrongMagic = r;
    wrongMagic.magic = 0xDEADBEEF;
    assert(!calibration::isValid(wrongMagic));

    // Yanlis surum gecersiz.
    calibration::Record wrongVersion = r;
    wrongVersion.version = calibration::VERSION + 1;
    calibration::finalize(wrongVersion);
    assert(!calibration::isValid(wrongVersion));

    // Silinmis flash (hepsi 0xFF) gecersiz.
    calibration::Record erased;
    memset(&erased, 0xFF, sizeof(erased));
    assert(!calibration::isValid(erased));

    printf("test_calibration: OK\n");
    return 0;
}
