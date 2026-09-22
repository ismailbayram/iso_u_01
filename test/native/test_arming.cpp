#include <cassert>
#include <cstdio>
#include "arming.h"

using arming::GestureDetector;
using arming::Phase;

static const uint16_t DOWN = 100;   // DOWN_THRESHOLD altinda
static const uint16_t UP = 3000;    // RELEASE_THRESHOLD ustunde
static const uint16_t MID = 2048;   // ikisinin de disinda

// Jesti tamamlar, armed'a gectigi turda true dondugunu dogrular.
static bool runFullGesture(GestureDetector &d, uint32_t startMs)
{
    bool armedEdge = false;
    armedEdge |= d.update(DOWN, DOWN, startMs);
    armedEdge |= d.update(UP, UP, startMs + 200);
    // Tutma, gercek bir 50 Hz linkin verdigi gibi 20 ms adimlarla paket
    // paket besleniyor: HOLD_MIN_SAMPLES artik tek bir paketle gecilemiyor.
    for (uint32_t t = startMs + 400; t <= startMs + 900; t += 20) {
        armedEdge |= d.update(DOWN, DOWN, t);
    }
    return armedEdge;
}

int main()
{
    // 1. Yeni detector armed degil.
    {
        GestureDetector d;
        d.reset(0);
        assert(!d.isArmed());
        assert(d.phase() == Phase::Idle);
    }

    // 2. Tam jest arm eder ve kenar tam bir kez gelir.
    {
        GestureDetector d;
        d.reset(0);
        assert(runFullGesture(d, 1000));
        assert(d.isArmed());
        // Zaten armed'ken tekrar kenar gelmez.
        assert(!d.update(DOWN, DOWN, 2000));
    }

    // 3. Tek asagi cevrimi arm etmez.
    {
        GestureDetector d;
        d.reset(0);
        d.update(DOWN, DOWN, 0);
        d.update(DOWN, DOWN, 600);
        assert(!d.isArmed());
    }

    // 4. Ikinci asagida yeterince tutulmazsa arm etmez.
    {
        GestureDetector d;
        d.reset(0);
        d.update(DOWN, DOWN, 0);
        d.update(UP, UP, 200);
        d.update(DOWN, DOWN, 400);
        d.update(DOWN, DOWN, 800);   // sadece 400 ms
        assert(!d.isArmed());
    }

    // 4b. Sure dolmus ama paket sayisi yetersizse arm etmez. Test 4 artik iki
    //     sebepten birden geciyor; bu vaka yalniz paket sartini sabitliyor.
    {
        GestureDetector d;
        d.reset(0);
        d.update(DOWN, DOWN, 0);
        d.update(UP, UP, 200);
        d.update(DOWN, DOWN, 400);
        // Sadece uc paket, ama aradan HOLD_MS'ten fazlasi gecti.
        d.update(DOWN, DOWN, 700);
        d.update(DOWN, DOWN, 1000);
        assert(!d.isArmed());
    }

    // 5. Ikinci asagi biraktirilirsa bastan baslar.
    {
        GestureDetector d;
        d.reset(0);
        d.update(DOWN, DOWN, 0);
        d.update(UP, UP, 200);
        d.update(DOWN, DOWN, 400);
        d.update(MID, MID, 600);     // birakti
        assert(d.phase() == Phase::Idle);
        d.update(DOWN, DOWN, 700);
        d.update(DOWN, DOWN, 1300);
        assert(!d.isArmed());
    }

    // 6. Sekans zaman asimi bastan baslatir.
    {
        GestureDetector d;
        d.reset(0);
        d.update(DOWN, DOWN, 0);
        d.update(UP, UP, 4000);      // 3000 ms gecti
        assert(d.phase() == Phase::Idle);
    }

    // 7. Tek cubuk ilerletmez.
    {
        GestureDetector d;
        d.reset(0);
        d.update(DOWN, UP, 0);
        assert(d.phase() == Phase::Idle);
        d.update(UP, DOWN, 100);
        assert(d.phase() == Phase::Idle);
    }

    // 8. Esik sinirlari: tam esik degeri asagi sayilmaz.
    {
        GestureDetector d;
        d.reset(0);
        d.update(arming::DOWN_THRESHOLD, arming::DOWN_THRESHOLD, 0);
        assert(d.phase() == Phase::Idle);
        d.update(arming::DOWN_THRESHOLD - 1, arming::DOWN_THRESHOLD - 1, 100);
        assert(d.phase() == Phase::Down1);
    }

    // 9. disarm() armed'i kaldirir ve jest tekrar aranabilir.
    {
        GestureDetector d;
        d.reset(0);
        runFullGesture(d, 0);
        assert(d.isArmed());
        d.disarm(2000);
        assert(!d.isArmed());
        assert(d.phase() == Phase::Idle);
        assert(runFullGesture(d, 3000));
        assert(d.isArmed());
    }

    // 10. Down2'ye zamaninda girilirse, tutma suresi sekans esigini assa bile
    //     arm eder. Zaman asimi jest desenini tamamlamayi sinirlar; pilot
    //     cubuklari bilincli tutarken jesti sessizce reddetmek istenmiyor.
    {
        GestureDetector d;
        d.reset(0);
        d.update(DOWN, DOWN, 0);
        d.update(UP, UP, 1000);
        d.update(DOWN, DOWN, 2900);
        assert(d.phase() == Phase::Down2);
        // Tutma, gercek bir 50 Hz linkin verdigi gibi paket akisiyla besleniyor.
        bool armedEdge = false;
        for (uint32_t t = 2920; t <= 3400; t += 20) {
            armedEdge |= d.update(DOWN, DOWN, t);
        }
        assert(armedEdge);
        assert(d.isArmed());
    }

    // 11. Down2'ye zamaninda girilemezse arm etmez: Up1'de zaman asimi vurur.
    {
        GestureDetector d;
        d.reset(0);
        d.update(DOWN, DOWN, 0);
        d.update(UP, UP, 1000);
        d.update(DOWN, DOWN, 3100);
        assert(d.phase() == Phase::Idle);
        assert(!d.isArmed());
    }

    // 12. millis() tasmasi: fark aritmetigi uint32 tasmasinda da dogru calisir.
    {
        GestureDetector d;
        const uint32_t nearMax = 0xFFFFFF00u;
        d.reset(nearMax);
        d.update(DOWN, DOWN, nearMax);
        d.update(UP, UP, nearMax + 200);
        d.update(DOWN, DOWN, nearMax + 400);
        assert(d.phase() == Phase::Down2);
        // <= kullanilamaz: zaman damgalari dongunun ortasinda tasiyor.
        bool armedEdge = false;
        for (uint32_t t = nearMax + 420; t != nearMax + 920; t += 20) {
            armedEdge |= d.update(DOWN, DOWN, t);
        }
        assert(armedEdge);
        assert(d.isArmed());
    }

    // 13. Tutma suresi yalniz duvar saatiyle olculmez: link yarida koparsa
    //     aradan 500 ms gecmis olsa bile tek paket jesti tamamlamaz.
    {
        GestureDetector d;
        d.reset(0);
        d.update(DOWN, DOWN, 0);
        d.update(UP, UP, 200);
        d.update(DOWN, DOWN, 400);
        assert(d.phase() == Phase::Down2);
        assert(!d.update(DOWN, DOWN, 1000));
        assert(!d.isArmed());
        for (uint32_t t = 1020; t <= 1200; t += 20) {
            d.update(DOWN, DOWN, t);
        }
        assert(d.isArmed());
    }

    printf("test_arming: OK\n");
    return 0;
}
